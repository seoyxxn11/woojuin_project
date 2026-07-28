package com.ssafy.woojuin.domain.item.controller;

import com.ssafy.woojuin.domain.item.dto.ItemDetailResponse;
import com.ssafy.woojuin.domain.item.dto.ItemStatusResponse;
import com.ssafy.woojuin.domain.item.dto.ItemUpdateRequest;
import com.ssafy.woojuin.domain.item.service.ItemService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 개별 아이템 단위 API. API 명세서 기준 이 경로들은 workspaceId 없이 itemId만으로
 * 접근한다 (아이템이 자기 workspaceId를 갖고 있어 경로에 중복시킬 필요가 없음).
 */
@RestController
@RequestMapping("/api/items/{itemId}")
public class ItemDetailController {

    private final ItemService itemService;
    private final CurrentUserResolver currentUserResolver;

    public ItemDetailController(ItemService itemService, CurrentUserResolver currentUserResolver) {
        this.itemService = itemService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @GetMapping
    public ResponseEntity<ApiResponse<ItemDetailResponse>> detail(@PathVariable Long itemId) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(itemService.getDetail(itemId, userId)));
    }

    @AuthenticatedUser
    @GetMapping("/status")
    public ResponseEntity<ApiResponse<ItemStatusResponse>> status(@PathVariable Long itemId) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(itemService.getStatus(itemId, userId)));
    }

    @AuthenticatedUser
    @PatchMapping
    public ResponseEntity<ApiResponse<ItemDetailResponse>> update(
            @PathVariable Long itemId,
            @Valid @RequestBody ItemUpdateRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(itemService.update(itemId, userId, request)));
    }

    /** 휴지통 이동 (soft delete). 영구 삭제는 /permanent로만 가능하다. */
    @AuthenticatedUser
    @DeleteMapping
    public ResponseEntity<ApiResponse<Void>> moveToTrash(@PathVariable Long itemId) {
        Long userId = currentUserResolver.resolveUserId();
        itemService.moveToTrash(itemId, userId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }

    @AuthenticatedUser
    @PostMapping("/restore")
    public ResponseEntity<ApiResponse<ItemDetailResponse>> restore(@PathVariable Long itemId) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(itemService.restore(itemId, userId)));
    }

    @AuthenticatedUser
    @DeleteMapping("/permanent")
    public ResponseEntity<ApiResponse<Void>> deletePermanently(@PathVariable Long itemId) {
        Long userId = currentUserResolver.resolveUserId();
        itemService.deletePermanently(itemId, userId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }
}
