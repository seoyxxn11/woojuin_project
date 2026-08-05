package com.ssafy.woojuin.domain.ai.engine;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * 잠정 신호 Redis 저장소. 첫 번째 동일 대상 데이터를 후보로 만들지 않고 잠깐 보류하는
 * 상태다(생성 지연). 영구 상태(후보·연결)와 달리 짧은 수명을 가지므로 DB가 아니라 Redis에 둔다.
 *
 * <p>키 {@code cat-signal:{workspaceId}:{normalizedAnchorKey}} — 2번째 같은 대상 데이터가 오면
 * 이 키로 신호를 조회해 decide 요청에 실어 보내고, 후보로 전환되면 키를 삭제한다. TTL이 지나면
 * 자동 소멸한다(= EXPIRED).
 */
@Slf4j
@Component
public class CategoryEngineSignalStore {

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;
    private final Duration ttl;

    public CategoryEngineSignalStore(
            StringRedisTemplate redis,
            ObjectMapper objectMapper,
            @Value("${woojuin.category-engine.signal-ttl-hours:336}") long signalTtlHours) {
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.ttl = Duration.ofHours(signalTtlHours);
    }

    /** Redis에 보관하는 잠정 신호. AI decide의 provisionalSignal로 그대로 전달된다. */
    public record StoredSignal(
            Long signalId, Long firstItemId, String anchorType, String normalizedAnchorName,
            List<String> aliases, String firstTitle, String firstSummary) {
    }

    private String key(long workspaceId, String normalizedAnchorName) {
        return "cat-signal:" + workspaceId + ":" + AnchorKeys.normalize(normalizedAnchorName);
    }

    /** 첫 데이터의 신호를 저장(upsert)한다. signalId는 Redis 시퀀스로 채번한다. */
    public StoredSignal store(long workspaceId, StoredSignal signal) {
        Long signalId = signal.signalId() != null
                ? signal.signalId()
                : redis.opsForValue().increment("cat-signal-seq");
        StoredSignal stored = new StoredSignal(
                signalId, signal.firstItemId(), signal.anchorType(), signal.normalizedAnchorName(),
                signal.aliases(), signal.firstTitle(), signal.firstSummary());
        try {
            redis.opsForValue().set(
                    key(workspaceId, signal.normalizedAnchorName()),
                    objectMapper.writeValueAsString(stored), ttl);
        } catch (Exception e) {
            // Redis 일시 장애가 아이템 저장을 뒤집지 않게 한다 — 신호는 다음 기회에 다시 생긴다.
            log.warn("잠정 신호 저장 실패(무시): ws={} anchor={}", workspaceId, signal.normalizedAnchorName(), e);
        }
        return stored;
    }

    /** 2번째 데이터 처리 전, 같은 앵커의 대기 신호를 조회한다. 없으면 null. */
    public StoredSignal find(long workspaceId, String normalizedAnchorName) {
        try {
            String raw = redis.opsForValue().get(key(workspaceId, normalizedAnchorName));
            return raw == null ? null : objectMapper.readValue(raw, StoredSignal.class);
        } catch (Exception e) {
            log.warn("잠정 신호 조회 실패(무시): ws={} anchor={}", workspaceId, normalizedAnchorName, e);
            return null;
        }
    }

    /** 후보로 전환됐거나 만료 처리 시 신호를 삭제한다. */
    public void delete(long workspaceId, String normalizedAnchorName) {
        try {
            redis.delete(key(workspaceId, normalizedAnchorName));
        } catch (Exception e) {
            log.warn("잠정 신호 삭제 실패(무시): ws={} anchor={}", workspaceId, normalizedAnchorName, e);
        }
    }
}
