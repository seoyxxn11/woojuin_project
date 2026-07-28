package com.ssafy.woojuin.domain.item.processing.image;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 묶음 F의 ImageTextExtractor 빈이 아직 없을 때만 NoOp 스텁을 기본 빈으로 올린다.
 * F가 @Component 등으로 실제 구현을 등록하면 @ConditionalOnMissingBean 조건이
 * 어긋나 스텁은 생성되지 않는다.
 */
@Slf4j
@Configuration
public class ImageTextExtractorConfig {

    @Bean
    @ConditionalOnMissingBean(ImageTextExtractor.class)
    public ImageTextExtractor noOpImageTextExtractor() {
        log.info("ImageTextExtractor 스텁(NoOp) 활성화 — 묶음 F의 OCR이 없어 텍스트 추출은 건너뜁니다");
        return new NoOpImageTextExtractor();
    }
}
