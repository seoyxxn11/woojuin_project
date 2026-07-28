package com.ssafy.woojuin.domain.item.processing;

import com.ssafy.woojuin.domain.item.entity.ItemType;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.RedisSystemException;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.stream.Consumer;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.ReadOffset;
import org.springframework.data.redis.connection.stream.StreamOffset;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.stream.StreamListener;
import org.springframework.data.redis.stream.StreamMessageListenerContainer;
import org.springframework.data.redis.stream.StreamMessageListenerContainer.StreamMessageListenerContainerOptions;
import org.springframework.stereotype.Component;

/**
 * Redis Streams(woojuin:item-processing) consumer group의 유일한 소비자.
 * 새 메시지를 받아 {@link ItemProcessingDispatcher}에 넘기고, 결과에 따라 ACK를 정한다.
 *
 * <p><b>왜 컨슈머가 하나인가</b> — {@link ItemProcessor} javadoc 참조. 타입별로 컨슈머를
 * 나누면 consumer group의 임의 분배 때문에 URL 메시지가 이미지 워커에게 갈 수 있다.
 *
 * <p>이 컨슈머는 <b>새 메시지(never-delivered)만</b> 처리한다. 처리에 실패해 pending에
 * 남은 메시지의 재시도·최종 포기는 {@link PendingMessageReclaimer}가 맡는다.
 */
@Slf4j
@Component
public class ItemQueueConsumer
        implements StreamListener<String, MapRecord<String, String, String>>,
        InitializingBean, DisposableBean {

    private final RedisConnectionFactory connectionFactory;
    private final StringRedisTemplate redisTemplate;
    private final ItemProcessingDispatcher dispatcher;
    private final String streamKey;
    private final String consumerGroup;
    private final String consumerName;

    private StreamMessageListenerContainer<String, MapRecord<String, String, String>> container;

    public ItemQueueConsumer(
            RedisConnectionFactory connectionFactory,
            StringRedisTemplate redisTemplate,
            ItemProcessingDispatcher dispatcher,
            List<ItemProcessor> processors,
            @Value("${woojuin.queue.stream-key}") String streamKey,
            @Value("${woojuin.queue.consumer-group}") String consumerGroup) {
        this.connectionFactory = connectionFactory;
        this.redisTemplate = redisTemplate;
        this.dispatcher = dispatcher;
        this.streamKey = streamKey;
        this.consumerGroup = consumerGroup;
        // 인스턴스마다 고유해야 pending 추적이 섞이지 않는다. 다중 인스턴스 배포 대비.
        this.consumerName = "consumer-" + UUID.randomUUID().toString().substring(0, 8);
        verifyNoDuplicateProcessors(processors);
    }

    /** 한 타입에 프로세서가 둘이면 어느 쪽이 처리할지 모호하므로 기동을 막는다. */
    private void verifyNoDuplicateProcessors(List<ItemProcessor> processors) {
        for (ItemType type : ItemType.values()) {
            long count = processors.stream().filter(p -> p.supports(type)).count();
            if (count > 1) {
                throw new IllegalStateException(
                        "ItemProcessor가 타입 " + type + "에 " + count + "개 등록됨 — 타입당 하나여야 함");
            }
        }
    }

    @Override
    public void afterPropertiesSet() {
        // 컨테이너를 켜기 전에 consumer group을 보장한다. 그룹이 없는 상태로 XREADGROUP을
        // 시작하면 NOGROUP 에러로 컨테이너가 영구 정지하기 때문이다(신선한 Redis 배포 시).
        createGroupIfAbsent();

        var options = StreamMessageListenerContainerOptions.builder()
                .pollTimeout(Duration.ofSeconds(2))
                .build();
        this.container = StreamMessageListenerContainer.create(connectionFactory, options);
        // ReadOffset.lastConsumed() = 이 그룹이 아직 배달받지 않은 새 메시지(">")부터.
        // 기존 pending은 컨테이너가 자동으로 다시 배달하지 않으므로 PendingMessageReclaimer가 회수한다.
        container.receive(
                Consumer.from(consumerGroup, consumerName),
                StreamOffset.create(streamKey, ReadOffset.lastConsumed()),
                this);
        container.start();
        log.info("아이템 큐 컨슈머 시작: stream={}, group={}, consumer={}",
                streamKey, consumerGroup, consumerName);
    }

    /**
     * consumer group을 생성한다(없으면 스트림도 함께 — createGroup은 MKSTREAM 동작).
     * 이미 있으면(BUSYGROUP) 정상이므로 무시한다.
     */
    private void createGroupIfAbsent() {
        try {
            redisTemplate.opsForStream().createGroup(streamKey, ReadOffset.from("0"), consumerGroup);
            log.info("Redis stream consumer group 생성: stream={}, group={}", streamKey, consumerGroup);
        } catch (RedisSystemException e) {
            Throwable cause = e.getMostSpecificCause();
            if (cause != null && cause.getMessage() != null && cause.getMessage().contains("BUSYGROUP")) {
                log.debug("consumer group 이미 존재: group={}", consumerGroup);
            } else {
                throw e;
            }
        }
    }

    @Override
    public void onMessage(MapRecord<String, String, String> record) {
        ItemProcessingDispatcher.Outcome outcome = dispatcher.handle(record.getValue());
        // PROCESSED/POISON은 ACK로 큐에서 제거. NO_PROCESSOR/RETRYABLE은 pending에 남겨
        // PendingMessageReclaimer가 이어받게 한다.
        if (outcome == ItemProcessingDispatcher.Outcome.PROCESSED
                || outcome == ItemProcessingDispatcher.Outcome.POISON) {
            redisTemplate.opsForStream().acknowledge(consumerGroup, record);
        }
    }

    @Override
    public void destroy() {
        if (container != null) {
            container.stop();
            log.info("아이템 큐 컨슈머 종료: consumer={}", consumerName);
        }
    }
}
