package com.ssafy.woojuin.domain.auth.security;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

/**
 * DaoAuthenticationProvider가 이메일/비밀번호 로그인 검증에 사용.
 * OAuth 유저는 이 경로를 타지 않으므로 provider=LOCAL 계정만 조회한다.
 */
@Service
public class CustomUserDetailsService implements UserDetailsService {

    private final UserRepository userRepository;

    public CustomUserDetailsService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        User user = userRepository.findByEmailAndProvider(email, AuthProvider.LOCAL)
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + email));
        return new CustomUserPrincipal(user);
    }
}
