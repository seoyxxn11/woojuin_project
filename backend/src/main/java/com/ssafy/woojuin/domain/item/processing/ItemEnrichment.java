package com.ssafy.woojuin.domain.item.processing;

import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import lombok.Builder;

/**
 * 프로세서의 네트워크 가공(추출·OCR·AI) 결과를 담아 트랜잭션 안 반영 단계
 * ({@link ItemEnrichmentWriter})로 넘기는 값 객체.
 *
 * <p>네트워크 I/O는 이 객체를 만드는 동안 <b>트랜잭션 밖</b>에서 끝나고, 여기 담긴 값만
 * 짧은 트랜잭션에서 아이템에 반영된다 — DB 커넥션을 수 초짜리 외부 호출 동안 붙잡지 않기 위함.
 *
 * <p>null 필드는 "확보 못 함"을 뜻하며 반영 시 기존 값을 지우지 않는다(Item.applyXxx 계약).
 * {@code categories}만 예외로, null이면 빈 목록으로 정규화한다(CategoryAssignmentService가
 * 빈 목록을 "기타" 폴백으로 처리하므로 null을 넘기면 안 된다).
 */
@Builder
public record ItemEnrichment(
        String previewTitle,
        String previewThumbnailUrl,
        String previewDescription,
        String content,
        String summary,
        List<String> categories,
        ItemStatus targetStatus) {

    public ItemEnrichment {
        categories = (categories == null) ? List.of() : List.copyOf(categories);
    }
}
