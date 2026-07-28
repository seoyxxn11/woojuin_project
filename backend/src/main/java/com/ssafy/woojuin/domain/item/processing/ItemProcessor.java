package com.ssafy.woojuin.domain.item.processing;

import com.ssafy.woojuin.domain.item.entity.ItemType;

/**
 * 아이템 타입별 비동기 가공 담당. 큐 컨슈머(ItemQueueConsumer)가 메시지의 type을 보고
 * 맞는 구현체 하나에 위임한다.
 *
 * <p><b>왜 타입별 컨슈머가 아니라 타입별 프로세서인가</b><br>
 * Redis Streams의 consumer group은 그룹 안 컨슈머들에게 메시지를 임의 분배한다.
 * 묶음 D(URL)와 묶음 F(이미지/메모)가 같은 그룹에 각자 컨슈머로 붙으면 URL 메시지가
 * 이미지 워커에게 배달될 수 있다. 그래서 컨슈머는 하나로 두고 여기서 분기한다.
 *
 * <p><b>구현 규약</b>
 * <ul>
 *   <li>supports()는 서로 겹치지 않아야 한다. 한 타입에 구현체가 둘이면 기동 시 실패한다</li>
 *   <li>process()는 성공하면 아이템 상태를 DONE/PARTIAL 중 하나로 확정해야 한다.
 *       PROCESSING으로 남겨두면 사용자 화면에 영원히 스피너가 돈다</li>
 *   <li>재시도해도 소용없는 실패는 예외를 던지지 말고 내부에서 PARTIAL/FAILED로 확정할 것.
 *       예외를 던지면 컨슈머가 재시도 대상으로 간주한다</li>
 * </ul>
 */
public interface ItemProcessor {

    boolean supports(ItemType type);

    void process(ItemProcessingMessage message);
}
