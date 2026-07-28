package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.SignupRequest;
import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.event.UserSignedUpEvent;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class SignupService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final ApplicationEventPublisher eventPublisher;

    public SignupService(UserRepository userRepository, PasswordEncoder passwordEncoder,
                          ApplicationEventPublisher eventPublisher) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.eventPublisher = eventPublisher;
    }

    public User signup(SignupRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("이미 가입된 이메일입니다");
        }

        User user = User.builder()
                .email(request.email())
                .passwordHash(passwordEncoder.encode(request.password()))
                .provider(AuthProvider.LOCAL)
                .emailVerified(false)
                .nickname(request.nickname())
                .build();
        User saved = userRepository.save(user);
        eventPublisher.publishEvent(new UserSignedUpEvent(saved.getId()));
        return saved;
    }
}
