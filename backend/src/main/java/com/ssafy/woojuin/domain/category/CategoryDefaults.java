package com.ssafy.woojuin.domain.category;

import java.util.List;

/**
 * 워크스페이스 생성 시 시드되는 기본 카테고리. 사용자는 이후 추가/수정/삭제할 수 있고,
 * AI는 이 고정 목록이 아니라 <b>그 시점 워크스페이스에 존재하는</b> 카테고리 중에서만 분류한다.
 */
public final class CategoryDefaults {

    /** 분류 실패·미매칭 시 폴백 대상. 항상 존재해야 하므로 삭제를 막는다. */
    public static final String ETC = "기타";

    public static final List<String> NAMES = List.of(
            "생활·할 일",
            "학습·지식",
            "취업·커리어",
            "여행·장소",
            "음식·맛집",
            "쇼핑·제품",
            "건강·운동",
            "문화·콘텐츠",
            "돈·재테크",
            "아이디어·영감",
            ETC);

    private CategoryDefaults() {
    }
}
