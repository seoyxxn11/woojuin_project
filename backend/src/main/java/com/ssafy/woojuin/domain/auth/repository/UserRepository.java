package com.ssafy.woojuin.domain.auth.repository;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByProviderAndProviderId(AuthProvider provider, String providerId);

    Optional<User> findByEmailAndProvider(String email, AuthProvider provider);

    boolean existsByEmail(String email);
}
