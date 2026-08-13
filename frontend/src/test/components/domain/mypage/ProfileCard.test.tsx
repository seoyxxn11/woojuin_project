import { describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-react';
import { userEvent } from 'vitest/browser';
import ProfileCard from '@/components/domain/mypage/ProfileCard';

const renderProfileCard = async () => {
  const onNicknameChange = vi.fn();
  const onAvatarColorChange = vi.fn();
  const onLogout = vi.fn();
  const result = await render(
    <ProfileCard
      nickname="우주인"
      email="astronaut@woojuin.com"
      avatarColor="WHITE"
      provider="LOCAL"
      saving={false}
      onNicknameChange={onNicknameChange}
      onAvatarColorChange={onAvatarColorChange}
      onLogout={onLogout}
    />,
  );

  return { ...result, onNicknameChange, onAvatarColorChange, onLogout };
};

describe('마이페이지 프로필 카드', () => {
  it('현재 사용자 정보를 표시한다', async () => {
    const { container } = await renderProfileCard();
    expect(container.textContent).toContain('우주인');
    expect(container.textContent).toContain('astronaut@woojuin.com');
    expect(container.textContent).toContain('이메일 계정 연결');
  });

  it('닉네임을 편집해 저장한다', async () => {
    const { container, onNicknameChange } = await renderProfileCard();
    const editButton = container.querySelector('button[aria-label="닉네임 수정"]') as HTMLElement;
    await userEvent.click(editButton);

    const input = container.querySelector('input[aria-label="닉네임"]') as HTMLInputElement;
    await userEvent.clear(input);
    await userEvent.type(input, '새우주인');
    await userEvent.keyboard('{Enter}');

    expect(onNicknameChange).toHaveBeenCalledWith('새우주인');
  });

  it('특수문자가 포함된 닉네임은 저장하지 않고 안내한다', async () => {
    const { container, onNicknameChange } = await renderProfileCard();
    const editButton = container.querySelector('button[aria-label="닉네임 수정"]') as HTMLElement;
    await userEvent.click(editButton);

    const input = container.querySelector('input[aria-label="닉네임"]') as HTMLInputElement;
    await userEvent.clear(input);
    await userEvent.type(input, '우주인!');
    await userEvent.keyboard('{Enter}');

    expect(onNicknameChange).not.toHaveBeenCalled();
    expect(container.textContent).toContain('닉네임은 한글, 영문, 숫자로 2~20자 입력해 주세요.');
  });

  it('색상과 로그아웃 동작을 부모에게 전달한다', async () => {
    const { container, onAvatarColorChange, onLogout } = await renderProfileCard();
    const purple = container.querySelector('button[aria-label="퍼플"]') as HTMLElement;
    const logout = [...container.querySelectorAll('button')].find(
      (button) => button.textContent === '로그아웃',
    ) as HTMLElement;

    await userEvent.click(purple);
    await userEvent.click(logout);

    expect(onAvatarColorChange).toHaveBeenCalledWith('PURPLE');
    expect(onLogout).toHaveBeenCalledOnce();
  });

  it('준비된 우주인 에셋 11종을 모두 색상 선택지로 표시한다', async () => {
    const { container } = await renderProfileCard();
    const colorOptions = container.querySelectorAll('[role="radio"]');

    expect(colorOptions).toHaveLength(11);
    for (const label of [
      '화이트',
      '블랙',
      '레드',
      '크림슨',
      '핑크',
      '오렌지',
      '라임',
      '그린',
      '블루',
      '네이비',
      '퍼플',
    ]) {
      expect(container.querySelector(`[role="radio"][aria-label="${label}"]`)).not.toBeNull();
    }
  });
});
