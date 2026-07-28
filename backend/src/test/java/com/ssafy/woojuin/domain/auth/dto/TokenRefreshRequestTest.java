package com.ssafy.woojuin.domain.auth.dto;

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

class TokenRefreshRequestTest {

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
    @DisplayName("refreshToken이 비어있으면 검증에 실패한다")
    void blankRefreshToken_failsValidation() {
        TokenRefreshRequest request = new TokenRefreshRequest("");

        Set<ConstraintViolation<TokenRefreshRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("refreshToken이 있으면 검증을 통과한다")
    void validRequest_passesValidation() {
        TokenRefreshRequest request = new TokenRefreshRequest("some-refresh-token");

        Set<ConstraintViolation<TokenRefreshRequest>> violations = validator.validate(request);

        assertThat(violations).isEmpty();
    }
}
