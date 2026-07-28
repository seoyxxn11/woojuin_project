package com.ssafy.woojuin.domain.auth.dto;

import com.ssafy.woojuin.domain.auth.entity.AvatarColor;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class UpdateProfileRequestTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        factory.close();
    }

    @Test
    @DisplayName("닉네임이 비어있으면 검증에 실패한다")
    void blankNickname_failsValidation() {
        UpdateProfileRequest request = new UpdateProfileRequest("", "https://example.com/a.png", AvatarColor.WHITE);

        Set<ConstraintViolation<UpdateProfileRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("닉네임이 50자를 넘으면 검증에 실패한다")
    void tooLongNickname_failsValidation() {
        UpdateProfileRequest request =
                new UpdateProfileRequest("가".repeat(51), "https://example.com/a.png", AvatarColor.WHITE);

        Set<ConstraintViolation<UpdateProfileRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("닉네임이 유효하면 검증을 통과한다 (profileImageUrl은 선택값)")
    void validRequest_passesValidation() {
        UpdateProfileRequest request = new UpdateProfileRequest("닉네임", null, AvatarColor.WHITE);

        Set<ConstraintViolation<UpdateProfileRequest>> violations = validator.validate(request);

        assertThat(violations).isEmpty();
    }
}
