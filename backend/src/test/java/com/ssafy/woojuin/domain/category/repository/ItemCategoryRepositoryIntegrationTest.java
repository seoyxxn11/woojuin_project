package com.ssafy.woojuin.domain.category.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import java.sql.Connection;
import java.sql.DriverManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace;

/**
 * {@link ItemCategoryRepository#insertIgnoringDuplicate} 의 멱등 동작(PostgreSQL
 * {@code ON CONFLICT DO NOTHING})을 <b>실제 Postgres</b>에 붙여 검증하는 로컬 전용 통합 테스트.
 *
 * <p>단위 테스트는 레포지토리를 목킹하므로 네이티브 SQL·identity 컬럼 자동생성·unique 제약이
 * 실제로 맞물리는지는 확인되지 않는다. 여기서만 진짜 DB로 확인한다.
 *
 * <p><b>로컬 전용</b>: docker-compose의 Postgres(localhost:5432)가 떠 있을 때만 실행되고,
 * DB가 없으면(예: CI) {@link EnabledIf}로 조용히 skip한다 — CI에는 DB 사이드카가 없기 때문.
 * 실행 전 {@code docker compose up -d postgres} 필요.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)   // application.yml의 실제 Postgres 사용(H2로 대체 금지)
@EnabledIf("localPostgresAvailable")
class ItemCategoryRepositoryIntegrationTest {

    // 다른 데이터와 겹치지 않을 임의의 큰 값. 엔티티가 itemId/categoryId를 순수 Long 컬럼으로
    // 둬(FK 제약 없음) 실제 아이템/카테고리 행이 없어도 삽입할 수 있다.
    private static final long ITEM_ID = 999_000_001L;
    private static final long CATEGORY_ID = 888_000_001L;

    @Autowired
    private ItemCategoryRepository repository;

    @Test
    void 새_조합은_id가_자동생성되며_삽입된다() {
        repository.insertIgnoringDuplicate(ITEM_ID, CATEGORY_ID);

        var rows = repository.findByItemId(ITEM_ID);
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0).getId()).isNotNull();          // identity 컬럼 자동생성 확인
        assertThat(rows.get(0).getCategoryId()).isEqualTo(CATEGORY_ID);
    }

    @Test
    void 같은_조합을_두_번_넣어도_예외없이_한_줄만_남는다() {
        repository.insertIgnoringDuplicate(ITEM_ID, CATEGORY_ID);

        // 두 번째 호출 = 동시 처리로 이미 들어간 행을 다시 넣는 상황. unique 위반으로 예외가
        // 터지면 트랜잭션이 rollback-only가 돼 요약·본문까지 롤백된다 — ON CONFLICT로 막는다.
        assertThatCode(() -> repository.insertIgnoringDuplicate(ITEM_ID, CATEGORY_ID))
                .doesNotThrowAnyException();

        assertThat(repository.findByItemId(ITEM_ID)).hasSize(1);
    }

    @Test
    void 기존_행이_JPA_save로_들어가_있어도_중복_삽입은_무시된다() {
        // "먼저 save로 들어간 뒤, 동시에 도는 다른 트랜잭션이 같은 조합을 넣으려는" 실제 시나리오 재현
        repository.saveAndFlush(ItemCategory.builder().itemId(ITEM_ID).categoryId(CATEGORY_ID).build());

        assertThatCode(() -> repository.insertIgnoringDuplicate(ITEM_ID, CATEGORY_ID))
                .doesNotThrowAnyException();

        assertThat(repository.findByItemId(ITEM_ID)).hasSize(1);
    }

    /**
     * 로컬 Postgres 접속 가능 여부. 컨텍스트 로딩 전에 JUnit이 평가하므로, DB가 없으면
     * 컨텍스트 실패(ERROR) 대신 테스트 전체를 skip한다. login timeout을 짧게 줘 빨리 판단한다.
     */
    @SuppressWarnings("unused")
    static boolean localPostgresAvailable() {
        String url = envOr("DB_URL", "jdbc:postgresql://localhost:5432/woojuin");
        String user = envOr("DB_USERNAME", "woojuin");
        String password = envOr("DB_PASSWORD", "woojuin-local");
        DriverManager.setLoginTimeout(2);
        try (Connection ignored = DriverManager.getConnection(url, user, password)) {
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private static String envOr(String key, String fallback) {
        String v = System.getenv(key);
        return (v != null && !v.isBlank()) ? v : fallback;
    }
}
