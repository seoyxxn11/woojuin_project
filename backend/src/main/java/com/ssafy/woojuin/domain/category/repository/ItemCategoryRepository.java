package com.ssafy.woojuin.domain.category.repository;

import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface ItemCategoryRepository extends JpaRepository<ItemCategory, Long> {

    List<ItemCategory> findByItemId(Long itemId);

    /** 목록 응답에서 여러 아이템의 카테고리를 한 번에 읽어 N+1을 피한다. */
    List<ItemCategory> findByItemIdIn(Collection<Long> itemIds);

    /**
     * 카테고리 필터용 — 그 카테고리들 중 하나라도 연결된 아이템 id들(OR). 한 아이템이
     * 여러 선택 카테고리에 걸쳐 있으면 중복 링크가 나올 수 있어 distinct로 뽑는다.
     */
    @Query("select distinct ic.itemId from ItemCategory ic where ic.categoryId in :categoryIds")
    List<Long> findItemIdsByCategoryIdIn(Collection<Long> categoryIds);

    /** 그 워크스페이스에서 '활성(휴지통 제외) 아이템이 하나라도 연결된' 카테고리 id들. */
    @Query("select distinct ic.categoryId from ItemCategory ic "
            + "where ic.itemId in (select i.id from Item i "
            + "where i.workspaceId = :workspaceId and i.deletedAt is null)")
    List<Long> findCategoryIdsWithActiveItems(Long workspaceId);

    boolean existsByItemIdAndCategoryId(Long itemId, Long categoryId);

    /** 카테고리 삭제 시 연결 정리용. */
    void deleteByCategoryId(Long categoryId);

    void deleteByItemId(Long itemId);
}
