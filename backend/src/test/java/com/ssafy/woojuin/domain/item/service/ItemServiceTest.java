package com.ssafy.woojuin.domain.item.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.item.dto.ItemCreateRequest;
import com.ssafy.woojuin.domain.item.dto.ItemCreateResponse;
import com.ssafy.woojuin.domain.item.dto.ItemListResponse;
import com.ssafy.woojuin.domain.item.dto.ItemDetailResponse;
import com.ssafy.woojuin.domain.item.dto.ItemStatusResponse;
import com.ssafy.woojuin.domain.item.dto.ItemUpdateRequest;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.exception.ItemNotFoundException;
import com.ssafy.woojuin.domain.item.exception.WorkspaceAccessDeniedException;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class ItemServiceTest {

    @Mock
    private ItemRepository itemRepository;

    @Mock
    private S3Uploader s3Uploader;

    @Mock
    private ItemQueueProducer itemQueueProducer;

    @Mock
    private WorkspaceMemberRepository workspaceMemberRepository;

    @Mock
    private com.ssafy.woojuin.domain.category.service.ItemCategoryQueryService itemCategoryQueryService;

    @InjectMocks
    private ItemService itemService;

    /**
     * 대부분의 테스트는 멤버십 검증 자체가 아니라 그 다음 로직을 보는 것이라, 기본적으로 멤버라고
     * 가정한다. 아이템이 없어 멤버십 검증까지 가지도 않는 404 테스트들도 있어 lenient로 둔다.
     */
    @BeforeEach
    void setUpMembership() {
        lenient().when(workspaceMemberRepository.findByWorkspaceIdAndUserId(any(), any()))
                .thenReturn(Optional.of(mock(WorkspaceMember.class)));
        // 읽기 경로가 카테고리를 조회하지만 이 테스트들의 관심사는 아니라 기본 빈 결과로 둔다.
        lenient().when(itemCategoryQueryService.categoriesByItemIds(any())).thenReturn(java.util.Map.of());
        lenient().when(itemCategoryQueryService.categoriesOf(any())).thenReturn(List.of());
    }

    @Test
    void URL_타입은_url이_없으면_예외() {
        ItemCreateRequest request = new ItemCreateRequest(ItemType.URL, null, null);

        assertThatThrownBy(() -> itemService.createFromRequest(1L, 1L, request))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void URL_타입에_content를_같이_보내면_예외() {
        ItemCreateRequest request = new ItemCreateRequest(ItemType.URL, "https://example.com", "메모");

        assertThatThrownBy(() -> itemService.createFromRequest(1L, 1L, request))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void MEMO_타입은_content가_없으면_예외() {
        ItemCreateRequest request = new ItemCreateRequest(ItemType.MEMO, null, null);

        assertThatThrownBy(() -> itemService.createFromRequest(1L, 1L, request))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void URL_저장_성공시_큐에_발행되고_PROCESSING_응답() {
        ItemCreateRequest request = new ItemCreateRequest(ItemType.URL, "https://example.com", null);
        when(itemRepository.save(any(Item.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ItemCreateResponse response = itemService.createFromRequest(10L, 1L, request);

        assertThat(response.status()).isEqualTo(ItemStatus.PROCESSING);
        verify(itemQueueProducer).publish(response.itemId(), 10L, ItemType.URL);
    }

    @Test
    void IMAGE_저장은_S3_업로드_후_큐에_발행() {
        MockMultipartFile file = new MockMultipartFile("file", "photo.png", "image/png", new byte[] {1, 2, 3});
        when(s3Uploader.upload(file, 10L)).thenReturn("items/10/uuid-photo.png");
        when(itemRepository.save(any(Item.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ItemCreateResponse response = itemService.createFromImage(10L, 1L, file);

        assertThat(response.status()).isEqualTo(ItemStatus.PROCESSING);
        verify(itemQueueProducer).publish(response.itemId(), 10L, ItemType.IMAGE);
    }

    @Test
    void IMAGE_저장시_원본_파일명이_title_기본값으로_채워진다() {
        MockMultipartFile file = new MockMultipartFile("file", "제주도_노을.jpg", "image/jpeg", new byte[] {1});
        when(s3Uploader.upload(file, 10L)).thenReturn("items/10/uuid-제주도_노을.jpg");
        ArgumentCaptor<Item> captor = ArgumentCaptor.forClass(Item.class);
        when(itemRepository.save(captor.capture())).thenAnswer(invocation -> invocation.getArgument(0));

        itemService.createFromImage(10L, 1L, file);

        assertThat(captor.getValue().getTitle()).isEqualTo("제주도_노을.jpg");
    }

    @Test
    void IMAGE_저장시_파일명이_없으면_title은_null() {
        MockMultipartFile file = new MockMultipartFile("file", null, "image/png", new byte[] {1});
        when(s3Uploader.upload(file, 10L)).thenReturn("items/10/uuid");
        ArgumentCaptor<Item> captor = ArgumentCaptor.forClass(Item.class);
        when(itemRepository.save(captor.capture())).thenAnswer(invocation -> invocation.getArgument(0));

        itemService.createFromImage(10L, 1L, file);

        assertThat(captor.getValue().getTitle()).isNull();
    }

    @Test
    void IMAGE_저장시_DB저장이_실패하면_S3_원본을_정리하고_예외를_전파한다() {
        MockMultipartFile file = new MockMultipartFile("file", "photo.png", "image/png", new byte[] {1});
        when(s3Uploader.upload(file, 10L)).thenReturn("items/10/uuid-photo.png");
        when(itemRepository.save(any(Item.class))).thenThrow(new RuntimeException("DB 장애"));

        assertThatThrownBy(() -> itemService.createFromImage(10L, 1L, file))
                .isInstanceOf(RuntimeException.class)
                .hasMessage("DB 장애");

        verify(s3Uploader).deleteQuietly("items/10/uuid-photo.png");
        verify(itemQueueProducer, never()).publish(any(), any(), any());
    }

    @Test
    void IMAGE_저장시_큐_발행만_실패하면_S3_원본을_정리하지_않는다() {
        MockMultipartFile file = new MockMultipartFile("file", "photo.png", "image/png", new byte[] {1});
        when(s3Uploader.upload(file, 10L)).thenReturn("items/10/uuid-photo.png");
        when(itemRepository.save(any(Item.class))).thenAnswer(invocation -> invocation.getArgument(0));
        doThrow(new RuntimeException("Redis 장애")).when(itemQueueProducer).publish(any(), any(), any());

        // DB엔 이미 커밋된 뒤라 S3 원본을 지우면 참조가 끊긴 아이템이 되므로 지우면 안 된다.
        assertThatThrownBy(() -> itemService.createFromImage(10L, 1L, file))
                .isInstanceOf(RuntimeException.class);

        verify(s3Uploader, never()).deleteQuietly(any());
    }

    @Test
    void 상세조회는_존재하는_아이템을_반환() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(item));

        ItemDetailResponse response = itemService.getDetail(1L, 1L);

        assertThat(response.type()).isEqualTo(ItemType.URL);
        assertThat(response.url()).isEqualTo("https://example.com");
        assertThat(response.imageUrl()).isNull();
        verify(s3Uploader, never()).presignGet(any());
    }

    @Test
    void IMAGE_상세조회는_presigned_이미지URL을_채운다() {
        Item image = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.IMAGE)
                .s3Key("items/1/uuid-photo.png").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(image));
        when(s3Uploader.presignGet("items/1/uuid-photo.png"))
                .thenReturn("http://localhost:9000/woojuin-items/items/1/uuid-photo.png?sig=abc");

        ItemDetailResponse response = itemService.getDetail(1L, 1L);

        assertThat(response.type()).isEqualTo(ItemType.IMAGE);
        assertThat(response.imageUrl())
                .isEqualTo("http://localhost:9000/woojuin-items/items/1/uuid-photo.png?sig=abc");
    }

    @Test
    void 상세조회는_없는_아이템이면_404_예외() {
        when(itemRepository.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> itemService.getDetail(999L, 1L))
                .isInstanceOf(ItemNotFoundException.class);
    }

    @Test
    void 상태조회는_상태값만_반환() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("메모").build();
        when(itemRepository.findById(2L)).thenReturn(Optional.of(item));

        ItemStatusResponse response = itemService.getStatus(2L, 1L);

        assertThat(response.status()).isEqualTo(ItemStatus.PROCESSING);
    }

    @Test
    void 목록조회는_페이지_결과를_그대로_매핑() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").build();
        ReflectionTestUtils.setField(item, "id", 1L);   // 영속 아이템은 id를 가진다
        when(itemRepository.findAll(any(Specification.class), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(item), PageRequest.of(0, 20), 1));

        ItemListResponse response = itemService.list(1L, 1L, null, null, null, null, "latest", 0, 20);

        assertThat(response.totalElements()).isEqualTo(1);
        assertThat(response.content()).hasSize(1);
    }

    @Test
    void IMAGE_목록조회는_썸네일이_있으면_썸네일_presigned_URL을_쓴다() {
        Item image = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.IMAGE)
                .s3Key("items/1/photo.png").build();
        image.applyThumbnail("items/1/photo.png.thumb.webp");
        ReflectionTestUtils.setField(image, "id", 1L);
        when(itemRepository.findAll(any(Specification.class), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(image), PageRequest.of(0, 20), 1));
        when(s3Uploader.presignGet("items/1/photo.png.thumb.webp")).thenReturn("http://minio/thumb?sig=1");

        ItemListResponse response = itemService.list(1L, 1L, null, null, null, null, "latest", 0, 20);

        assertThat(response.content().get(0).imageUrl()).isEqualTo("http://minio/thumb?sig=1");
    }

    @Test
    void IMAGE_목록조회는_썸네일이_없으면_원본으로_폴백한다() {
        Item image = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.IMAGE)
                .s3Key("items/1/photo.png").build();   // 썸네일 미생성(PROCESSING 등)
        ReflectionTestUtils.setField(image, "id", 1L);
        when(itemRepository.findAll(any(Specification.class), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(image), PageRequest.of(0, 20), 1));
        when(s3Uploader.presignGet("items/1/photo.png")).thenReturn("http://minio/original?sig=1");

        ItemListResponse response = itemService.list(1L, 1L, null, null, null, null, "latest", 0, 20);

        assertThat(response.content().get(0).imageUrl()).isEqualTo("http://minio/original?sig=1");
    }

    @Test
    void 목록조회_size가_상한을_넘으면_잘린다() {
        ArgumentCaptor<PageRequest> captor = ArgumentCaptor.forClass(PageRequest.class);
        when(itemRepository.findAll(any(Specification.class), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(), PageRequest.of(0, 100), 0));

        itemService.list(1L, 1L, null, null, null, null, "latest", 0, 100_000);

        verify(itemRepository).findAll(any(Specification.class), captor.capture());
        assertThat(captor.getValue().getPageSize()).isEqualTo(100);
    }

    @Test
    void 카테고리로_필터하면_해당_카테고리_아이템만_반환한다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO).content("메모").build();
        ReflectionTestUtils.setField(item, "id", 7L);
        when(itemCategoryQueryService.itemIdsInCategories(List.of(3L))).thenReturn(List.of(7L));
        when(itemRepository.findAll(any(Specification.class), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(item), PageRequest.of(0, 28), 1));

        ItemListResponse response = itemService.list(1L, 1L, null, null, null, List.of(3L), "latest", 0, 28);

        assertThat(response.totalElements()).isEqualTo(1);
        assertThat(response.content().get(0).itemId()).isEqualTo(7L);
        verify(itemCategoryQueryService).itemIdsInCategories(List.of(3L));
    }

    @Test
    void 카테고리를_여러개_선택하면_그중_하나라도_연결된_아이템을_OR로_반환한다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO).content("메모").build();
        ReflectionTestUtils.setField(item, "id", 8L);
        when(itemCategoryQueryService.itemIdsInCategories(List.of(3L, 5L))).thenReturn(List.of(8L));
        when(itemRepository.findAll(any(Specification.class), any(PageRequest.class)))
                .thenReturn(new PageImpl<>(List.of(item), PageRequest.of(0, 28), 1));

        ItemListResponse response = itemService.list(1L, 1L, null, null, null, List.of(3L, 5L), "latest", 0, 28);

        assertThat(response.totalElements()).isEqualTo(1);
        assertThat(response.content().get(0).itemId()).isEqualTo(8L);
        verify(itemCategoryQueryService).itemIdsInCategories(List.of(3L, 5L));
    }

    @Test
    void 카테고리에_연결된_아이템이_없으면_조회없이_빈결과() {
        when(itemCategoryQueryService.itemIdsInCategories(List.of(3L))).thenReturn(List.of());

        ItemListResponse response = itemService.list(1L, 1L, null, null, null, List.of(3L), "latest", 0, 28);

        assertThat(response.totalElements()).isEqualTo(0);
        assertThat(response.content()).isEmpty();
        verify(itemRepository, never()).findAll(any(Specification.class), any(PageRequest.class));
    }

    @Test
    void 소프트삭제된_아이템은_상세조회에서_404() {
        Item deleted = trashedItem();
        when(itemRepository.findById(5L)).thenReturn(Optional.of(deleted));

        assertThatThrownBy(() -> itemService.getDetail(5L, 1L))
                .isInstanceOf(ItemNotFoundException.class);
    }

    @Test
    void 워크스페이스_멤버가_아니면_상세조회_403() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(item));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(1L, 999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> itemService.getDetail(1L, 999L))
                .isInstanceOf(WorkspaceAccessDeniedException.class);
    }

    @Test
    void 워크스페이스_멤버가_아니면_생성_403() {
        ItemCreateRequest request = new ItemCreateRequest(ItemType.URL, "https://example.com", null);
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(1L, 999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> itemService.createFromRequest(1L, 999L, request))
                .isInstanceOf(WorkspaceAccessDeniedException.class);
        verify(itemRepository, never()).save(any());
    }

    @Test
    void 수정은_null이_아닌_필드만_반영() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .title("원래 제목").content("원래 내용").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(item));

        ItemDetailResponse response = itemService.update(1L, 1L, new ItemUpdateRequest("바뀐 제목", null));

        assertThat(response.title()).isEqualTo("바뀐 제목");
        assertThat(response.content()).isEqualTo("원래 내용");
    }

    @Test
    void URL_아이템에도_메모를_붙일_수_있다() {
        // 트랙 A/B가 모두 실패하면 사용자 메모로 폴백하기 때문 (FR-020)
        Item urlItem = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(urlItem));

        ItemDetailResponse response = itemService.update(1L, 1L, new ItemUpdateRequest(null, "직접 남긴 메모"));

        assertThat(response.content()).isEqualTo("직접 남긴 메모");
        assertThat(response.url()).isEqualTo("https://example.com");
    }

    @Test
    void 수정할_내용이_하나도_없으면_예외() {
        assertThatThrownBy(() -> itemService.update(1L, 1L, new ItemUpdateRequest(null, null)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void 수정은_큐에_재발행하지_않는다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("원래").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(item));

        itemService.update(1L, 1L, new ItemUpdateRequest(null, "수정됨"));

        verifyNoInteractions(itemQueueProducer);
    }

    @Test
    void 삭제는_행을_지우지_않고_휴지통으로_보낸다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("메모").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(item));

        itemService.moveToTrash(1L, 1L);

        assertThat(item.isTrashed()).isTrue();
        verify(itemRepository, never()).delete(any(Item.class));
    }

    @Test
    void 휴지통에_없는_아이템은_복구할_수_없다() {
        Item active = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("정상").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(active));

        assertThatThrownBy(() -> itemService.restore(1L, 1L))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void 복구하면_다시_조회된다() {
        Item trashed = trashedItem();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(trashed));

        ItemDetailResponse response = itemService.restore(1L, 1L);

        assertThat(trashed.isTrashed()).isFalse();
        assertThat(response.deletedAt()).isNull();
    }

    @Test
    void 휴지통에_없는_아이템은_영구삭제할_수_없다() {
        Item active = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("정상").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(active));

        assertThatThrownBy(() -> itemService.deletePermanently(1L, 1L))
                .isInstanceOf(IllegalArgumentException.class);
        verify(itemRepository, never()).delete(any(Item.class));
    }

    @Test
    void 이미지_영구삭제는_S3_원본도_지운다() {
        Item trashed = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.IMAGE)
                .s3Key("items/1/uuid-photo.png").build();
        ReflectionTestUtils.setField(trashed, "deletedAt", OffsetDateTime.now());
        when(itemRepository.findById(1L)).thenReturn(Optional.of(trashed));

        itemService.deletePermanently(1L, 1L);

        verify(itemRepository).delete(trashed);
        verify(s3Uploader).deleteQuietly("items/1/uuid-photo.png");
    }

    @Test
    void 이미지_영구삭제는_썸네일도_함께_지운다() {
        Item trashed = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.IMAGE)
                .s3Key("items/1/photo.png").build();
        trashed.applyThumbnail("items/1/photo.png.thumb.webp");
        ReflectionTestUtils.setField(trashed, "deletedAt", OffsetDateTime.now());
        when(itemRepository.findById(1L)).thenReturn(Optional.of(trashed));

        itemService.deletePermanently(1L, 1L);

        verify(s3Uploader).deleteQuietly("items/1/photo.png");
        verify(s3Uploader).deleteQuietly("items/1/photo.png.thumb.webp");
    }

    @Test
    void s3Key가_없는_아이템_영구삭제는_S3를_호출하지_않는다() {
        Item trashed = trashedItem();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(trashed));

        itemService.deletePermanently(1L, 1L);

        verify(itemRepository).delete(trashed);
        verifyNoInteractions(s3Uploader);
    }

    private Item trashedItem() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("삭제됨").build();
        ReflectionTestUtils.setField(item, "deletedAt", OffsetDateTime.now());
        return item;
    }
}
