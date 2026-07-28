package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.event.UserSignedUpEvent;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 * provider+providerId로 기존 계정을 찾거나 없으면 새로 만든다.
 * 카카오/구글 각각의 OAuth2User 속성 파싱은 이 서비스 밖(SecurityConfig 연동 단계)에서 처리한다.
 */
@Service
public class OAuthAccountService {

    private final UserRepository userRepository;
    private final ApplicationEventPublisher eventPublisher;

    public OAuthAccountService(UserRepository userRepository, ApplicationEventPublisher eventPublisher) {
        this.userRepository = userRepository;
        this.eventPublisher = eventPublisher;
    }

    public User findOrCreateUser(AuthProvider provider, String providerId, String email, String nickname) {
        Optional<User> existing = userRepository.findByProviderAndProviderId(provider, providerId);
        if (existing.isPresent()) {
            return existing.get();
        }

        User saved = userRepository.save(User.builder()
                .email(email)
                .provider(provider)
                .providerId(providerId)
                .emailVerified(true)
                .nickname(nickname)
                .build());
        eventPublisher.publishEvent(new UserSignedUpEvent(saved.getId()));
        return saved;
    }
}
