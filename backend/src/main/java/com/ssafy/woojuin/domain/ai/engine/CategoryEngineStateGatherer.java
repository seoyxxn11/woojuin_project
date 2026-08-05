package com.ssafy.woojuin.domain.ai.engine;

import com.ssafy.woojuin.domain.ai.CategoryEngineClient;
import com.ssafy.woojuin.domain.ai.engine.entity.CandidateAlias;
import com.ssafy.woojuin.domain.ai.engine.entity.CategoryAnchor;
import com.ssafy.woojuin.domain.ai.engine.entity.TemporaryCandidate;
import com.ssafy.woojuin.domain.ai.engine.repository.CandidateAliasRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.CategoryAnchorRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.TemporaryCandidateRepository;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Limit;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * decide 요청에 실을 현재 워크스페이스 상태를 DB에서 모은다. AI 서버가 상태를 저장하지 않으므로
 * "무엇이 있는지"는 백엔드가 매 호출마다 구성해 전달한다.
 *
 * <p>후보 shortlist는 v1에서 워크스페이스의 활성 후보 전체(상한)를 넘긴다 — 아이템 앵커는 decide
 * 안에서 추출되므로 호출 전에 앵커로 좁힐 수 없기 때문이다(임베딩 Top-K는 후속 최적화).
 */
@Service
@RequiredArgsConstructor
public class CategoryEngineStateGatherer {

    private static final int CANDIDATE_LIMIT = 100;

    private final CategoryRepository categoryRepository;
    private final CategoryAnchorRepository categoryAnchorRepository;
    private final TemporaryCandidateRepository candidateRepository;
    private final CandidateAliasRepository aliasRepository;

    /** 정식 카테고리(시드 + 승격) — 승격 카테고리는 앵커 메타를 붙인다. */
    @Transactional(readOnly = true)
    public List<CategoryEngineClient.FormalCategory> formalCategories(long workspaceId) {
        List<Category> categories = categoryRepository.findByWorkspaceId(workspaceId);
        Map<Long, CategoryAnchor> anchors = categoryAnchorRepository
                .findAllById(categories.stream().map(Category::getId).toList())
                .stream().collect(Collectors.toMap(CategoryAnchor::getCategoryId, Function.identity()));
        return categories.stream().map(c -> {
            CategoryAnchor a = anchors.get(c.getId());
            String origin = a != null ? a.getOrigin() : CategoryAnchor.SEED;
            return new CategoryEngineClient.FormalCategory(
                    c.getId(), c.getName(), origin,
                    a != null ? a.getAnchorType() : null,
                    a != null ? a.getNormalizedAnchorName() : null,
                    List.of());
        }).toList();
    }

    /** 후보 shortlist — 활성 후보(PENDING/READY) + 별칭. */
    @Transactional(readOnly = true)
    public List<CategoryEngineClient.Candidate> candidateShortlist(long workspaceId) {
        List<TemporaryCandidate> candidates = candidateRepository.findByWorkspaceIdAndStatusIn(
                workspaceId,
                List.of(TemporaryCandidate.PENDING, TemporaryCandidate.READY_TO_PROMOTE),
                Limit.of(CANDIDATE_LIMIT));
        return candidates.stream().map(c -> {
            List<String> aliases = aliasRepository.findByCandidateId(c.getId()).stream()
                    .map(CandidateAlias::getAliasKey).toList();
            return new CategoryEngineClient.Candidate(
                    c.getId(), c.getSuggestedName(), c.getAnchorType(), c.getNormalizedAnchorName(),
                    aliases, c.getSupportCount(), null, List.of());
        }).toList();
    }
}
