package com.ssafy.woojuin.global.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.auditing.DateTimeProvider;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

import java.time.OffsetDateTime;
import java.util.Optional;

/**
 * 기본 DateTimeProvider는 LocalDateTime을 생성하는데, BaseTimeEntity는
 * OffsetDateTime 컬럼이라 그대로 두면 저장 시점에 타입 변환 에러가 난다.
 */
@Configuration
@EnableJpaAuditing(dateTimeProviderRef = "auditingDateTimeProvider")
public class JpaAuditingConfig {

    @Bean
    public DateTimeProvider auditingDateTimeProvider() {
        return () -> Optional.of(OffsetDateTime.now());
    }
}
