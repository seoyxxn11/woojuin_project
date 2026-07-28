package com.ssafy.woojuin.domain.category.service;

import com.ssafy.woojuin.domain.category.CategoryColors;
import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.exception.CategoryNotFoundException;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 카테고리 사용자 관리(조회·추가·수정·삭제). AI 자동 분류 저장은
 * {@link CategoryAssignmentService}가 담당한다 — 사용자용/파이프라인용을 분리한다.
 *
 * <p>카테고리는 워크스페이스에 속하므로 모든 작업은 그 워크스페이스 멤버여야 한다.
 * "기타"는 분류 실패 폴백 대상이라 항상 존재해야 하므로 수정·삭제를 막는다.
 */
@Service
public class CategoryService {

    private final CategoryRepository categoryRepository;
    private final ItemCategoryRepository itemCategoryRepository;
    private final WorkspaceMemberRepository workspaceMemberRepository;

    public CategoryService(CategoryRepository categoryRepository,
            ItemCategoryRepository itemCategoryRepository,
            WorkspaceMemberRepository workspaceMemberRepository) {
        this.categoryRepository = categoryRepository;
        this.itemCategoryRepository = itemCategoryRepository;
        this.workspaceMemberRepository = workspaceMemberRepository;
    }

    /**
     * hasItems=true면 활성(휴지통 제외) 아이템이 하나라도 있는 카테고리만 반환한다 —
     * 필터 칩처럼 "실제로 아이템이 있는 카테고리"만 보여줄 때 쓴다. 기본(false)은 전체
     * 반환(카테고리 관리·수동 지정 등 빈 카테고리도 필요한 경로용).
     */
    @Transactional(readOnly = true)
    public List<CategoryResponse> list(Long workspaceId, Long userId, boolean hasItems) {
        verifyMembership(workspaceId, userId);
        List<Category> categories = categoryRepository.findByWorkspaceId(workspaceId);
        if (hasItems) {
            Set<Long> withItems = new HashSet<>(
                    itemCategoryRepository.findCategoryIdsWithActiveItems(workspaceId));
            categories = categories.stream()
                    .filter(category -> withItems.contains(category.getId()))
                    .toList();
        }
        return categories.stream().map(CategoryResponse::from).toList();
    }

    @Transactional
    public CategoryResponse create(Long workspaceId, Long userId, String name) {
        verifyMembership(workspaceId, userId);
        String trimmed = normalize(name);
        if (categoryRepository.existsByWorkspaceIdAndName(workspaceId, trimmed)) {
            throw new IllegalArgumentException("이미 같은 이름의 카테고리가 있습니다: " + trimmed);
        }
        // 색은 서버가 자동 배정한다 — 기존 별자리(기타 제외) 수를 기준으로 팔레트를 순환한다.
        Category saved = categoryRepository.save(
                Category.builder().workspaceId(workspaceId).name(trimmed)
                        .color(CategoryColors.forOrdinal(constellationCount(workspaceId))).build());
        return CategoryResponse.from(saved);
    }

    @Transactional
    public CategoryResponse rename(Long workspaceId, Long userId, Long categoryId, String name) {
        verifyMembership(workspaceId, userId);
        Category category = findInWorkspace(workspaceId, categoryId);
        if (CategoryDefaults.ETC.equals(category.getName())) {
            throw new IllegalArgumentException("\"" + CategoryDefaults.ETC + "\" 카테고리는 수정할 수 없습니다");
        }
        String trimmed = normalize(name);
        // 다른 카테고리가 이미 그 이름을 쓰고 있으면 중복. 자기 이름 그대로면 통과.
        if (!trimmed.equals(category.getName())
                && categoryRepository.existsByWorkspaceIdAndName(workspaceId, trimmed)) {
            throw new IllegalArgumentException("이미 같은 이름의 카테고리가 있습니다: " + trimmed);
        }
        category.rename(trimmed);
        return CategoryResponse.from(category);
    }

    @Transactional
    public void delete(Long workspaceId, Long userId, Long categoryId) {
        verifyMembership(workspaceId, userId);
        Category category = findInWorkspace(workspaceId, categoryId);
        if (CategoryDefaults.ETC.equals(category.getName())) {
            throw new IllegalArgumentException("\"" + CategoryDefaults.ETC + "\" 카테고리는 삭제할 수 없습니다");
        }
        // 아이템 연결을 먼저 끊어야 고아 조인 행이 남지 않는다.
        itemCategoryRepository.deleteByCategoryId(categoryId);
        categoryRepository.delete(category);
    }

    /** categoryId가 그 워크스페이스 소속인지까지 확인한다(다른 워크스페이스 카테고리 접근 차단). */
    private Category findInWorkspace(Long workspaceId, Long categoryId) {
        Category category = categoryRepository.findById(categoryId)
                .orElseThrow(() -> new CategoryNotFoundException(categoryId));
        if (!category.getWorkspaceId().equals(workspaceId)) {
            throw new CategoryNotFoundException(categoryId);
        }
        return category;
    }

    /** 색상 순환 배정 기준 — 그 워크스페이스의 별자리(기타 제외) 수. */
    private int constellationCount(Long workspaceId) {
        return (int) categoryRepository.findByWorkspaceId(workspaceId).stream()
                .filter(c -> !CategoryDefaults.ETC.equals(c.getName()))
                .count();
    }

    private void verifyMembership(Long workspaceId, Long userId) {
        workspaceMemberRepository.findByWorkspaceIdAndUserId(workspaceId, userId)
                .orElseThrow(() -> new WorkspaceMemberRequiredException(workspaceId));
    }

    private String normalize(String name) {
        String trimmed = name == null ? "" : name.trim();
        if (trimmed.isEmpty()) {
            throw new IllegalArgumentException("카테고리 이름이 비어 있습니다");
        }
        return trimmed;
    }
}
