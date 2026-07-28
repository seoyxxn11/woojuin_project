package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.UpdateProfileRequest;
import com.ssafy.woojuin.domain.auth.dto.UserProfileResponse;
import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.AvatarColor;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserProfileServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserProfileService userProfileService;

    private User existingUser() {
        User user = User.builder()
                .email("test@woojuin.com")
                .provider(AuthProvider.LOCAL)
                .emailVerified(true)
                .nickname("우주인")
                .profileImageUrl("https://example.com/old.png")
                .build();
        ReflectionTestUtils.setField(user, "id", 1L);
        ReflectionTestUtils.setField(user, "personalWorkspaceId", 99L);
        return user;
    }

    @Test
    @DisplayName("존재하는 유저면 프로필을 반환한다")
    void getProfile_existingUser_returnsProfile() {
        when(userRepository.findById(1L)).thenReturn(Optional.of(existingUser()));

        UserProfileResponse response = userProfileService.getProfile(1L);

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.email()).isEqualTo("test@woojuin.com");
        assertThat(response.nickname()).isEqualTo("우주인");
        assertThat(response.personalSpaceId()).isEqualTo(99L);
        assertThat(response.avatarColor()).isEqualTo(AvatarColor.WHITE);
    }

    @Test
    @DisplayName("존재하지 않는 유저면 예외를 던진다")
    void getProfile_missingUser_throwsException() {
        when(userRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userProfileService.getProfile(1L))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("존재하는 유저면 닉네임/프로필 이미지/아바타 색상을 수정하고 반영된 값을 반환한다")
    void updateProfile_existingUser_updatesAndReturnsProfile() {
        User user = existingUser();
        when(userRepository.findById(1L)).thenReturn(Optional.of(user));

        UserProfileResponse response = userProfileService.updateProfile(1L,
                new UpdateProfileRequest("새닉네임", "https://example.com/new.png", AvatarColor.CRIMSON));

        assertThat(response.nickname()).isEqualTo("새닉네임");
        assertThat(response.profileImageUrl()).isEqualTo("https://example.com/new.png");
        assertThat(response.avatarColor()).isEqualTo(AvatarColor.CRIMSON);
        assertThat(user.getNickname()).isEqualTo("새닉네임");
        assertThat(user.getAvatarColor()).isEqualTo(AvatarColor.CRIMSON);
    }

    @Test
    @DisplayName("존재하지 않는 유저면 수정 시에도 예외를 던진다")
    void updateProfile_missingUser_throwsException() {
        when(userRepository.findById(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userProfileService.updateProfile(1L,
                new UpdateProfileRequest("새닉네임", null, AvatarColor.WHITE)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
