package com.ssafy.woojuin.domain.item.processing.url;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalysisRequest;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemEnrichment;
import com.ssafy.woojuin.domain.item.processing.ItemEnrichmentWriter;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.processing.ItemProcessor;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.net.URI;
import java.util.List;
import java.util.Optional;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.nodes.Document;
import org.springframework.stereotype.Component;

/**
 * URL 아이템 가공 오케스트레이터 (묶음 D).
 *
 * <p><b>트랙 A(미리보기)</b>: 정규화 → oEmbed(알려진 제공자) → 실패 시 HTML fetch + OG
 * 스크래핑 → 그래도 없으면 도메인명 폴백. 거의 항상 최소 미리보기를 만든다.
 *
 * <p><b>트랙 B(본문 확보)</b>: 트랙 A가 받아둔 Document를 재활용해 readability4j로 본문을
 * 뽑는다. 두 트랙은 완전히 격리돼 한쪽 실패가 다른 쪽에 영향을 주지 않는다.
 *
 * <p><b>AI 보강</b>: 본문이 없어도(PARTIAL) title만으로 분류하도록 항상 시도한다. 요약은
 * 본문이 있을 때만 채워지고, 카테고리는 그 워크스페이스의 현재 카테고리 중에서 배정된다.
 *
 * <p><b>트랜잭션 경계</b>: oEmbed·HTML fetch·본문 추출·AI 호출은 네트워크 I/O라 트랜잭션
 * 밖에서 하고, DB 반영만 {@link ItemEnrichmentWriter}의 짧은 트랜잭션에 맡긴다(커넥션 장기
 * 점유 방지). 반영 시 미리보기·본문·요약·카테고리·상태가 한 트랜잭션에서 함께 커밋된다.
 *
 * <p><b>상태 전이</b>는 AGENTS.md 정의를 따른다 — 트랙 B(콘텐츠) 성공 여부로만 정한다.
 * <ul>
 *   <li>트랙 B 성공 → DONE</li>
 *   <li>트랙 A만 성공(트랙 B 실패) → PARTIAL</li>
 *   <li>트랙 A조차 실패(도메인 폴백도 불가) → FAILED (사실상 URL 파싱 불가일 때만)</li>
 * </ul>
 */
@Slf4j
@Component
public class UrlItemProcessor implements ItemProcessor {

    private final ItemRepository itemRepository;
    private final UrlNormalizer urlNormalizer;
    private final OEmbedClient oEmbedClient;
    private final HtmlFetcher htmlFetcher;
    private final OpenGraphScraper openGraphScraper;
    private final ContentExtractor contentExtractor;
    private final AiAnalyzer aiAnalyzer;
    private final CategoryAssignmentService categoryAssignmentService;
    private final ItemEnrichmentWriter enrichmentWriter;

    public UrlItemProcessor(ItemRepository itemRepository, UrlNormalizer urlNormalizer,
            OEmbedClient oEmbedClient, HtmlFetcher htmlFetcher, OpenGraphScraper openGraphScraper,
            ContentExtractor contentExtractor, AiAnalyzer aiAnalyzer,
            CategoryAssignmentService categoryAssignmentService,
            ItemEnrichmentWriter enrichmentWriter) {
        this.itemRepository = itemRepository;
        this.urlNormalizer = urlNormalizer;
        this.oEmbedClient = oEmbedClient;
        this.htmlFetcher = htmlFetcher;
        this.openGraphScraper = openGraphScraper;
        this.contentExtractor = contentExtractor;
        this.aiAnalyzer = aiAnalyzer;
        this.categoryAssignmentService = categoryAssignmentService;
        this.enrichmentWriter = enrichmentWriter;
    }

    @Override
    public boolean supports(ItemType type) {
        return type == ItemType.URL;
    }

    @Override
    public void process(ItemProcessingMessage message) {
        Item item = itemRepository.findById(message.itemId()).orElse(null);
        if (item == null) {
            log.warn("가공할 아이템이 없음(삭제됨?): itemId={}", message.itemId());
            return;
        }
        if (item.getStatus() != ItemStatus.PROCESSING) {
            // at-least-once 큐 특성상 이미 끝난 메시지가 재배달될 수 있다. 값비싼 fetch·추출·AI를
            // 반복하지 않도록 여기서 미리 막는다(반영 단계에서 한 번 더 권위 있게 재확인한다).
            log.info("이미 처리된 아이템, 재처리 스킵: itemId={}, status={}", item.getId(), item.getStatus());
            return;
        }

        String normalizedUrl = urlNormalizer.normalize(item.getUrl());

        // 트랙 A: 미리보기. OG 스크래핑에 쓴 Document는 트랙 B가 재활용하도록 넘겨받는다.
        Document doc = null;
        UrlPreview preview;
        Optional<UrlPreview> oembed = oEmbedClient.fetch(normalizedUrl);
        if (oembed.isPresent() && !oembed.get().hasNothing()) {
            preview = oembed.get();   // 미디어 제공자는 본문이 없어 트랙 B 대상이 아니다(doc=null)
        } else {
            doc = tryFetch(normalizedUrl);
            preview = (doc != null) ? openGraphScraper.scrape(doc) : UrlPreview.empty();
        }
        if (preview.hasNothing()) {
            preview = new UrlPreview(domainOf(normalizedUrl), null, null);
        }

        // 트랙 B: 본문 확보. Document가 없으면(oEmbed 경로/트랙 A fetch 실패) 본문도 없다.
        String content = (doc != null) ? contentExtractor.extract(doc) : null;
        boolean contentAcquired = content != null;

        // AI 보강(네트워크). title이 비어 있으면 미리보기 제목을 분류 힌트로 넘긴다
        // (applyPreview가 title을 채우는 규칙과 동일). 본문이 없어도 title로 분류 시도한다.
        String titleForAi = hasText(item.getTitle()) ? item.getTitle() : preview.title();
        AiAnalysis analysis = analyzeQuietly(item, titleForAi, content);

        ItemStatus target = contentAcquired ? ItemStatus.DONE
                : (!preview.hasNothing() ? ItemStatus.PARTIAL : ItemStatus.FAILED);

        enrichmentWriter.apply(message.itemId(), ItemEnrichment.builder()
                .previewTitle(preview.title())
                .previewThumbnailUrl(preview.thumbnailUrl())
                .previewDescription(preview.description())
                .content(content)
                .summary(analysis.summary())
                .categories(analysis.categories())
                .targetStatus(target)
                .build());
        log.info("URL 가공 완료: itemId={}, status={}", message.itemId(), target);
    }

    private Document tryFetch(String url) {
        try {
            return htmlFetcher.fetch(url);
        } catch (HtmlFetchException e) {
            log.info("HTML fetch 실패: url={}, cause={}", url, e.getMessage());
            return null;
        }
    }

    /**
     * AI 요약·분류를 시도한다. 후보 카테고리(그 워크스페이스의 현재 목록)를 넘겨 결과를 받는다.
     * 어떤 실패도 이미 확보한 본문·미리보기를 무효화하면 안 되므로 조용히 흡수하고 빈 결과를 돌려준다.
     */
    private AiAnalysis analyzeQuietly(Item item, String title, String content) {
        try {
            List<String> candidates = categoryAssignmentService.candidateNames(item.getWorkspaceId());
            return aiAnalyzer.analyze(new AiAnalysisRequest(title, content, candidates));
        } catch (Exception e) {
            log.warn("AI 보강 실패(무시): itemId={}, cause={}", item.getId(), e.toString());
            return AiAnalysis.empty();
        }
    }

    private static boolean hasText(String s) {
        return s != null && !s.isBlank();
    }

    private String domainOf(String url) {
        try {
            String host = new URI(url).getHost();
            return host != null ? host : url;
        } catch (Exception e) {
            return url;
        }
    }
}
