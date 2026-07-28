package com.ssafy.woojuin.domain.item.processing.image;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalysisRequest;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.processing.ItemProcessor;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.item.service.S3Uploader;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 이미지 아이템 가공 오케스트레이터 (묶음 D).
 *
 * <p>{@code createFromImage}는 S3 업로드 성공 후에만 Item을 만들기 때문에 이
 * 프로세서가 도는 시점엔 원본 이미지가 항상 존재한다 — URL의 트랙 A(미리보기)에
 * 대응하며 항상 성공한다고 볼 수 있다. OCR(트랙 B에 대응)로 텍스트를 확보하면
 * DONE, 실패·빈 결과면 PARTIAL. 이 프로세서에서 FAILED는 발생하지 않는다.
 *
 * <p>AI 보강은 OCR 결과 유무와 무관하게 항상 시도한다(텍스트가 없으면 title만으로
 * 분류 — UrlItemProcessor와 동일 계약).
 */
@Slf4j
@Component
public class ImageItemProcessor implements ItemProcessor {

    private final ItemRepository itemRepository;
    private final S3Uploader s3Uploader;
    private final ImageTextExtractor imageTextExtractor;
    private final ImageThumbnailGenerator thumbnailGenerator;
    private final AiAnalyzer aiAnalyzer;
    private final CategoryAssignmentService categoryAssignmentService;

    public ImageItemProcessor(ItemRepository itemRepository, S3Uploader s3Uploader,
            ImageTextExtractor imageTextExtractor, ImageThumbnailGenerator thumbnailGenerator,
            AiAnalyzer aiAnalyzer, CategoryAssignmentService categoryAssignmentService) {
        this.itemRepository = itemRepository;
        this.s3Uploader = s3Uploader;
        this.imageTextExtractor = imageTextExtractor;
        this.thumbnailGenerator = thumbnailGenerator;
        this.aiAnalyzer = aiAnalyzer;
        this.categoryAssignmentService = categoryAssignmentService;
    }

    @Override
    public boolean supports(ItemType type) {
        return type == ItemType.IMAGE;
    }

    @Override
    @Transactional
    public void process(ItemProcessingMessage message) {
        Item item = itemRepository.findById(message.itemId()).orElse(null);
        if (item == null) {
            log.warn("가공할 아이템이 없음(삭제됨?): itemId={}", message.itemId());
            return;
        }
        if (item.getStatus() != ItemStatus.PROCESSING) {
            // at-least-once 큐 특성상 이미 끝난 메시지가 재배달될 수 있다.
            // AI를 또 호출하지 않도록 여기서 막는다.
            log.info("이미 처리된 아이템, 재처리 스킵: itemId={}, status={}", item.getId(), item.getStatus());
            return;
        }

        // 원본을 한 번만 내려받아 OCR과 썸네일 생성에 함께 쓴다.
        byte[] bytes = tryDownload(item.getS3Key());
        String text = tryExtract(bytes);
        boolean textAcquired = text != null;
        if (textAcquired) {
            item.applyContent(text);
        }

        tryGenerateThumbnail(item, bytes);
        enrichWithAi(item, text);
        finalizeStatus(item, textAcquired);
    }

    /** S3 원본 바이트를 읽는다. 실패해도 이미지 자체는 S3에 있으므로 null만 반환하고 넘어간다. */
    private byte[] tryDownload(String s3Key) {
        try {
            return s3Uploader.download(s3Key);
        } catch (Exception e) {
            log.info("이미지 다운로드 실패: cause={}", e.getMessage());
            return null;
        }
    }

    /** OCR로 텍스트를 뽑는다. 바이트가 없거나 OCR이 실패/빈 결과면 null. */
    private String tryExtract(byte[] bytes) {
        if (bytes == null) {
            return null;
        }
        try {
            String text = imageTextExtractor.extract(bytes);
            return (text != null && !text.isBlank()) ? text : null;
        } catch (Exception e) {
            log.info("OCR 실패: cause={}", e.getMessage());
            return null;
        }
    }

    /**
     * 목록 카드용 webp 썸네일을 만들어 S3에 올리고 thumbnailS3Key를 저장한다. 최적화지
     * 필수 경로가 아니므로 어떤 실패도(리사이즈·업로드) 조용히 흡수한다 — 썸네일이 없으면
     * 목록은 원본 presigned로 폴백한다(ItemService.thumbnailImageUrlOf). 상태에는 영향 없다.
     */
    private void tryGenerateThumbnail(Item item, byte[] bytes) {
        if (bytes == null) {
            return;
        }
        try {
            byte[] thumbnail = thumbnailGenerator.toThumbnail(bytes);
            if (thumbnail != null) {
                item.applyThumbnail(s3Uploader.uploadThumbnail(thumbnail, item.getS3Key()));
            }
        } catch (Exception e) {
            log.warn("썸네일 생성 실패(무시), 목록은 원본으로 폴백: itemId={}, cause={}", item.getId(), e.toString());
        }
    }

    /**
     * AI 요약·분류를 반영한다. 어떤 실패도 이미 확보한 이미지·본문을 무효화하면
     * 안 되므로 조용히 흡수한다(UrlItemProcessor.enrichWithAi와 동일 패턴).
     */
    private void enrichWithAi(Item item, String text) {
        try {
            List<String> candidates = categoryAssignmentService.candidateNames(item.getWorkspaceId());
            AiAnalysis analysis = aiAnalyzer.analyze(
                    new AiAnalysisRequest(item.getTitle(), text, candidates));
            item.applySummary(analysis.summary());
            categoryAssignmentService.assign(item.getId(), item.getWorkspaceId(), analysis.categories());
        } catch (Exception e) {
            log.warn("AI 보강 실패(무시): itemId={}, cause={}", item.getId(), e.toString());
        }
    }

    private void finalizeStatus(Item item, boolean textAcquired) {
        if (textAcquired) {
            item.markDone();
        } else {
            item.markPartial();
        }
        log.info("이미지 가공 완료: itemId={}, status={}", item.getId(), item.getStatus());
    }
}
