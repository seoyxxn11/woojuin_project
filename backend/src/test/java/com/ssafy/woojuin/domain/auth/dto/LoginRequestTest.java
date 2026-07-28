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

class LoginRequestTest {

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
    @DisplayName("이메일이 비어있으면 검증에 실패한다")
    void blankEmail_failsValidation() {
        LoginRequest request = new LoginRequest("", "password1234");

        Set<ConstraintViolation<LoginRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("이메일 형식이 아니면 검증에 실패한다")
    void invalidEmailFormat_failsValidation() {
        LoginRequest request = new LoginRequest("not-an-email", "password1234");

        Set<ConstraintViolation<LoginRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("비밀번호가 비어있으면 검증에 실패한다")
    void blankPassword_failsValidation() {
        LoginRequest request = new LoginRequest("test@woojuin.com", "");

        Set<ConstraintViolation<LoginRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("모든 값이 유효하면 검증을 통과한다")
    void validRequest_passesValidation() {
        LoginRequest request = new LoginRequest("test@woojuin.com", "password1234");

        Set<ConstraintViolation<LoginRequest>> violations = validator.validate(request);

        assertThat(violations).isEmpty();
    }
}
