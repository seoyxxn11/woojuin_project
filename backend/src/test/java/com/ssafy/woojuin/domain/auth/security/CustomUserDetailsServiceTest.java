package com.ssafy.woojuin.domain.auth.security;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class CustomUserDetailsServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private CustomUserDetailsService userDetailsService;

    @Test
    @DisplayName("LOCAL 계정 이메일로 조회하면 userId를 포함한 UserDetails를 반환한다")
    void loadUserByUsername_existingLocalUser_returnsPrincipalWithUserId() {
        User user = User.builder()
                .email("test@woojuin.com")
                .passwordHash("encoded-password")
                .provider(AuthProvider.LOCAL)
                .emailVerified(true)
                .nickname("우주인")
                .build();
        ReflectionTestUtils.setField(user, "id", 1L);
        when(userRepository.findByEmailAndProvider("test@woojuin.com", AuthProvider.LOCAL))
                .thenReturn(Optional.of(user));

        CustomUserPrincipal principal =
                (CustomUserPrincipal) userDetailsService.loadUserByUsername("test@woojuin.com");

        assertThat(principal.getUserId()).isEqualTo(1L);
        assertThat(principal.getUsername()).isEqualTo("test@woojuin.com");
        assertThat(principal.getPassword()).isEqualTo("encoded-password");
    }

    @Test
    @DisplayName("존재하지 않는 이메일이면 UsernameNotFoundException을 던진다")
    void loadUserByUsername_unknownEmail_throwsUsernameNotFoundException() {
        when(userRepository.findByEmailAndProvider("unknown@woojuin.com", AuthProvider.LOCAL))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> userDetailsService.loadUserByUsername("unknown@woojuin.com"))
                .isInstanceOf(UsernameNotFoundException.class);
    }
}
