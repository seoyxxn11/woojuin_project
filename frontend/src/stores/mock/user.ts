//유저==================================
//유저 정보
interface User {
  nickName: string;
  email: string;
  userId: number;
  avatarColor: string;
  remainMemories: number;
  fullMemories: number;
  /** 개인 워크스페이스 id — 로그인 후 이 우주로 들어간다 */
  personalSpaceId: number;
  workSpaces: WorkSpace[];
}

//유저 워크스페이스 수
interface WorkSpace {
  id: number;
  name: string;
}

export const USER_MOCK: User = {
  nickName: '홍길동',
  email: 'dngusdlqwkd@gmail.com',
  userId: 12,
  avatarColor: 'red',
  remainMemories: 12,
  fullMemories: 20,
  personalSpaceId: 1,
  workSpaces: [
    { id: 1, name: '몽골 여행' },
    { id: 2, name: '팀 프로젝트' },
    { id: 3, name: '스터디 그룹' },
  ],
};
