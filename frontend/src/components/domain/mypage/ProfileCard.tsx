import { useEffect, useState } from 'react';
import AvatarColorPicker from './AvatarColorPicker';
import { getSpacemanImage } from '@/utils/getSpacemanImage';
import { nicknameSchema } from '@/schemas/authSchemas';

interface ProfileCardProps {
  nickname: string;
  email: string;
  avatarColor: string;
  provider?: 'LOCAL' | 'KAKAO' | 'GOOGLE';
  saving: boolean;
  onNicknameChange: (nickname: string) => void;
  onAvatarColorChange: (color: string) => void;
  onLogout: () => void;
}

const PROVIDER_LABEL = {
  LOCAL: '이메일',
  KAKAO: '카카오',
  GOOGLE: '구글',
} as const;

const ProfileCard = ({
  nickname,
  email,
  avatarColor,
  provider,
  saving,
  onNicknameChange,
  onAvatarColorChange,
  onLogout,
}: ProfileCardProps) => {
  const [editing, setEditing] = useState(false);
  const [draftNickname, setDraftNickname] = useState(nickname);
  const [nicknameError, setNicknameError] = useState<string | null>(null);

  useEffect(() => setDraftNickname(nickname), [nickname]);

  const cancelEditing = () => {
    setDraftNickname(nickname);
    setNicknameError(null);
    setEditing(false);
  };

  const saveNickname = () => {
    const result = nicknameSchema.safeParse(draftNickname);
    if (!result.success) {
      setNicknameError(result.error.issues[0]?.message ?? null);
      return;
    }
    const nextNickname = result.data;
    if (nextNickname === nickname) {
      cancelEditing();
      return;
    }
    onNicknameChange(nextNickname);
    setEditing(false);
  };

  return (
    // 카드가 아니라 페이지의 머리(히어로)다 — 구획은 상자가 아니라 여백이 만든다
    <div className="mb-10">
      <section className="flex items-center gap-4 px-2 desktop:gap-[18px]">
        <div className="h-20 w-20 shrink-0 overflow-hidden rounded-full bg-surface-3">
          <img
            src={getSpacemanImage(avatarColor)}
            alt={`${nickname} 프로필`}
            className="block h-full w-full object-cover"
          />
        </div>

        <div className="min-w-0 flex-1">
          {editing ? (
            <input
              autoFocus
              aria-label="닉네임"
              value={draftNickname}
              maxLength={20}
              disabled={saving}
              aria-invalid={Boolean(nicknameError)}
              aria-describedby={nicknameError ? 'profile-nickname-error' : undefined}
              onChange={(event) => {
                setDraftNickname(event.target.value);
                setNicknameError(null);
              }}
              onBlur={saveNickname}
              onKeyDown={(event) => {
                if (event.key === 'Enter') saveNickname();
                if (event.key === 'Escape') cancelEditing();
              }}
              className="w-full max-w-[180px] rounded-sm border border-accent bg-surface-2 px-2.5 py-1 text-lg font-extrabold text-text-1 outline-none"
            />
          ) : (
            <div className="flex items-center gap-2">
              <h2 className="truncate text-xl font-extrabold text-text-1">{nickname}</h2>
              <button
                type="button"
                aria-label="닉네임 수정"
                onClick={() => setEditing(true)}
                disabled={saving}
                className="rounded px-1.5 py-0.5 text-xs font-bold text-text-3 hover:bg-surface-2 hover:text-text-1 disabled:cursor-wait"
              >
                수정
              </button>
            </div>
          )}
          {editing && nicknameError && (
            <p id="profile-nickname-error" className="mt-1 text-xs text-red-400">
              {nicknameError}
            </p>
          )}
          <p className="mt-0.5 truncate text-[13.5px] text-text-2">{email}</p>
          <p className="mt-1.5 text-xs text-text-3">
            {provider ? `${PROVIDER_LABEL[provider]} 계정 연결` : '계정 정보를 불러오는 중'}
          </p>
        </div>

        <button
          type="button"
          onClick={onLogout}
          className="shrink-0 rounded-[10px] border border-border bg-surface-2 px-3.5 py-[7px] text-[12.5px] font-bold text-text-1 hover:bg-surface-3"
        >
          로그아웃
        </button>
      </section>

      <AvatarColorPicker value={avatarColor} disabled={saving} onChange={onAvatarColorChange} />
    </div>
  );
};

export default ProfileCard;
