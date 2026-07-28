import { useQuery } from '@tanstack/react-query';
import { fetchMyProfile } from '@/services/auth';
import { USER_MOCK } from '@/stores/mock/user';
import { SPACEMAN_COLORS } from '@/utils/getSpacemanImage';

/**
 * 현재 로그인한 유저 정보 (닉네임·이메일·아바타색·저장공간).
 * 서버 상태 진입점 — 소비처는 이 훅만 쓴다. 워크스페이스 목록은 useWorkspaces 참고.
 *
 * avatarColor(아바타 색상 선택), remainMemories/fullMemories(저장 공간 quota),
 * personalSpaceId(개인 워크스페이스 id)는 백엔드에 아직 없는 값이라 임시로 채운다.
 * 프로필 로딩 전에는 화면이 비지 않도록 목업으로 대체한다.
 */
export function useUser() {
  const { data: profile } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: fetchMyProfile,
  });

  if (!profile) {
    return USER_MOCK;
  }

  return {
    nickName: profile.nickname,
    email: profile.email,
    userId: profile.id,
    avatarColor: SPACEMAN_COLORS[profile.id % SPACEMAN_COLORS.length],
    remainMemories: USER_MOCK.remainMemories,
    fullMemories: USER_MOCK.fullMemories,
    personalSpaceId: profile.personalSpaceId ?? USER_MOCK.personalSpaceId,
  };
}
