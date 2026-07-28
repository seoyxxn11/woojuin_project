package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * PERSONAL 워크스페이스가 없는 기존 가입자를 위한 1회성 백필.
 *
 * <p>ensurePersonalWorkspace가 멱등이라 매 기동마다 돌아도 안전하다 — Flyway를 쓰지 않아
 * 별도 마이그레이션 스크립트 대신 이 방식으로 처리한다.
 */
@Component
public class PersonalWorkspaceBackfillRunner implements ApplicationRunner {

    private final UserRepository userRepository;
    private final WorkspaceService workspaceService;

    public PersonalWorkspaceBackfillRunner(UserRepository userRepository, WorkspaceService workspaceService) {
        this.userRepository = userRepository;
        this.workspaceService = workspaceService;
    }

    @Override
    public void run(ApplicationArguments args) {
        userRepository.findAll().forEach(user -> workspaceService.ensurePersonalWorkspace(user.getId()));
    }
}
