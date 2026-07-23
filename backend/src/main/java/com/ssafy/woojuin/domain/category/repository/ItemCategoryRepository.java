package com.ssafy.woojuin.domain.category.repository;

import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ItemCategoryRepository extends JpaRepository<ItemCategory, Long> {

    List<ItemCategory> findByItemId(Long itemId);

    /** 목록 응답에서 여러 아이템의 카테고리를 한 번에 읽어 N+1을 피한다. */
    List<ItemCategory> findByItemIdIn(Collection<Long> itemIds);

    /**
     * (item_id, category_id)가 이미 있으면 무시하는 멱등 insert.
     *
     * <p>재전달 중복 처리나 다중 인스턴스로 같은 아이템이 동시에 가공될 때, "존재 확인 후
     * save"는 두 트랜잭션이 모두 "없음"을 읽고 각자 insert해 unique 제약을 위반한다. 그러면
     * 그 트랜잭션이 rollback-only로 마킹돼, AI 보강을 감싸던 catch가 예외를 삼켜도 커밋
     * 시점에 요약·본문까지 함께 롤백된다. ON CONFLICT DO NOTHING으로 예외 자체를 없앤다.
     */
    @Modifying
    @Query(value = "INSERT INTO item_categories (item_id, category_id) "
            + "VALUES (:itemId, :categoryId) ON CONFLICT (item_id, category_id) DO NOTHING",
            nativeQuery = true)
    void insertIgnoringDuplicate(@Param("itemId") Long itemId, @Param("categoryId") Long categoryId);

    /** 카테고리 삭제 시 연결 정리용. */
    void deleteByCategoryId(Long categoryId);

    void deleteByItemId(Long itemId);
}
