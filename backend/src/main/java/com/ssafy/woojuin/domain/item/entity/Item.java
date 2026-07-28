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
     * 트랙 A(미리보기) 결과 반영. title은 사용자가 이미 값을 넣었을 수 있어 덮어쓰지 않고
     * 비어 있을 때만 채운다 — 저장 시엔 URL 아이템 title이 비어 있는 게 일반적이다.
     * null 인자는 "확보 못 함"이므로 기존 값을 지우지 않는다.
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
