package com.ssafy.woojuin.domain.item.service;

import com.ssafy.woojuin.domain.item.entity.ItemType;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * 저장 직후 아이템을 Redis Streams(woojuin:item-processing)에 적재한다.
 * 실제 소비(트랙 A/B AI 가공)는 이 번들(묶음 C) 범위 밖 — 묶음 D/F 담당.
 */
@Component
public class ItemQueueProducer {

    private final StringRedisTemplate redisTemplate;
    private final String streamKey;

    public ItemQueueProducer(
            StringRedisTemplate redisTemplate,
            @Value("${woojuin.queue.stream-key}") String streamKey) {
        this.redisTemplate = redisTemplate;
        this.streamKey = streamKey;
    }

    /**
     * 트랜잭션 안에서 호출되면 커밋 이후로 발행을 미룬다. 커밋 전에 발행하면 컨슈머가
     * 메시지를 먼저 받아 아직 커밋되지 않은 아이템을 조회해 실패할 수 있고, 롤백 시에는
     * 존재하지 않을 아이템을 가리키는 고아 메시지가 남는다.
     */
    public void publish(Long itemId, Long workspaceId, ItemType type) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    doPublish(itemId, workspaceId, type);
                }
            });
            return;
        }
        doPublish(itemId, workspaceId, type);
    }

    private void doPublish(Long itemId, Long workspaceId, ItemType type) {
        redisTemplate.opsForStream().add(streamKey, Map.of(
                "itemId", String.valueOf(itemId),
                "workspaceId", String.valueOf(workspaceId),
                "type", type.name()));
    }
}
