package com.ssafy.woojuin.domain.item.processing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * 반영 단계의 계약을 직접 검증한다. 프로세서 테스트가 "네트워크 결과 → 올바른 반영"을 훑는다면,
 * 여기서는 재로드·상태 재확인·null 보존 같은 반영 자체의 규칙에 집중한다.
 */
@ExtendWith(MockitoExtension.class)
class ItemEnrichmentWriterTest {

    @Mock ItemRepository itemRepository;
    @Mock CategoryAssignmentService categoryAssignmentService;
    @InjectMocks ItemEnrichmentWriter writer;

    private Item item(ItemStatus status, String title) {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com/a").title(title).build();
        ReflectionTestUtils.setField(item, "id", 42L);
        if (status != ItemStatus.PROCESSING) {
            // 저장 시 기본값은 PROCESSING이므로, 다른 상태는 명시적으로 만들어 준다.
            ReflectionTestUtils.setField(item, "status", status);
        }
        return item;
    }

    @Test
    void PROCESSING이면_반영하고_카테고리를_연결하고_상태를_확정한다() {
        Item item = item(ItemStatus.PROCESSING, null);
        when(itemRepository.findById(42L)).thenReturn(Optional.of(item));

        writer.apply(42L, ItemEnrichment.builder()
                .previewTitle("제목").previewThumbnailUrl("https://thumb").previewDescription("설명")
                .content("본문").summary("요약")
                .categories(List.of("학습·지식"))
                .targetStatus(ItemStatus.DONE)
                .build());

        assertThat(item.getTitle()).isEqualTo("제목");
        assertThat(item.getPreviewThumbnailUrl()).isEqualTo("https://thumb");
        assertThat(item.getPreviewDescription()).isEqualTo("설명");
        assertThat(item.getContent()).isEqualTo("본문");
        assertThat(item.getSummary()).isEqualTo("요약");
        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
        verify(categoryAssignmentService).assign(eq(42L), eq(1L), eq(List.of("학습·지식")));
    }

    @Test
    void 아이템이_사라졌으면_아무것도_하지_않는다() {
        when(itemRepository.findById(42L)).thenReturn(Optional.empty());

        writer.apply(42L, ItemEnrichment.builder().targetStatus(ItemStatus.DONE).build());

        verifyNoInteractions(categoryAssignmentService);
    }

    @Test
    void 이미_끝난_아이템이면_남의_결과를_덮어쓰지_않고_스킵한다() {
        // 동시성 안전망: 프리체크~반영 사이에 다른 소비자가 먼저 끝낸(PARTIAL) 상황.
        Item finished = item(ItemStatus.PARTIAL, "기존제목");
        when(itemRepository.findById(42L)).thenReturn(Optional.of(finished));

        writer.apply(42L, ItemEnrichment.builder()
                .previewTitle("새제목").content("새본문").summary("새요약")
                .categories(List.of("여행·장소"))
                .targetStatus(ItemStatus.DONE)
                .build());

        assertThat(finished.getStatus()).isEqualTo(ItemStatus.PARTIAL);   // DONE으로 덮어쓰지 않음
        assertThat(finished.getTitle()).isEqualTo("기존제목");
        assertThat(finished.getContent()).isNull();
        assertThat(finished.getSummary()).isNull();
        verifyNoInteractions(categoryAssignmentService);                  // 카테고리도 다시 붙이지 않음
    }

    @Test
    void null_필드는_기존값을_지우지_않고_상태만_PARTIAL로_확정한다() {
        Item item = item(ItemStatus.PROCESSING, "기존제목");
        when(itemRepository.findById(42L)).thenReturn(Optional.of(item));

        // 본문·요약을 확보 못 한 PARTIAL 케이스(예: 미리보기만 있는 영상)
        writer.apply(42L, ItemEnrichment.builder()
                .targetStatus(ItemStatus.PARTIAL)
                .build());   // preview/content/summary 모두 null, categories 없음(→ 빈 목록)

        assertThat(item.getTitle()).isEqualTo("기존제목");
        assertThat(item.getContent()).isNull();
        assertThat(item.getSummary()).isNull();
        assertThat(item.getStatus()).isEqualTo(ItemStatus.PARTIAL);
        // 빈 목록이라도 assign은 호출한다("기타" 폴백은 CategoryAssignmentService가 처리)
        verify(categoryAssignmentService).assign(eq(42L), eq(1L), eq(List.of()));
    }

    @Test
    void 목표상태가_FAILED면_FAILED로_확정한다() {
        Item item = item(ItemStatus.PROCESSING, null);
        when(itemRepository.findById(42L)).thenReturn(Optional.of(item));

        writer.apply(42L, ItemEnrichment.builder().targetStatus(ItemStatus.FAILED).build());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.FAILED);
    }

    @Test
    void PROCESSING을_목표상태로_주면_거부한다() {
        Item item = item(ItemStatus.PROCESSING, null);
        when(itemRepository.findById(42L)).thenReturn(Optional.of(item));

        org.assertj.core.api.Assertions.assertThatThrownBy(() ->
                writer.apply(42L, ItemEnrichment.builder().targetStatus(ItemStatus.PROCESSING).build()))
                .isInstanceOf(IllegalArgumentException.class);

        // 상태 확정 이전 단계는 정상 수행되므로 assign은 호출됨
        verify(categoryAssignmentService).assign(anyLong(), anyLong(), any());
    }
}
