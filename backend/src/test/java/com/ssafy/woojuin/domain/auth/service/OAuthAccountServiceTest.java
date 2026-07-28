package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.AvatarColor;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.event.UserSignedUpEvent;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OAuthAccountServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private ApplicationEventPublisher eventPublisher;

    @InjectMocks
    private OAuthAccountService oAuthAccountService;

    @Test
    @DisplayName("이미 같은 provider+providerId 계정이 있으면 그대로 반환하고 저장하지 않는다")
    void findOrCreateUser_existingAccount_returnsExistingUserWithoutSaving() {
        User existing = User.builder()
                .email("test@kakao.com")
                .provider(AuthProvider.KAKAO)
                .providerId("kakao-123")
                .emailVerified(true)
                .nickname("우주인")
                .build();
        when(userRepository.findByProviderAndProviderId(AuthProvider.KAKAO, "kakao-123"))
                .thenReturn(Optional.of(existing));

        User result = oAuthAccountService.findOrCreateUser(AuthProvider.KAKAO, "kakao-123", "test@kakao.com", "우주인");

        assertThat(result).isSameAs(existing);
        verify(userRepository, never()).save(any(User.class));
        verify(eventPublisher, never()).publishEvent(any());
    }

    @Test
    @DisplayName("계정이 없으면 emailVerified=true, passwordHash=null인 OAuth 유저를 생성해 저장한다")
    void findOrCreateUser_newAccount_createsAndSavesOAuthUser() {
        when(userRepository.findByProviderAndProviderId(AuthProvider.GOOGLE, "google-456"))
                .thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> invocation.getArgument(0));

        oAuthAccountService.findOrCreateUser(AuthProvider.GOOGLE, "google-456", "test@google.com", "우주인");

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        User saved = captor.getValue();
        assertThat(saved.getProvider()).isEqualTo(AuthProvider.GOOGLE);
        assertThat(saved.getProviderId()).isEqualTo("google-456");
        assertThat(saved.getEmail()).isEqualTo("test@google.com");
        assertThat(saved.getNickname()).isEqualTo("우주인");
        assertThat(saved.getPasswordHash()).isNull();
        assertThat(saved.isEmailVerified()).isTrue();
        assertThat(saved.getAvatarColor()).isEqualTo(AvatarColor.WHITE);
    }

    @Test
    @DisplayName("신규 계정을 생성하면 UserSignedUpEvent를 발행한다")
    void findOrCreateUser_newAccount_publishesUserSignedUpEvent() {
        when(userRepository.findByProviderAndProviderId(AuthProvider.GOOGLE, "google-456"))
                .thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> {
            User user = invocation.getArgument(0);
            ReflectionTestUtils.setField(user, "id", 5L);
            return user;
        });

        oAuthAccountService.findOrCreateUser(AuthProvider.GOOGLE, "google-456", "test@google.com", "우주인");

        ArgumentCaptor<UserSignedUpEvent> captor = ArgumentCaptor.forClass(UserSignedUpEvent.class);
        verify(eventPublisher).publishEvent(captor.capture());
        assertThat(captor.getValue().userId()).isEqualTo(5L);
    }
}
