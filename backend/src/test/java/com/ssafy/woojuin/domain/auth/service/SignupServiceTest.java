package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.SignupRequest;
import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.AvatarColor;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.event.UserSignedUpEvent;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SignupServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private ApplicationEventPublisher eventPublisher;

    private SignupService signupService;

    @Test
    @DisplayName("신규 이메일이면 비밀번호를 인코딩해 LOCAL 유저를 저장한다")
    void signup_newEmail_savesEncodedLocalUser() {
        signupService = new SignupService(userRepository, passwordEncoder, eventPublisher);
        SignupRequest request = new SignupRequest("test@woojuin.com", "raw-password", "우주인");

        when(passwordEncoder.encode("raw-password")).thenReturn("encoded-password");
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> invocation.getArgument(0));

        signupService.signup(request);

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        User saved = captor.getValue();
        assertThat(saved.getEmail()).isEqualTo("test@woojuin.com");
        assertThat(saved.getNickname()).isEqualTo("우주인");
        assertThat(saved.getPasswordHash()).isEqualTo("encoded-password");
        assertThat(saved.getProvider()).isEqualTo(AuthProvider.LOCAL);
        assertThat(saved.isEmailVerified()).isFalse();
        assertThat(saved.getAvatarColor()).isEqualTo(AvatarColor.WHITE);
    }

    @Test
    @DisplayName("다른 provider로라도 이미 가입된 이메일이면 예외를 던지고 저장하지 않는다")
    void signup_emailAlreadyUsedByAnyProvider_throwsAndDoesNotSave() {
        signupService = new SignupService(userRepository, passwordEncoder, eventPublisher);
        SignupRequest request = new SignupRequest("test@woojuin.com", "raw-password", "우주인");

        // 구글로 이미 가입된 이메일로 로컬 회원가입을 시도하는 시나리오
        when(userRepository.existsByEmail("test@woojuin.com")).thenReturn(true);

        assertThatThrownBy(() -> signupService.signup(request))
                .isInstanceOf(IllegalArgumentException.class);

        verify(userRepository, never()).save(any(User.class));
        verify(eventPublisher, never()).publishEvent(any());
    }

    @Test
    @DisplayName("가입에 성공하면 UserSignedUpEvent를 발행한다")
    void signup_success_publishesUserSignedUpEvent() {
        signupService = new SignupService(userRepository, passwordEncoder, eventPublisher);
        SignupRequest request = new SignupRequest("test@woojuin.com", "raw-password", "우주인");

        when(passwordEncoder.encode("raw-password")).thenReturn("encoded-password");
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> {
            User user = invocation.getArgument(0);
            ReflectionTestUtils.setField(user, "id", 1L);
            return user;
        });

        signupService.signup(request);

        ArgumentCaptor<UserSignedUpEvent> captor = ArgumentCaptor.forClass(UserSignedUpEvent.class);
        verify(eventPublisher).publishEvent(captor.capture());
        assertThat(captor.getValue().userId()).isEqualTo(1L);
    }
}
