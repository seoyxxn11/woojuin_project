package com.ssafy.woojuin.domain.item.processing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.woojuin.domain.item.entity.ItemType;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ItemProcessingMessageTest {

    @Test
    void 정상_메시지를_파싱한다() {
        ItemProcessingMessage message = ItemProcessingMessage.from(
                Map.of("itemId", "42", "workspaceId", "7", "type", "URL"));

        assertThat(message.itemId()).isEqualTo(42L);
        assertThat(message.workspaceId()).isEqualTo(7L);
        assertThat(message.type()).isEqualTo(ItemType.URL);
    }

    @Test
    void 필드가_없으면_독약메시지로_간주해_예외를_던진다() {
        assertThatThrownBy(() -> ItemProcessingMessage.from(Map.of("itemId", "42")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void 알수없는_타입이면_예외를_던진다() {
        assertThatThrownBy(() -> ItemProcessingMessage.from(
                Map.of("itemId", "42", "workspaceId", "7", "type", "PODCAST")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void 숫자가_아닌_id면_예외를_던진다() {
        assertThatThrownBy(() -> ItemProcessingMessage.from(
                Map.of("itemId", "abc", "workspaceId", "7", "type", "URL")))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
