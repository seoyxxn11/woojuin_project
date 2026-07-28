package com.ssafy.woojuin.domain.item.processing.url;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalysisRequest;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.processing.ItemProcessor;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.net.URI;
import java.util.List;
import java.util.Optional;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.nodes.Document;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

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
 * 보강 실패는 이미 확보한 미리보기·본문을 무효화하지 않는다.
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

    public UrlItemProcessor(ItemRepository itemRepository, UrlNormalizer urlNormalizer,
            OEmbedClient oEmbedClient, HtmlFetcher htmlFetcher, OpenGraphScraper openGraphScraper,
            ContentExtractor contentExtractor, AiAnalyzer aiAnalyzer,
            CategoryAssignmentService categoryAssignmentService) {
        this.itemRepository = itemRepository;
        this.urlNormalizer = urlNormalizer;
        this.oEmbedClient = oEmbedClient;
        this.htmlFetcher = htmlFetcher;
        this.openGraphScraper = openGraphScraper;
        this.contentExtractor = contentExtractor;
        this.aiAnalyzer = aiAnalyzer;
        this.categoryAssignmentService = categoryAssignmentService;
    }

    @Override
    public boolean supports(ItemType type) {
        return type == ItemType.URL;
    }

    /**
     * @Transactional이라 JPA 더티체킹으로 변경이 flush되고, 미리보기·본문·요약·카테고리가
     * 한 트랜잭션에서 함께 커밋된다. 아이템이 사라졌으면(저장과 처리 사이 삭제) 조용히
     * 반환한다 — 재시도해도 다시 생기지 않으므로 예외를 던지지 않는다.
     */
    @Override
    @Transactional
    public void process(ItemProcessingMessage message) {
        Item item = itemRepository.findById(message.itemId()).orElse(null);
        if (item == null) {
            log.warn("가공할 아이템이 없음(삭제됨?): itemId={}", message.itemId());
            return;
        }
        if (item.getStatus() != ItemStatus.PROCESSING) {
            // DB 커밋은 됐는데 큐 ACK 직전에 죽는 등 at-least-once 큐 특성상 이미 끝난
            // 메시지가 재배달될 수 있다. AI를 또 호출하지 않도록 여기서 막는다.
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
        item.applyPreview(preview.title(), preview.thumbnailUrl(), preview.description());

        // 트랙 B: 본문 확보. Document가 없으면(oEmbed 경로/트랙 A fetch 실패) 본문도 없다.
        String content = (doc != null) ? contentExtractor.extract(doc) : null;
        boolean contentAcquired = content != null;
        if (contentAcquired) {
            item.applyContent(content);
        }

        enrichWithAi(item, content);   // 본문이 없어도 title로 분류 시도(상태에는 영향 없음)
        finalizeStatus(item, preview, contentAcquired);
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
     * AI 요약·분류를 반영한다. 후보 카테고리(그 워크스페이스의 현재 목록)를 넘기고, 결과
     * 요약을 저장하며, 분류된 카테고리를 아이템에 연결한다. 어떤 실패도 이미 확보한 본문·
     * 미리보기를 무효화하면 안 되므로 조용히 흡수한다.
     */
    private void enrichWithAi(Item item, String content) {
        try {
            List<String> candidates = categoryAssignmentService.candidateNames(item.getWorkspaceId());
            AiAnalysis analysis = aiAnalyzer.analyze(
                    new AiAnalysisRequest(item.getTitle(), content, candidates));
            item.applySummary(analysis.summary());
            categoryAssignmentService.assign(item.getId(), item.getWorkspaceId(), analysis.categories());
        } catch (Exception e) {
            log.warn("AI 보강 실패(무시): itemId={}, cause={}", item.getId(), e.toString());
        }
    }

    private void finalizeStatus(Item item, UrlPreview preview, boolean contentAcquired) {
        if (contentAcquired) {
            item.markDone();
        } else if (!preview.hasNothing()) {
            item.markPartial();
        } else {
            item.markFailed();   // 도메인 폴백조차 비었을 때 — 사실상 URL 파싱 불가
        }
        log.info("URL 가공 완료: itemId={}, status={}", item.getId(), item.getStatus());
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
