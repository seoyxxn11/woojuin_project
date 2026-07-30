package com.ssafy.woojuin.domain.item.entity;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.woojuin.global.common.ItemStatus;
import org.junit.jupiter.api.Test;

/**
 * 트랙 A/B 결과를 반영하는 Item 도메인 메서드 단위 테스트.
 * 미리보기 반영 규칙(사용자 title 보존, null 무시)과 상태 전이만 검증한다.
 */
class ItemPreviewTest {

    private Item urlItem() {
        return Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").build();
    }

    @Test
    void applyPreview_비어있는_title을_채운다() {
        Item item = urlItem();

        item.applyPreview("스크래핑한 제목", "https://img", "설명");

        assertThat(item.getTitle()).isEqualTo("스크래핑한 제목");
        assertThat(item.getPreviewThumbnailUrl()).isEqualTo("https://img");
        assertThat(item.getPreviewDescription()).isEqualTo("설명");
    }

    @Test
    void applyPreview_사용자가_넣은_title은_덮어쓰지_않는다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").title("사용자 제목").build();

        item.applyPreview("스크래핑한 제목", null, null);

        assertThat(item.getTitle()).isEqualTo("사용자 제목");
    }

    /**
     * FR-013 공유 저장의 핵심 시나리오. 쿠팡은 봇을 막아 OG 스크래핑이 전부 실패하고
     * UrlItemProcessor가 host+path 폴백 제목을 넘기는데, 공유 시트에서 받은 상품명이
     * 그걸 밀어내지 않아야 한다 — 이 규칙이 깨지면 쿠팡 카드가 전부
     * "www.coupang.com/vp/products/..."로 보인다.
     */
    @Test
    void applyPreview_공유된_제목은_host_path_폴백보다_우선한다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://www.coupang.com/vp/products/123").title("무선 이어폰 블루투스 5.3").build();

        item.applyPreview("www.coupang.com/vp/products/123", null, null);

        assertThat(item.getTitle()).isEqualTo("무선 이어폰 블루투스 5.3");
    }

    /** 공유 제목이 없으면(직접 URL 입력) 폴백 제목이 그대로 쓰여야 한다. */
    @Test
    void applyPreview_공유된_제목이_없으면_폴백_제목을_쓴다() {
        Item item = urlItem();

        item.applyPreview("www.coupang.com/vp/products/123", null, null);

        assertThat(item.getTitle()).isEqualTo("www.coupang.com/vp/products/123");
    }

    @Test
    void applyPreview_null_필드는_기존값을_지우지_않는다() {
        Item item = urlItem();
        item.applyPreview(null, "https://img", "설명");

        item.applyPreview(null, null, null);

        assertThat(item.getPreviewThumbnailUrl()).isEqualTo("https://img");
        assertThat(item.getPreviewDescription()).isEqualTo("설명");
    }

    @Test
    void 상태_전이() {
        Item item = urlItem();
        assertThat(item.getStatus()).isEqualTo(ItemStatus.PROCESSING);

        item.markDone();
        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);

        item.markPartial();
        assertThat(item.getStatus()).isEqualTo(ItemStatus.PARTIAL);

        item.markFailed();
        assertThat(item.getStatus()).isEqualTo(ItemStatus.FAILED);
    }
}
