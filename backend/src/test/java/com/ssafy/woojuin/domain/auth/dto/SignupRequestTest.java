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

/** 컨트롤러 없이도 검증 애노테이션 자체를 확인할 수 있는 Jakarta Bean Validation 단위 테스트. */
class SignupRequestTest {

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
        SignupRequest request = new SignupRequest("", "password1234", "닉네임");

        Set<ConstraintViolation<SignupRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("이메일 형식이 아니면 검증에 실패한다")
    void invalidEmailFormat_failsValidation() {
        SignupRequest request = new SignupRequest("not-an-email", "password1234", "닉네임");

        Set<ConstraintViolation<SignupRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("비밀번호가 8자 미만이면 검증에 실패한다")
    void shortPassword_failsValidation() {
        SignupRequest request = new SignupRequest("test@woojuin.com", "short", "닉네임");

        Set<ConstraintViolation<SignupRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("닉네임이 비어있으면 검증에 실패한다")
    void blankNickname_failsValidation() {
        SignupRequest request = new SignupRequest("test@woojuin.com", "password1234", "");

        Set<ConstraintViolation<SignupRequest>> violations = validator.validate(request);

        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("모든 값이 유효하면 검증을 통과한다")
    void validRequest_passesValidation() {
        SignupRequest request = new SignupRequest("test@woojuin.com", "password1234", "닉네임");

        Set<ConstraintViolation<SignupRequest>> violations = validator.validate(request);

        assertThat(violations).isEmpty();
    }
}
