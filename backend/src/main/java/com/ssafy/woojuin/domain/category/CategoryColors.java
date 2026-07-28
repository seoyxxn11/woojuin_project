package com.ssafy.woojuin.domain.category;

import java.util.List;

/**
 * 카테고리(별자리) 색상 팔레트. 프론트 design-system의 "별자리 파스텔" 팔레트와 일치시킨다.
 *
 * <p>규칙: 별자리(=카테고리)에는 {@link #PALETTE} 5색을 순환 배정하고, 어떤 별자리에도
 * 속하지 않는 미분류("기타", {@link CategoryDefaults#ETC})는 {@link #UNCATEGORIZED}(white)를 쓴다.
 * hex 문자열로 저장해 프론트가 그대로 렌더한다.
 */
public final class CategoryColors {

    /** 미분류(기타) 전용 색. 순환 팔레트에 포함되지 않는다. */
    public static final String UNCATEGORIZED = "#F5F1E8"; // white

    /**
     * 별자리에 순환 배정하는 팔레트. 기본 파스텔 5색(vivid)과, 색상·명도는 그대로 두고 채도만
     * 낮춘 변형 5색(muted, HSL 기준 S×0.5)을 이어붙여 10색으로 구성한다 — 기본 카테고리
     * 10개(기타 제외)가 모두 다른 색을 갖고, 커스텀 카테고리는 이 10색을 이어서 순환한다.
     */
    public static final List<String> PALETTE = List.of(
            // ring0 — vivid (프론트 별자리 파스텔 원본)
            "#C9B8FF",  // lavender
            "#8FB4FF",  // blue
            "#B8E6A3",  // green
            "#F5B08A",  // orange
            "#F2D96B",  // yellow
            // ring1 — muted (같은 hue/명도, 채도만 절반)
            "#D2CAED",  // lavender (muted)
            "#ABBEE3",  // blue (muted)
            "#BED5B4",  // green (muted)
            "#DAB8A5",  // orange (muted)
            "#D0C48D"); // yellow (muted)

    private CategoryColors() {
    }

    /** ordinal번째 별자리에 배정할 색(순환). 기타에는 쓰지 말고 {@link #UNCATEGORIZED}를 쓸 것. */
    public static String forOrdinal(int ordinal) {
        return PALETTE.get(Math.floorMod(ordinal, PALETTE.size()));
    }
}
