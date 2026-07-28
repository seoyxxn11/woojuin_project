package com.ssafy.woojuin.domain.ai;

import java.util.List;

/**
 * AI 분석 결과.
 *
 * <p>categories는 카테고리 <b>이름</b> 목록이다. 한 아이템이 여러 카테고리에 중복으로 속할
 * 수 있어 리스트다(개수 제한은 분석기가 유사도 기준으로 정한다 — 묶음 F). 이름은 요청 시
 * 넘긴 candidateCategories 안의 값이어야 하며, 저장 측(묶음 D)이 그 워크스페이스의
 * category_id로 매핑한다. 매칭이 없으면 "기타"로 폴백한다.
 *
 * <p>summary는 본문이 있을 때만 채워진다 — title만으로 분류된 PARTIAL 아이템은 null.
 */
public record AiAnalysis(String summary, List<String> categories) {

    /** 분석에 실패했거나 아직 분석기가 없을 때. 호출부는 이 값을 받으면 요약·카테고리를 비워둔다. */
    public static AiAnalysis empty() {
        return new AiAnalysis(null, List.of());
    }

    public boolean isEmpty() {
        return summary == null && categories.isEmpty();
    }
}
