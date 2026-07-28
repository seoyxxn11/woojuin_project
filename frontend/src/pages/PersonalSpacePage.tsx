import { Navigate } from 'react-router-dom';
import { useUser } from '@/hooks/useUser';

/**
 * 로그인 직후 도착지 — 그림 없는 리다이렉트 전용 화면.
 *
 * 개인 워크스페이스 id 는 가입할 때 서버가 만들어주므로 URL 을 고정할 수 없다.
 * 프로필에 실려 오는 personalSpaceId 를 받아 그 우주로 넘긴다.
 *
 * replace 인 이유: push 면 성좌에서 뒤로가기 → /home → 다시 성좌로 튕겨서
 * 뒤로가기가 영영 안 먹는다.
 */
const PersonalSpacePage = () => {
  const { personalSpaceId } = useUser();

  return <Navigate to={`/workspace/${personalSpaceId}/universe`} replace />;
};

export default PersonalSpacePage;
