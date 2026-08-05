package com.ssafy.woojuin.domain.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * aimix가 켜져 있으면 ai-mix 사이드카 기반 분석기를, 꺼져 있으면 NoOp 스텁을 올린다.
 * 사이드카 없이 백엔드만 돌리는 환경에서도 앱이 뜨고 저장·미리보기·OCR은 그대로
 * 동작하게 하려는 것이다(크롤러의 CRAWLER_ENABLED와 같은 패턴).
 *
 * <p>사이드카가 켜져 있는데 죽어 있는 경우는 여기서 못 거른다 — 그건 호출 시점에
 * {@link AiMixAnalyzer}가 빈 결과로 폴백한다.
 */
@Slf4j
@Configuration
public class AiAnalyzerConfig {

    /**
     * ai-mix HTTP 클라이언트. 분석기 외에 카테고리 설명 생성에도 쓰인다. aimix가 꺼져
     * 있으면 등록하지 않는다 — 쓰는 쪽은 {@link ObjectProvider}로 받아 없으면 건너뛴다.
     */
    @Bean
    @ConditionalOnProperty(name = "woojuin.aimix.enabled", havingValue = "true")
    public AiMixClient aiMixClient(
            ObjectMapper objectMapper,
            @Value("${woojuin.aimix.base-url}") String baseUrl,
            @Value("${woojuin.aimix.timeout-ms}") long timeoutMs) {
        return new AiMixClient(baseUrl, Duration.ofMillis(timeoutMs), objectMapper);
    }

    /**
     * 증분 카테고리(앵커) 엔진 stateless decide 클라이언트(ai-test 사이드카). 상태 전이 판단만
     * 받아오고 DB·Redis 반영은 백엔드가 한다. 켜져 있을 때만 등록한다 — 쓰는 쪽은
     * {@link ObjectProvider}로 받아 없으면 건너뛴다.
     */
    @Bean
    @ConditionalOnProperty(name = "woojuin.category-engine.enabled", havingValue = "true")
    public CategoryEngineClient categoryEngineClient(
            ObjectMapper objectMapper,
            @Value("${woojuin.category-engine.base-url}") String baseUrl,
            @Value("${woojuin.category-engine.timeout-ms}") long timeoutMs) {
        log.info("CategoryEngineClient: 카테고리 엔진 활성화 (baseUrl={})", baseUrl);
        return new CategoryEngineClient(baseUrl, Duration.ofMillis(timeoutMs), objectMapper);
    }

    @Bean
    public AiAnalyzer aiAnalyzer(
            ObjectProvider<AiMixClient> clientProvider,
            @Value("${woojuin.aimix.base-url}") String baseUrl) {
        AiMixClient client = clientProvider.getIfAvailable();
        if (client == null) {
            log.info("AiAnalyzer: aimix가 꺼져 있어 NoOp으로 동작합니다 — 요약·분류를 건너뜁니다"
                    + "(저장·미리보기·OCR은 정상). AIMIX_ENABLED=true로 켜면 활성화됩니다");
            return new NoOpAiAnalyzer();
        }
        log.info("AiAnalyzer: ai-mix 활성화 (baseUrl={})", baseUrl);
        return new AiMixAnalyzer(client);
    }
}
