package com.ssafy.woojuin.domain.item.processing.image;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalysisRequest;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemEnrichment;
import com.ssafy.woojuin.domain.item.processing.ItemEnrichmentWriter;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.processing.ItemProcessor;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.item.service.S3Uploader;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 이미지 아이템 가공 오케스트레이터 (묶음 D).
 *
 * <p>{@code createFromImage}는 S3 업로드 성공 후에만 Item을 만들기 때문에 이 프로세서가 도는
 * 시점엔 원본 이미지가 항상 존재한다 — URL의 트랙 A(미리보기)에 대응하며 항상 성공한다고 볼 수
 * 있다. OCR(트랙 B에 대응)로 텍스트를 확보하면 DONE, 실패·빈 결과면 PARTIAL. 이 프로세서에서
 * FAILED는 발생하지 않는다.
 *
 * <p>AI 보강은 OCR 결과 유무와 무관하게 항상 시도한다(텍스트가 없으면 title만으로 분류 —
 * UrlItemProcessor와 동일 계약).
 *
 * <p><b>트랜잭션 경계</b>: S3 다운로드·OCR·AI 호출은 네트워크 I/O라 트랜잭션 밖에서 하고,
 * DB 반영만 {@link ItemEnrichmentWriter}의 짧은 트랜잭션에 맡긴다(커넥션 장기 점유 방지).
 */
@Slf4j
@Component
public class ImageItemProcessor implements ItemProcessor {

    private final ItemRepository itemRepository;
    private final S3Uploader s3Uploader;
    private final ImageTextExtractor imageTextExtractor;
    private final AiAnalyzer aiAnalyzer;
    private final CategoryAssignmentService categoryAssignmentService;
    private final ItemEnrichmentWriter enrichmentWriter;

    public ImageItemProcessor(ItemRepository itemRepository, S3Uploader s3Uploader,
            ImageTextExtractor imageTextExtractor, AiAnalyzer aiAnalyzer,
            CategoryAssignmentService categoryAssignmentService,
            ItemEnrichmentWriter enrichmentWriter) {
        this.itemRepository = itemRepository;
        this.s3Uploader = s3Uploader;
        this.imageTextExtractor = imageTextExtractor;
        this.aiAnalyzer = aiAnalyzer;
        this.categoryAssignmentService = categoryAssignmentService;
        this.enrichmentWriter = enrichmentWriter;
    }

    @Override
    public boolean supports(ItemType type) {
        return type == ItemType.IMAGE;
    }

    @Override
    public void process(ItemProcessingMessage message) {
        Item item = itemRepository.findById(message.itemId()).orElse(null);
        if (item == null) {
            log.warn("가공할 아이템이 없음(삭제됨?): itemId={}", message.itemId());
            return;
        }
        if (item.getStatus() != ItemStatus.PROCESSING) {
            // at-least-once 큐 특성상 이미 끝난 메시지가 재배달될 수 있다. 값비싼 다운로드·OCR·AI를
            // 반복하지 않도록 여기서 미리 막는다(반영 단계에서 한 번 더 권위 있게 재확인한다).
            log.info("이미 처리된 아이템, 재처리 스킵: itemId={}, status={}", item.getId(), item.getStatus());
            return;
        }

        // 네트워크 단계(트랜잭션 밖): S3 다운로드 + OCR + AI. 텍스트 확보 여부로 상태를 정한다.
        String text = downloadAndExtract(item.getS3Key());
        boolean textAcquired = text != null;
        AiAnalysis analysis = analyzeQuietly(item, text);

        enrichmentWriter.apply(message.itemId(), ItemEnrichment.builder()
                .content(text)
                .summary(analysis.summary())
                .categories(analysis.categories())
                .targetStatus(textAcquired ? ItemStatus.DONE : ItemStatus.PARTIAL)
                .build());
        log.info("이미지 가공 완료: itemId={}, textAcquired={}", message.itemId(), textAcquired);
    }

    /**
     * S3에서 원본을 읽어 OCR로 텍스트를 뽑는다. 다운로드·OCR 어느 쪽이 실패해도 이미지 자체는
     * 이미 S3에 있으므로 null만 반환하고 조용히 넘어간다.
     */
    private String downloadAndExtract(String s3Key) {
        try {
            byte[] bytes = s3Uploader.download(s3Key);
            String text = imageTextExtractor.extract(bytes);
            return (text != null && !text.isBlank()) ? text : null;
        } catch (Exception e) {
            log.info("이미지 다운로드/OCR 실패: cause={}", e.getMessage());
            return null;
        }
    }

    /**
     * AI 요약·분류를 시도한다. 어떤 실패도 이미 확보한 이미지·본문을 무효화하면 안 되므로
     * 조용히 흡수하고 빈 결과를 돌려준다(UrlItemProcessor.analyzeQuietly와 동일 패턴).
     */
    private AiAnalysis analyzeQuietly(Item item, String text) {
        try {
            List<String> candidates = categoryAssignmentService.candidateNames(item.getWorkspaceId());
            return aiAnalyzer.analyze(new AiAnalysisRequest(item.getTitle(), text, candidates));
        } catch (Exception e) {
            log.warn("AI 보강 실패(무시): itemId={}, cause={}", item.getId(), e.toString());
            return AiAnalysis.empty();
        }
    }
}
