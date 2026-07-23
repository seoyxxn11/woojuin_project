package com.ssafy.woojuin.tools;

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
 * <p>입출력 txt는 {@code backend/url-batch-export/}(input/output) 아래에서 관리한다.
 * docker-compose로 postgres/redis/minio는 떠 있어야 하고, 이미 떠 있는 :8080 서버는
 * 포트 충돌을 피하려면 잠시 내려둘 것.
 * <pre>
 * cd backend
 * ./gradlew bootRun --args="--spring.profiles.active=batch-export --urls=url-batch-export/input/urls.txt --out=url-batch-export/output/export.txt"
 * </pre>
 * urls.txt는 한 줄에 URL 하나(빈 줄/#으로 시작하는 줄은 무시). 결과는 out 경로에
 * 탭으로 구분된 txt로 쌓인다 — 헤더 한 줄(url\ttitle\tcontent) 뒤로 URL당 한 줄.
 * 끝나면 프로세스가 자동 종료된다.
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
    private final ConfigurableApplicationContext context;

    public UrlBatchExportRunner(UrlNormalizer urlNormalizer, OEmbedClient oEmbedClient,
            HtmlFetcher htmlFetcher, OpenGraphScraper openGraphScraper,
            ContentExtractor contentExtractor, ConfigurableApplicationContext context) {
        this.urlNormalizer = urlNormalizer;
        this.oEmbedClient = oEmbedClient;
        this.htmlFetcher = htmlFetcher;
        this.openGraphScraper = openGraphScraper;
        this.contentExtractor = contentExtractor;
        this.context = context;
    }

    private record ExportResult(String url, String title, String content, boolean hasContent) {
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
            writeRow(writer, "url", "title", "content");   // 헤더

            List<Runnable> tasks = urls.stream()
                    .<Runnable>map(url -> () -> {
                        ExportResult result = extract(url);
                        if (result.hasContent()) {
                            withContent.incrementAndGet();
                        }
                        try {
                            synchronized (writeLock) {
                                writeRow(writer, result.url(), result.title(), result.content());
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

    /** UrlItemProcessor.process()의 트랙A/트랙B와 동일한 로직 — DB/AI/카테고리 없이 추출만. */
    private ExportResult extract(String rawUrl) {
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

            String content = (doc != null) ? contentExtractor.extract(doc) : null;
            return new ExportResult(rawUrl, preview.title(), content, content != null);
        } catch (Exception e) {
            log.warn("추출 실패: url={}, cause={}", rawUrl, e.toString());
            return new ExportResult(rawUrl, null, null, false);
        }
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

    /**
     * TSV 한 줄을 쓴다. content는 이미 ContentExtractor가 공백류를 한 칸으로
     * 뭉개둬서 개행은 안 남지만, title은 확실치 않으니 탭/개행을 방어적으로 지운다.
     */
    private void writeRow(BufferedWriter writer, String url, String title, String content) throws IOException {
        writer.write(tsvSafe(url) + "\t" + tsvSafe(title) + "\t" + tsvSafe(content));
        writer.newLine();
    }

    private String tsvSafe(String value) {
        return value == null ? "" : value.replaceAll("[\\t\\r\\n]+", " ").trim();
    }

    private String singleOption(ApplicationArguments args, String name) {
        List<String> values = args.getOptionValues(name);
        return (values == null || values.isEmpty()) ? null : values.get(0);
    }

    private void exit(int code) {
        System.exit(SpringApplication.exit(context, () -> code));
    }
}
