package com.ssafy.woojuin.tools;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.woojuin.domain.item.dto.ItemResponse;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.url.ContentExtractor;
import com.ssafy.woojuin.domain.item.processing.url.HtmlFetchException;
import com.ssafy.woojuin.domain.item.processing.url.HtmlFetcher;
import com.ssafy.woojuin.domain.item.processing.url.OEmbedClient;
import com.ssafy.woojuin.domain.item.processing.url.OpenGraphScraper;
import com.ssafy.woojuin.domain.item.processing.url.UrlNormalizer;
import com.ssafy.woojuin.domain.item.processing.url.UrlPreview;
import java.io.BufferedWriter;
import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.nodes.Document;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/**
 * F(AI 분류 모델)가 학습·검증용으로 URL을 많이 넣어봐야 할 때 쓰는 배치 도구.
 * UrlItemProcessor와 <b>같은 추출 컴포넌트</b>를 그대로 재사용해서, 실제 운영에서
 * AiAnalyzer가 받게 될 title/content와 동일한 결과를 뽑아준다 — DB·큐·인증은
 * 거치지 않아 워크스페이스/토큰 준비 없이 바로 돌릴 수 있다.
 *
 * <p>결과는 실제 아이템 응답 DTO({@link ItemResponse})와 동일한 구조로 나간다 —
 * 직접 필드를 나열하지 않고 트랙A/B 결과를 (저장 안 되는) {@link Item}에 그대로
 * 반영한 뒤 {@code ItemResponse.from()}에 태워서, 응답 DTO가 바뀌어도 이 도구가
 * 자동으로 같이 맞는다. itemId/createdAt은 실제로 저장하지 않아 null이고,
 * summary/categories는 AiAnalyzer/CategoryAssignmentService를 안 거쳐 항상
 * null/빈 배열이다 — 그 자리는 F의 몫이라는 뜻.
 *
 * <p>입출력 txt는 {@code backend/url-batch-export/}(input/output) 아래에서 관리한다.
 * docker-compose로 postgres/redis/minio는 떠 있어야 하고, 이미 떠 있는 :8080 서버는
 * 포트 충돌을 피하려면 잠시 내려둘 것.
 * <pre>
 * cd backend
 * ./gradlew bootRun --args="--spring.profiles.active=batch-export --urls=url-batch-export/input/urls.txt --out=url-batch-export/output/export.txt"
 * </pre>
 * urls.txt는 한 줄에 URL 하나(빈 줄/#으로 시작하는 줄은 무시). 결과는 out 경로에
 * JSON Lines(한 줄에 ItemResponse 하나씩)로 쌓인다. 끝나면 프로세스가 자동 종료된다.
 */
@Slf4j
@Component
@Profile("batch-export")
public class UrlBatchExportRunner implements ApplicationRunner {

    private static final int PARALLELISM = 8;

    private final UrlNormalizer urlNormalizer;
    private final OEmbedClient oEmbedClient;
    private final HtmlFetcher htmlFetcher;
    private final OpenGraphScraper openGraphScraper;
    private final ContentExtractor contentExtractor;
    private final ObjectMapper objectMapper;
    private final ConfigurableApplicationContext context;

    public UrlBatchExportRunner(UrlNormalizer urlNormalizer, OEmbedClient oEmbedClient,
            HtmlFetcher htmlFetcher, OpenGraphScraper openGraphScraper,
            ContentExtractor contentExtractor, ObjectMapper objectMapper,
            ConfigurableApplicationContext context) {
        this.urlNormalizer = urlNormalizer;
        this.oEmbedClient = oEmbedClient;
        this.htmlFetcher = htmlFetcher;
        this.openGraphScraper = openGraphScraper;
        this.contentExtractor = contentExtractor;
        this.objectMapper = objectMapper;
        this.context = context;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        String urlsPath = singleOption(args, "urls");
        String outPath = args.containsOption("out")
                ? singleOption(args, "out") : "url-batch-export/output/export.txt";
        if (urlsPath == null) {
            log.error("--urls=<파일경로> 가 필요합니다. 예: --urls=url-batch-export/input/urls.txt");
            exit(1);
            return;
        }

        List<String> urls = Files.readAllLines(Path.of(urlsPath), StandardCharsets.UTF_8).stream()
                .map(String::trim)
                .filter(line -> !line.isBlank() && !line.startsWith("#"))
                .toList();
        log.info("URL {}개 처리 시작 (병렬 {}개), 출력: {}", urls.size(), PARALLELISM, outPath);

        AtomicInteger done = new AtomicInteger();
        AtomicInteger withContent = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(PARALLELISM);
        Object writeLock = new Object();

        try (BufferedWriter writer = Files.newBufferedWriter(Path.of(outPath), StandardCharsets.UTF_8)) {
            List<Runnable> tasks = urls.stream()
                    .<Runnable>map(url -> () -> {
                        ItemResponse response = extract(url);
                        if (response.content() != null) {
                            withContent.incrementAndGet();
                        }
                        try {
                            synchronized (writeLock) {
                                writer.write(objectMapper.writeValueAsString(response));
                                writer.newLine();
                            }
                        } catch (IOException e) {
                            log.error("결과 쓰기 실패: url={}", url, e);
                        }
                        int n = done.incrementAndGet();
                        if (n % 10 == 0 || n == urls.size()) {
                            log.info("진행 {}/{}", n, urls.size());
                        }
                    })
                    .toList();

            for (Runnable task : tasks) {
                pool.submit(task);
            }
            pool.shutdown();
            pool.awaitTermination(30, TimeUnit.MINUTES);
        }

        log.info("완료: 총 {}개 중 본문 확보 {}개, 출력 파일: {}", urls.size(), withContent.get(), outPath);
        exit(0);
    }

    /**
     * UrlItemProcessor.process()의 트랙A/트랙B와 동일한 로직으로 (저장 안 되는) Item을
     * 채운 뒤 실제 응답 DTO로 변환한다. DB/AI/카테고리는 거치지 않는다.
     */
    private ItemResponse extract(String rawUrl) {
        Item item = Item.builder().workspaceId(0L).createdBy(0L).type(ItemType.URL).url(rawUrl).build();
        try {
            String normalizedUrl = urlNormalizer.normalize(rawUrl);

            Document doc = null;
            UrlPreview preview;
            var oembed = oEmbedClient.fetch(normalizedUrl);
            if (oembed.isPresent() && !oembed.get().hasNothing()) {
                preview = oembed.get();
            } else {
                doc = tryFetch(normalizedUrl);
                preview = (doc != null) ? openGraphScraper.scrape(doc) : UrlPreview.empty();
            }
            if (preview.hasNothing()) {
                preview = new UrlPreview(domainOf(normalizedUrl), null, null);
            }
            item.applyPreview(preview.title(), preview.thumbnailUrl(), preview.description());

            String content = (doc != null) ? contentExtractor.extract(doc) : null;
            if (content != null) {
                item.applyContent(content);
                item.markDone();
            } else {
                item.markPartial();
            }
        } catch (Exception e) {
            log.warn("추출 실패: url={}, cause={}", rawUrl, e.toString());
            item.markFailed();
        }
        return ItemResponse.from(item, List.of());
    }

    private Document tryFetch(String url) {
        try {
            return htmlFetcher.fetch(url);
        } catch (HtmlFetchException e) {
            return null;
        }
    }

    private String domainOf(String url) {
        try {
            String host = new URI(url).getHost();
            return host != null ? host : url;
        } catch (Exception e) {
            return url;
        }
    }

    private String singleOption(ApplicationArguments args, String name) {
        List<String> values = args.getOptionValues(name);
        return (values == null || values.isEmpty()) ? null : values.get(0);
    }

    private void exit(int code) {
        System.exit(SpringApplication.exit(context, () -> code));
    }
}
