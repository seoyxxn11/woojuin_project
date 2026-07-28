package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.UpdateProfileRequest;
import com.ssafy.woojuin.domain.auth.dto.UserProfileResponse;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserProfileService {

    private final UserRepository userRepository;

    public UserProfileService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public UserProfileResponse getProfile(Long userId) {
        return UserProfileResponse.from(findUser(userId));
    }

    @Transactional
    public UserProfileResponse updateProfile(Long userId, UpdateProfileRequest request) {
        User user = findUser(userId);
        user.updateProfile(request.nickname(), request.profileImageUrl(), request.avatarColor());
        return UserProfileResponse.from(user);
    }

    private User findUser(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다"));
    }
}
