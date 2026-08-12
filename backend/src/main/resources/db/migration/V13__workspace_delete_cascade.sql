-- ===========================================================================
-- 워크스페이스 삭제를 막던 부속 테이블 FK 에 삭제 규칙을 붙인다
-- ===========================================================================
-- (배경) WorkspaceService.delete() 는 workspace_members / workspace_invitations 만
-- 직접 정리하는데, 아래 부속 테이블들은 FK 에 삭제 규칙이 없어 행이 하나라도 있으면
-- workspaces DELETE 가 FK 위반으로 실패했다. 멤버 합류 시 JOINED 활동이 반드시
-- 기록되므로(WorkspaceInvitationService), "다른 사용자가 초대된 워크스페이스는
-- 삭제가 안 되는" 버그로 드러났다.
--
-- 로그·부속 데이터(활동 이력, 피드 확인 시각, 추방 기록)는 워크스페이스와 운명을
-- 같이하면 되므로 CASCADE 로 지운다. 서비스 코드에서 deleteAll 을 늘리는 방식은
-- 부속 테이블이 새로 생길 때마다 누락되기 쉬워(이번 사례) DB 규칙으로 내린다.

ALTER TABLE workspace_member_activities
    DROP CONSTRAINT fk_workspace_member_activities_workspace,
    ADD CONSTRAINT fk_workspace_member_activities_workspace
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE;

ALTER TABLE workspace_member_last_seens
    DROP CONSTRAINT fk_workspace_member_last_seens_workspace,
    ADD CONSTRAINT fk_workspace_member_last_seens_workspace
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE;

ALTER TABLE workspace_bans
    DROP CONSTRAINT fk_workspace_bans_workspace,
    ADD CONSTRAINT fk_workspace_bans_workspace
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE;

-- 봇 연동의 기본 저장 공간은 연동 자체를 지우면 안 되고 지정만 풀리면 된다.
-- 봇 쪽은 default_workspace 가 NULL 이면 "미지정" 안내로 이미 대응한다
-- (ChatCommandService.defaultWorkspaceId → DefaultWorkspaceNotSetException).
ALTER TABLE chat_account_connections
    DROP CONSTRAINT fk_chat_account_connections_workspace,
    ADD CONSTRAINT fk_chat_account_connections_workspace
        FOREIGN KEY (default_workspace_id) REFERENCES workspaces (id) ON DELETE SET NULL;
