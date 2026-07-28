package com.ssafy.woojuin.domain.item.processing;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.PendingMessage;
import org.springframework.data.redis.connection.stream.PendingMessages;
import org.springframework.data.redis.connection.stream.RecordId;
import org.springframework.data.redis.core.StreamOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 처리에 실패해 pending에 남은 메시지를 주기적으로 회수한다. 컨슈머는 새 메시지만 받고
 * pending을 다시 배달하지 않으므로, 재시도는 전적으로 이 스케줄러가 담당한다.
 *
 * <p>한 사이클에서 idle 기준을 넘긴 pending 각각에 대해:
 * <ul>
 *   <li>담당 프로세서가 없는 타입(F 미구현) → 건드리지 않는다(카운트/포기 대상 아님)</li>
 *   <li>배달 횟수가 상한 이상 → 재시도해도 안 되는 것으로 보고 FAILED 확정 후 ACK</li>
 *   <li>그 외 → 자신에게 claim(배달 횟수 +1)하고 재처리. 성공 ACK, 실패면 pending 유지</li>
 * </ul>
 * 배달 횟수는 claim마다 증가하므로, 실패가 반복되면 결국 상한에 닿아 FAILED로 수렴한다.
 */
@Slf4j
@Component
public class PendingMessageReclaimer {

    private final StringRedisTemplate redisTemplate;
    private final ItemProcessingDispatcher dispatcher;
    private final String streamKey;
    private final String consumerGroup;
    private final String consumerName;
    private final int maxDelivery;
    private final long idleThresholdMs;
    private final int batchSize;

    public PendingMessageReclaimer(
            StringRedisTemplate redisTemplate,
            ItemProcessingDispatcher dispatcher,
            @Value("${woojuin.queue.stream-key}") String streamKey,
            @Value("${woojuin.queue.consumer-group}") String consumerGroup,
            @Value("${woojuin.queue.max-delivery:3}") int maxDelivery,
            @Value("${woojuin.queue.reclaim-idle-ms:60000}") long idleThresholdMs,
            @Value("${woojuin.queue.reclaim-batch-size:32}") int batchSize) {
        this.redisTemplate = redisTemplate;
        this.dispatcher = dispatcher;
        this.streamKey = streamKey;
        this.consumerGroup = consumerGroup;
        this.consumerName = "reclaimer-" + UUID.randomUUID().toString().substring(0, 8);
        this.maxDelivery = maxDelivery;
        this.idleThresholdMs = idleThresholdMs;
        this.batchSize = batchSize;
    }

    @Scheduled(fixedDelayString = "${woojuin.queue.reclaim-interval-ms:30000}")
    public void reclaim() {
        StreamOperations<String, String, String> ops = redisTemplate.opsForStream();
        PendingMessages pending;
        try {
            pending = ops.pending(streamKey, consumerGroup, Range.unbounded(), batchSize);
        } catch (Exception e) {
            // 스트림/그룹이 아직 없거나 Redis 일시 장애 — 다음 주기에 다시 시도한다.
            log.debug("pending 조회 실패, 다음 주기 재시도: {}", e.toString());
            return;
        }

        for (PendingMessage pm : pending) {
            if (pm.getElapsedTimeSinceLastDelivery().toMillis() < idleThresholdMs) {
                continue;   // 아직 처리 중일 수 있으니 유예
            }
            reclaimOne(ops, pm);
        }
    }

    private void reclaimOne(StreamOperations<String, String, String> ops, PendingMessage pm) {
        String id = pm.getIdAsString();

        List<MapRecord<String, String, String>> records = ops.range(streamKey, Range.closed(id, id));
        if (records == null || records.isEmpty()) {
            // 스트림에서 트림됐는데 PEL에만 남은 유령 엔트리 → 정리한다.
            ops.acknowledge(streamKey, consumerGroup, id);
            return;
        }
        MapRecord<String, String, String> record = records.get(0);

        ItemProcessingMessage message;
        try {
            message = ItemProcessingMessage.from(record.getValue());
        } catch (IllegalArgumentException e) {
            log.error("pending 독약 메시지 폐기: id={}, value={}", id, record.getValue());
            ops.acknowledge(streamKey, consumerGroup, id);
            return;
        }

        // 담당 프로세서가 없으면(F 미구현 타입) 재시도 카운트를 올리지 않고 그대로 둔다.
        if (dispatcher.findProcessor(message) == null) {
            return;
        }

        // 이미 충분히 배달됐다면 포기. claim으로 카운트를 더 올리기 전에 판단한다.
        if (pm.getTotalDeliveryCount() >= maxDelivery) {
            dispatcher.markFailed(message.itemId());
            ops.acknowledge(streamKey, consumerGroup, id);
            return;
        }

        // 자신에게 claim(배달 횟수 +1)한 뒤 재처리.
        List<MapRecord<String, String, String>> claimed = ops.claim(streamKey, consumerGroup, consumerName,
                Duration.ofMillis(idleThresholdMs), RecordId.of(id));
        if (claimed == null || claimed.isEmpty()) {
            return;   // 그 사이 다른 소비자가 가져감
        }

        ItemProcessingDispatcher.Outcome outcome = dispatcher.handle(claimed.get(0).getValue());
        if (outcome == ItemProcessingDispatcher.Outcome.PROCESSED
                || outcome == ItemProcessingDispatcher.Outcome.POISON) {
            ops.acknowledge(streamKey, consumerGroup, id);
        }
        // RETRYABLE/NO_PROCESSOR → pending 유지, 다음 주기에 배달 횟수가 올라 결국 상한에 닿는다.
    }
}
