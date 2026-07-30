package com.ssafy.woojuin.domain.item.entity;

import com.ssafy.woojuin.global.common.BaseTimeEntity;
import com.ssafy.woojuin.global.common.ItemStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * items 테이블 (ERD 기준). workspace_id/created_by는 워크스페이스/인증 도메인이
 * 아직 준비되지 않아 JPA 연관관계 없이 순수 FK 컬럼으로 둔다.
 */
@Getter
@Entity
@Table(name = "items")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Item extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long workspaceId;

    @Column(nullable = false)
    private Long createdBy;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private ItemType type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 15)
    private ItemStatus status;

    @Column(length = 500)
    private String title;

    @Column(columnDefinition = "text")
    private String url;

    @Column(columnDefinition = "text")
    private String content;

    @Column(columnDefinition = "text")
    private String summary;

    @Column(length = 500)
    private String s3Key;

    // IMAGE 썸네일(목록 카드용 저용량 webp)의 S3 키. 비동기 처리기가 생성하므로 생성 전/실패 시
    // null이고, 그때 목록은 원본(s3Key)으로 폴백한다. IMAGE가 아닌 타입은 항상 null.
    @Column(length = 500)
    private String thumbnailS3Key;

    @Column(columnDefinition = "text")
    private String previewDescription;

    @Column(columnDefinition = "text")
    private String previewThumbnailUrl;

    // 지도 뷰용 좌표 (FR-023 지도 자동 매핑). URL은 지도 공유 링크 파싱 또는 본문 주소
    // 지오코딩으로, IMAGE는 사진 EXIF GPS로 얻는다. 대부분의 아이템에는 위치가 없다
    // (코드 링크, 메모, 스크린샷 등) — null이 정상 상태다.
    //
    // 타입이 Double인 이유:
    //  - BigDecimal은 함정이다. Hibernate 6 + PostgreSQL 기본이 numeric(38,2)라서
    //    ddl-auto=update로 만들면 소수점 2자리(≈1km 오차)가 조용히 박힌다.
    //  - 원시 double은 "모름"을 표현할 수 없다. 0.0은 실제 좌표(기니만)이고,
    //    지도 조회가 IS NOT NULL 필터에 의존한다.
    //
    // AGENTS.md: 지도 SDK는 미정이므로 좌표는 특정 API 형식이 아닌 lat/lng 원시값으로 둔다.
    @Column
    private Double lat;

    @Column
    private Double lng;

    // 사람이 읽는 주소. 정방향 지오코딩은 좌표와 함께 받고, EXIF 경로는 역지오코딩으로
    // 따로 채운다. 확보 못 하면 좌표만 있고 null이다.
    @Column(length = 300)
    private String address;

    // 카테고리는 item_categories 조인 테이블로 다대다 관리한다(단일 category_id 폐기).
    // 기존 DB의 category_id 컬럼은 ddl-auto=update로는 드롭되지 않으니 마이그레이션 시 정리.

    @Column(nullable = false)
    private boolean favorite;

    private OffsetDateTime deletedAt;

    @Builder
    private Item(Long workspaceId, Long createdBy, ItemType type, String title, String url,
            String content, String s3Key) {
        this.workspaceId = workspaceId;
        this.createdBy = createdBy;
        this.type = type;
        this.status = ItemStatus.PROCESSING;
        this.title = title;
        this.url = url;
        this.content = content;
        this.s3Key = s3Key;
        this.favorite = false;
    }

    /**
     * null인 필드는 건드리지 않는다(부분 수정). content는 타입과 무관하게 수정 가능한데,
     * URL 아이템도 트랙 A/B가 모두 실패하면 사용자 메모로 폴백하기 때문이다(FR-020).
     */
    public void update(String title, String content) {
        if (title != null) {
            this.title = title;
        }
        if (content != null) {
            this.content = content;
        }
    }

    /**
     * 트랙 A(미리보기) 결과 반영. title은 이미 값이 있으면 덮어쓰지 않고 비어 있을 때만 채운다.
     * null 인자는 "확보 못 함"이므로 기존 값을 지우지 않는다.
     *
     * <p>이 "비어 있을 때만" 규칙이 <b>공유 시트가 준 제목을 지켜주는 장치</b>다(FR-013).
     * 쿠팡처럼 봇을 막는 쇼핑몰은 크롤링 제목이 host+path 폴백뿐인데, 저장 시점에 공유
     * 시트에서 받은 상품명이 들어와 있으면 그 폴백이 이걸 밀어내지 않는다. 따라서
     * <b>공유 제목이 OG 제목보다 우선한다</b> — 둘 다 있을 땐 OG를 버리는 셈이지만, 공유
     * 제목도 결국 그 페이지의 제목이라 손실이 거의 없고, 지저분한 공유 텍스트는 뒤이어
     * 실행되는 AI 보강이 다듬어 덮어쓴다({@link com.ssafy.woojuin.domain.ai.AiAnalysis}).
     *
     * <p>사용자가 직접 입력한 제목도 같은 규칙으로 보호된다.
     */
    public void applyPreview(String title, String thumbnailUrl, String description) {
        if ((this.title == null || this.title.isBlank()) && title != null && !title.isBlank()) {
            this.title = title;
        }
        if (thumbnailUrl != null) {
            this.previewThumbnailUrl = thumbnailUrl;
        }
        if (description != null) {
            this.previewDescription = description;
        }
    }

    /**
     * IMAGE 썸네일 생성(비동기) 결과 반영. 생성 실패 시엔 호출되지 않아 null로 남고,
     * 목록 응답은 원본 s3Key로 폴백한다. null 인자는 "생성 못 함"이라 무시한다.
     */
    public void applyThumbnail(String thumbnailS3Key) {
        if (thumbnailS3Key != null) {
            this.thumbnailS3Key = thumbnailS3Key;
        }
    }

    /** 트랙 B(본문 확보) 결과 반영. AI 분석 입력이 되는 원문 텍스트다. */
    public void applyContent(String content) {
        if (content != null) {
            this.content = content;
        }
    }

    /** AI 요약 반영. 본문이 없어 요약을 못 만든 경우(null)는 기존 값을 지우지 않는다. */
    public void applySummary(String summary) {
        if (summary != null) {
            this.summary = summary;
        }
    }

    /**
     * 지도 좌표·주소 반영 (FR-023). 다른 apply*와 같은 계약이다 — null 인자는
     * "확보 못 함"이므로 기존 값을 지우지 않는다.
     *
     * <p>lat/lng는 <b>쌍으로만</b> 반영한다. 한쪽만 채우면 지도 조회(둘 다 NOT NULL 조건)에서
     * 어차피 걸러지는 반쪽 상태만 남는다. address는 별개로 반영한다 — 역지오코딩이 실패해도
     * 좌표는 살려야 하기 때문이다(핀이 목적이고 주소는 장식이다).
     *
     * <p>범위를 벗어난 좌표는 무시한다. 지도 공유 링크에서 투영 좌표(카카오 WCONGNAMUL 등)를
     * 잘못 읽는 사고가 조용히 저장되는 걸 막는 마지막 방어선이다.
     */
    public void applyLocation(Double lat, Double lng, String address) {
        if (isValidCoordinate(lat, lng)) {
            this.lat = lat;
            this.lng = lng;
        }
        if (address != null && !address.isBlank()) {
            this.address = address;
        }
    }

    /** 0,0은 EXIF 누락·파싱 실패의 전형적 산출물이라 실제 좌표로 취급하지 않는다. */
    private static boolean isValidCoordinate(Double lat, Double lng) {
        return lat != null && lng != null
                && lat >= -90 && lat <= 90
                && lng >= -180 && lng <= 180
                && !(lat == 0 && lng == 0);
    }

    public boolean hasCoordinates() {
        return this.lat != null && this.lng != null;
    }

    /** 트랙 A/B 모두 성공. AI 분석까지 끝난 최종 상태. */
    public void markDone() {
        this.status = ItemStatus.DONE;
    }

    /** 트랙 A는 됐지만 트랙 B(또는 AI)가 실패. 미리보기만 있는 반쪽 상태. */
    public void markPartial() {
        this.status = ItemStatus.PARTIAL;
    }

    /** 트랙 A까지 실패해 사용자에게 보여줄 게 URL밖에 없는 상태. */
    public void markFailed() {
        this.status = ItemStatus.FAILED;
    }

    /**
     * 즐겨찾기 on/off. 토글이 아니라 원하는 상태를 그대로 반영한다 — POST/DELETE가 각각
     * true/false를 보내므로, 연타나 재시도로 같은 요청이 두 번 와도 상태가 뒤집히지 않는다.
     */
    public void changeFavorite(boolean favorite) {
        this.favorite = favorite;
    }

    public void moveToTrash() {
        this.deletedAt = OffsetDateTime.now();
    }

    public void restore() {
        this.deletedAt = null;
    }

    public boolean isTrashed() {
        return this.deletedAt != null;
    }
}
