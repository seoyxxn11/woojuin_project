package com.ssafy.woojuin.domain.item.processing.image;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.item.service.S3Uploader;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ImageItemProcessorTest {

    @Mock ItemRepository itemRepository;
    @Mock S3Uploader s3Uploader;
    @Mock ImageTextExtractor imageTextExtractor;
    @Mock ImageThumbnailGenerator thumbnailGenerator;
    @Mock AiAnalyzer aiAnalyzer;
    @Mock CategoryAssignmentService categoryAssignmentService;

    ImageItemProcessor processor;

    private Item imageItem() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.IMAGE)
                .s3Key("items/1/abc-photo.png").build();
        when(itemRepository.findById(any())).thenReturn(Optional.of(item));
        return item;
    }

    private ItemProcessingMessage message() {
        return new ItemProcessingMessage(1L, 1L, ItemType.IMAGE);
    }

    private void newProcessor() {
        processor = new ImageItemProcessor(itemRepository, s3Uploader, imageTextExtractor,
                thumbnailGenerator, aiAnalyzer, categoryAssignmentService);
    }

    @Test
    void 아이템이_사라졌으면_조용히_반환한다() {
        newProcessor();
        when(itemRepository.findById(any())).thenReturn(Optional.empty());

        processor.process(message());

        verifyNoInteractions(s3Uploader, imageTextExtractor, thumbnailGenerator, aiAnalyzer,
                categoryAssignmentService);
    }

    @Test
    void 다운로드와_OCR_성공하면_본문저장하고_DONE() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenReturn(new byte[]{1, 2, 3});
        when(imageTextExtractor.extract(any())).thenReturn("이미지에서 뽑은 텍스트");
        when(aiAnalyzer.analyze(any())).thenReturn(AiAnalysis.empty());

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
        assertThat(item.getContent()).isEqualTo("이미지에서 뽑은 텍스트");
    }

    @Test
    void 다운로드가_예외를_던지면_PARTIAL이고_본문없음() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenThrow(new IllegalStateException("S3 접근 실패"));
        when(aiAnalyzer.analyze(any())).thenReturn(AiAnalysis.empty());

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.PARTIAL);
        assertThat(item.getContent()).isNull();
    }

    @Test
    void OCR이_null을_반환하면_PARTIAL() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenReturn(new byte[]{1});
        when(imageTextExtractor.extract(any())).thenReturn(null);
        when(aiAnalyzer.analyze(any())).thenReturn(AiAnalysis.empty());

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.PARTIAL);
        assertThat(item.getContent()).isNull();
        // 본문이 없어도 분류는 시도한다(title 기반)
        verify(categoryAssignmentService).assign(eq(item.getId()), eq(1L), any());
    }

    @Test
    void OCR_성공했지만_AI_보강이_실패해도_상태는_DONE_유지() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenReturn(new byte[]{1});
        when(imageTextExtractor.extract(any())).thenReturn("텍스트");
        when(aiAnalyzer.analyze(any())).thenThrow(new RuntimeException("AI 서버 장애"));

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
        assertThat(item.getSummary()).isNull();
    }

    @Test
    void AI가_요약과_카테고리를_주면_저장한다() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenReturn(new byte[]{1});
        when(imageTextExtractor.extract(any())).thenReturn("텍스트");
        when(aiAnalyzer.analyze(any())).thenReturn(new AiAnalysis("요약문", List.of("문화·콘텐츠")));

        processor.process(message());

        assertThat(item.getSummary()).isEqualTo("요약문");
        verify(categoryAssignmentService).assign(eq(item.getId()), eq(1L), eq(List.of("문화·콘텐츠")));
    }

    @Test
    void 이미_처리된_아이템은_재처리하지_않는다() {
        newProcessor();
        Item item = imageItem();
        item.markPartial();   // at-least-once 큐 재배달 시나리오 시뮬레이션

        processor.process(message());

        verifyNoInteractions(s3Uploader, imageTextExtractor, thumbnailGenerator, aiAnalyzer,
                categoryAssignmentService);
    }

    @Test
    void 썸네일_생성에_성공하면_thumbnailS3Key를_저장한다() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenReturn(new byte[]{1});
        when(imageTextExtractor.extract(any())).thenReturn("텍스트");
        when(aiAnalyzer.analyze(any())).thenReturn(AiAnalysis.empty());
        when(thumbnailGenerator.toThumbnail(any())).thenReturn(new byte[]{9, 9});
        when(s3Uploader.uploadThumbnail(any(), eq("items/1/abc-photo.png")))
                .thenReturn("items/1/abc-photo.png.thumb.webp");

        processor.process(message());

        assertThat(item.getThumbnailS3Key()).isEqualTo("items/1/abc-photo.png.thumb.webp");
    }

    @Test
    void 썸네일_생성이_실패해도_상태와_본문에_영향없다() {
        newProcessor();
        Item item = imageItem();
        when(s3Uploader.download(any())).thenReturn(new byte[]{1});
        when(imageTextExtractor.extract(any())).thenReturn("텍스트");
        when(aiAnalyzer.analyze(any())).thenReturn(AiAnalysis.empty());
        when(thumbnailGenerator.toThumbnail(any())).thenThrow(new IllegalStateException("scrimage 실패"));

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
        assertThat(item.getContent()).isEqualTo("텍스트");
        assertThat(item.getThumbnailS3Key()).isNull();
    }
}
