package com.ssafy.woojuin.domain.item.processing;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 아이템 비동기 가공에 필요한 스케줄링을 활성화한다.
 * {@link PendingMessageReclaimer}의 @Scheduled가 동작하려면 필요하다.
 */
@Configuration
@EnableScheduling
public class ItemProcessingConfig {
}
