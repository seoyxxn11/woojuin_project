package com.ssafy.woojuin.domain.item.controller;

import com.ssafy.woojuin.domain.item.dto.ItemCreateRequest;
import com.ssafy.woojuin.domain.item.dto.ItemCreateResponse;
import com.ssafy.woojuin.domain.item.dto.ItemListResponse;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.service.ItemService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.common.ItemStatus;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 워크스페이스 단위 아이템 API (저장·목록·휴지통 목록).
 * 개별 아이템 단위 작업은 ItemDetailController 참고.
 *
 * workspaceId는 워크스페이스 역할 기반 접근 제어(멤버십 검증)가 아직 없어
 * path로만 받는다. userId는 JWT(@AuthenticatedUser + CurrentUserResolver)로 식별한다.
 */
@RestController
@RequestMapping("/api/workspaces/{workspaceId}")
public class ItemController {

    private final ItemService itemService;
    private final CurrentUserResolver currentUserResolver;

    public ItemController(ItemService itemService, CurrentUserResolver currentUserResolver) {
        this.itemService = itemService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @PostMapping(path = "/items", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<ApiResponse<ItemCreateResponse>> createFromRequest(
            @PathVariable Long workspaceId,
            @Valid @RequestBody ItemCreateRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        ItemCreateResponse response = itemService.createFromRequest(workspaceId, userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.of(201, "success", response));
    }

    @AuthenticatedUser
    @PostMapping(path = "/items", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ApiResponse<ItemCreateResponse>> createFromImage(
            @PathVariable Long workspaceId,
            @RequestPart MultipartFile file) {
        Long userId = currentUserResolver.resolveUserId();
        ItemCreateResponse response = itemService.createFromImage(workspaceId, userId, file);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.of(201, "success", response));
    }

    @AuthenticatedUser
    @GetMapping("/items")
    public ResponseEntity<ApiResponse<ItemListResponse>> list(
            @PathVariable Long workspaceId,
            @RequestParam(required = false) ItemType type,
            @RequestParam(required = false) ItemStatus status,
            @RequestParam(required = false) Boolean favorite,
            @RequestParam(required = false) List<Long> categoryIds,
            @RequestParam(defaultValue = "latest") String sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "28") int size) {
        Long userId = currentUserResolver.resolveUserId();
        ItemListResponse response =
                itemService.list(workspaceId, userId, type, status, favorite, categoryIds, sort, page, size);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /** 휴지통 목록 (FR-036). 삭제된 지 오래된 순이 아니라 최근 삭제 순으로 보여준다. */
    @AuthenticatedUser
    @GetMapping("/trash")
    public ResponseEntity<ApiResponse<ItemListResponse>> listTrash(
            @PathVariable Long workspaceId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "28") int size) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(itemService.listTrash(workspaceId, userId, page, size)));
    }
}
