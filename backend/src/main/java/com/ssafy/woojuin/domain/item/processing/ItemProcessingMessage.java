package com.ssafy.woojuin.domain.item.processing;

import com.ssafy.woojuin.domain.item.entity.ItemType;
import java.util.Map;

/**
 * Redis Streams(woojuin:item-processing)에 실리는 메시지.
 * ItemQueueProducer가 넣는 필드 3개와 1:1로 대응한다.
 */
public record ItemProcessingMessage(Long itemId, Long workspaceId, ItemType type) {

    /**
     * 스트림 레코드의 raw map을 파싱한다. 필드가 깨져 있으면 재시도해도 영원히 실패하므로
     * (독약 메시지) 호출부가 즉시 ACK하고 버릴 수 있도록 IllegalArgumentException을 던진다.
     */
    public static ItemProcessingMessage from(Map<String, String> fields) {
        try {
            return new ItemProcessingMessage(
                    Long.valueOf(fields.get("itemId")),
                    Long.valueOf(fields.get("workspaceId")),
                    ItemType.valueOf(fields.get("type")));
        } catch (NullPointerException | IllegalArgumentException e) {
            throw new IllegalArgumentException("처리할 수 없는 큐 메시지: " + fields, e);
        }
    }
}
