package com.ssafy.woojuin.domain.ai.engine;

import com.ssafy.woojuin.domain.ai.CategoryEngineClient;
import com.ssafy.woojuin.domain.ai.engine.entity.CandidateAlias;
import com.ssafy.woojuin.domain.ai.engine.entity.CandidateItemLink;
import com.ssafy.woojuin.domain.ai.engine.entity.CategoryAnchor;
import com.ssafy.woojuin.domain.ai.engine.entity.TemporaryCandidate;
import com.ssafy.woojuin.domain.ai.engine.repository.CandidateAliasRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.CandidateItemLinkRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.CategoryAnchorRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.TemporaryCandidateRepository;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * AI decide 응답의 {@code actions}를 백엔드 상태(DB·Redis)에 반영하는 실행기.
 *
 * <p>AI 서버는 상태를 저장하지 않고 "이렇게 바꿔라"만 반환한다(계약 문서 참고). 실제 연결·생성·
 * 승격·신호 저장은 여기서 한 트랜잭션으로 처리한다. action 적용 순서는 계약대로
 * LINK_FORMAL_CATEGORY → CREATE_CANDIDATE → LINK_CANDIDATE → PROMOTE_CANDIDATE → STORE_SIGNAL.
 *
 * <p>AI는 영속 id를 만들지 않는다 — 새 후보·승격 카테고리 id는 여기서 채번한다. LINK 계열은
 * 존재하면 건너뛰어 멱등하다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CategoryEngineActionExecutor {

    private final CategoryRepository categoryRepository;
    private final ItemCategoryRepository itemCategoryRepository;
    private final TemporaryCandidateRepository candidateRepository;
    private final CandidateItemLinkRepository linkRepository;
    private final CandidateAliasRepository aliasRepository;
    private final CategoryAnchorRepository categoryAnchorRepository;
    private final CategoryEngineSignalStore signalStore;

    /** 적용 결과 요약(로깅·응답용). AI가 채우지 못하는 채번 결과를 담는다. */
    public record ApplyResult(
            List<Long> linkedCategoryIds, Long createdCandidateId, Long promotedCategoryId,
            boolean signalStored) {
    }

    @Transactional
    public ApplyResult apply(
            long workspaceId, long itemId, String title, String summary,
            CategoryEngineClient.DecideResult decision) {

        List<CategoryEngineClient.EngineAction> actions = decision.actions();
        List<Long> linkedCategoryIds = new ArrayList<>();
        Long createdCandidateId = null;
        Long promotedCategoryId = null;
        boolean signalStored = false;

        // 계약 적용 순서대로(원 응답 순서와 무관하게 타입별로) 처리한다.
        for (var a : byType(actions, "LINK_FORMAL_CATEGORY")) {
            if (a.categoryId() != null && linkFormalCategory(itemId, a.categoryId())) {
                linkedCategoryIds.add(a.categoryId());
            }
        }
        for (var a : byType(actions, "CREATE_CANDIDATE")) {
            createdCandidateId = createCandidate(workspaceId, a);
        }
        for (var a : byType(actions, "LINK_CANDIDATE")) {
            linkCandidate(a, itemId);
        }
        for (var a : byType(actions, "PROMOTE_CANDIDATE")) {
            promotedCategoryId = promoteCandidate(workspaceId, a);
            if (promotedCategoryId != null && !linkedCategoryIds.contains(promotedCategoryId)) {
                linkedCategoryIds.add(promotedCategoryId);
            }
        }
        for (var a : byType(actions, "STORE_SIGNAL")) {
            storeSignal(workspaceId, itemId, title, summary, a);
            signalStored = true;
        }

        return new ApplyResult(linkedCategoryIds, createdCandidateId, promotedCategoryId, signalStored);
    }

    // ---- action별 처리 ----

    private boolean linkFormalCategory(long itemId, long categoryId) {
        if (itemCategoryRepository.existsByItemIdAndCategoryId(itemId, categoryId)) {
            return false;  // 멱등
        }
        itemCategoryRepository.save(ItemCategory.builder().itemId(itemId).categoryId(categoryId).build());
        return true;
    }

    private Long createCandidate(long workspaceId, CategoryEngineClient.EngineAction a) {
        TemporaryCandidate candidate = candidateRepository.save(TemporaryCandidate.builder()
                .workspaceId(workspaceId)
                .suggestedName(a.suggestedName())
                .anchorType(a.anchorType())
                .normalizedAnchorName(a.normalizedAnchorName())
                .supportCount(a.supportCountAfter() != null ? a.supportCountAfter() : 0)
                .status(TemporaryCandidate.PENDING)
                .build());
        saveAliases(candidate.getId(), a.aliases());
        if (a.linkItemIds() != null) {
            for (Long linkItemId : a.linkItemIds()) {
                linkCandidateItem(candidate.getId(), linkItemId);
            }
        }
        // 전환됐으므로 원 잠정 신호(Redis)를 지운다.
        if (a.normalizedAnchorName() != null) {
            signalStore.delete(workspaceId, a.normalizedAnchorName());
        }
        return candidate.getId();
    }

    private void linkCandidate(CategoryEngineClient.EngineAction a, long itemId) {
        if (a.candidateId() == null) {
            return;
        }
        linkCandidateItem(a.candidateId(), itemId);
        candidateRepository.findById(a.candidateId()).ifPresent(candidate -> {
            if (a.supportCountAfter() != null) {
                candidate.updateSupportCount(a.supportCountAfter());
            }
        });
    }

    private Long promoteCandidate(long workspaceId, CategoryEngineClient.EngineAction a) {
        if (a.candidateId() == null) {
            return null;
        }
        TemporaryCandidate candidate = candidateRepository.findById(a.candidateId()).orElse(null);
        if (candidate == null) {
            log.warn("승격 대상 후보 없음: candidateId={}", a.candidateId());
            return null;
        }
        String name = a.categoryName() != null ? a.categoryName() : candidate.getSuggestedName();

        // 같은 이름 카테고리가 이미 있으면 재사용(워크스페이스 내 이름 유니크)
        Category category = categoryRepository.findByWorkspaceIdAndName(workspaceId, name)
                .orElseGet(() -> categoryRepository.save(
                        Category.builder().workspaceId(workspaceId).name(name).build()));
        Long categoryId = category.getId();

        // 승격 카테고리 앵커 메타 기록(재사용 매칭용)
        if (!categoryAnchorRepository.existsById(categoryId)) {
            categoryAnchorRepository.save(CategoryAnchor.builder()
                    .categoryId(categoryId)
                    .origin(CategoryAnchor.AI_PROMOTED)
                    .anchorType(a.anchorType() != null ? a.anchorType() : candidate.getAnchorType())
                    .normalizedAnchorName(candidate.getNormalizedAnchorName())
                    .build());
        }

        candidate.promote(categoryId);

        // 연결된 데이터를 새 정식 카테고리로 재분류(다중 카테고리 — 기존 연결은 유지)
        for (CandidateItemLink link : linkRepository.findByCandidateId(candidate.getId())) {
            linkFormalCategory(link.getItemId(), categoryId);
        }
        return categoryId;
    }

    private void storeSignal(
            long workspaceId, long itemId, String title, String summary,
            CategoryEngineClient.EngineAction a) {
        Long firstItemId = (a.linkItemIds() != null && !a.linkItemIds().isEmpty())
                ? a.linkItemIds().get(0) : itemId;
        signalStore.store(workspaceId, new CategoryEngineSignalStore.StoredSignal(
                null, firstItemId, a.anchorType(), a.normalizedAnchorName(),
                a.aliases() != null ? a.aliases() : List.of(), title, summary));
    }

    // ---- 헬퍼 ----

    private void linkCandidateItem(Long candidateId, Long itemId) {
        if (!linkRepository.existsByCandidateIdAndItemId(candidateId, itemId)) {
            linkRepository.save(
                    CandidateItemLink.builder().candidateId(candidateId).itemId(itemId).build());
        }
    }

    private void saveAliases(Long candidateId, List<String> aliases) {
        if (aliases == null) {
            return;
        }
        for (String alias : aliases) {
            String key = AnchorKeys.normalize(alias);
            if (!key.isBlank() && !aliasRepository.existsByCandidateIdAndAliasKey(candidateId, key)) {
                aliasRepository.save(
                        CandidateAlias.builder().candidateId(candidateId).aliasKey(key).build());
            }
        }
    }

    private static List<CategoryEngineClient.EngineAction> byType(
            List<CategoryEngineClient.EngineAction> actions, String type) {
        List<CategoryEngineClient.EngineAction> out = new ArrayList<>();
        for (var a : actions) {
            if (type.equals(a.type())) {
                out.add(a);
            }
        }
        return out;
    }
}
