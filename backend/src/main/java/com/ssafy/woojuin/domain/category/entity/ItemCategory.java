package com.ssafy.woojuin.domain.category.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 아이템 ↔ 카테고리 다대다 연결. 한 아이템이 여러 카테고리에 중복으로 속할 수 있다.
 * itemId/categoryId는 순수 FK 컬럼으로 둔다(Item·Category와 동일한 스타일).
 */
@Getter
@Entity
@Table(name = "item_categories",
        uniqueConstraints = @UniqueConstraint(columnNames = {"item_id", "category_id"}))
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ItemCategory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long itemId;

    @Column(nullable = false)
    private Long categoryId;

    @Builder
    private ItemCategory(Long itemId, Long categoryId) {
        this.itemId = itemId;
        this.categoryId = categoryId;
    }
}
