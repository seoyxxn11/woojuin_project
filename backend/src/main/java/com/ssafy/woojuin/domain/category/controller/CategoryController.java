package com.ssafy.woojuin.domain.category.controller;

import com.ssafy.woojuin.domain.category.dto.CategoryCreateRequest;
import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.category.dto.CategoryUpdateRequest;
import com.ssafy.woojuin.domain.category.service.CategoryService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 워크스페이스별 카테고리 관리 API. 접근하려면 해당 워크스페이스 멤버여야 한다.
 * userId는 JWT(@AuthenticatedUser + CurrentUserResolver)로 식별한다.
 */
@RestController
@RequestMapping("/api/workspaces/{workspaceId}/categories")
public class CategoryController {

    private final CategoryService categoryService;
    private final CurrentUserResolver currentUserResolver;

    public CategoryController(CategoryService categoryService, CurrentUserResolver currentUserResolver) {
        this.categoryService = categoryService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @GetMapping
    public ResponseEntity<ApiResponse<List<CategoryResponse>>> list(
            @PathVariable Long workspaceId,
            @RequestParam(defaultValue = "false") boolean hasItems) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(categoryService.list(workspaceId, userId, hasItems)));
    }

    @AuthenticatedUser
    @PostMapping
    public ResponseEntity<ApiResponse<CategoryResponse>> create(
            @PathVariable Long workspaceId, @Valid @RequestBody CategoryCreateRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        CategoryResponse response = categoryService.create(workspaceId, userId, request.name());
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.of(201, "success", response));
    }

    @AuthenticatedUser
    @PatchMapping("/{categoryId}")
    public ResponseEntity<ApiResponse<CategoryResponse>> rename(
            @PathVariable Long workspaceId, @PathVariable Long categoryId,
            @Valid @RequestBody CategoryUpdateRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(
                categoryService.rename(workspaceId, userId, categoryId, request.name())));
    }

    @AuthenticatedUser
    @DeleteMapping("/{categoryId}")
    public ResponseEntity<ApiResponse<Void>> delete(
            @PathVariable Long workspaceId, @PathVariable Long categoryId) {
        Long userId = currentUserResolver.resolveUserId();
        categoryService.delete(workspaceId, userId, categoryId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }
}
