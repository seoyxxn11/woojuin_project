import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from 'vitest-browser-react';
import { userEvent } from 'vitest/browser';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider as JotaiProvider, createStore } from 'jotai';
import OAuthOnboardingPage from '@/pages/OAuthOnboardingPage';
import { fetchMyProfile, updateMyProfile } from '@/services/auth';
import { postLoginRedirectAtom } from '@/stores/authAtoms';
import type { UserProfile } from '@/services/auth';

vi.mock('@/services/auth', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/auth')>()),
  fetchMyProfile: vi.fn(),
  updateMyProfile: vi.fn(),
}));

const profile: UserProfile = {
  id: 1,
  email: 'astronaut@gmail.com',
  nickname: '구글유저',
  profileImageUrl: null,
  provider: 'GOOGLE',
  emailVerified: true,
  avatarColor: 'WHITE',
  personalSpaceId: 1,
  personalTutorialCompleted: false,
  sharedWorkspaceTutorialCompleted: false,
};

const renderOnboarding = (postLoginRedirect: string | null = null) => {
  const store = createStore();
  store.set(postLoginRedirectAtom, postLoginRedirect);
  return render(
    <JotaiProvider store={store}>
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <MemoryRouter initialEntries={['/oauth/onboarding']}>
          <Routes>
            <Route path="/oauth/onboarding" element={<OAuthOnboardingPage />} />
            <Route path="/home" element={<p>개인 워크스페이스</p>} />
            <Route path="/workspace/9/library" element={<p>서재 화면</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </JotaiProvider>,
  );
};

const submitButton = (c: HTMLElement) => c.querySelector('button[type="submit"]') as HTMLElement;
const nicknameInput = (c: HTMLElement) => c.querySelector('input[type="text"]') as HTMLInputElement;
const privacyCheckbox = (c: HTMLElement) =>
  c.querySelector('input[type="checkbox"]') as HTMLInputElement;
const scrollBody = (c: HTMLElement) =>
  c.querySelector('[data-testid="privacy-policy-scroll-body"]') as HTMLElement;

beforeEach(() => {
  vi.mocked(fetchMyProfile).mockReset();
  vi.mocked(updateMyProfile).mockReset();
  vi.mocked(fetchMyProfile).mockResolvedValue(profile);
});

describe('OAuthOnboardingPage', () => {
  it('구글이 준 기본 닉네임으로 미리 채워진다', async () => {
    const { container } = await renderOnboarding();

    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');
  });

  it('닉네임이 비어 있거나 방침에 동의하지 않으면 시작하기 버튼이 비활성이다', async () => {
    const { container } = await renderOnboarding();

    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');
    expect(submitButton(container).hasAttribute('disabled')).toBe(true);
  });

  it('닉네임을 지우면 버튼이 다시 비활성화된다(닉네임 필수)', async () => {
    const { container } = await renderOnboarding();
    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');

    await userEvent.clear(nicknameInput(container));

    expect(submitButton(container).hasAttribute('disabled')).toBe(true);
  });

  it('특수문자가 포함된 닉네임은 안내하고 제출할 수 없다', async () => {
    const { container } = await renderOnboarding();
    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');

    await userEvent.clear(nicknameInput(container));
    await userEvent.type(nicknameInput(container), '구글유저!');

    expect(submitButton(container).hasAttribute('disabled')).toBe(true);
    expect(container.textContent).toContain('닉네임은 한글, 영문, 숫자로 2~20자 입력해 주세요.');
  });

  it('닉네임을 채우고 방침에 끝까지 동의하면 시작하기 버튼이 활성화된다', async () => {
    const { container, getByRole } = await renderOnboarding();
    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');

    await userEvent.click(privacyCheckbox(container));
    scrollBody(container).scrollTop = scrollBody(container).scrollHeight;
    await userEvent.click(getByRole('button', { name: '확인' }));

    expect(submitButton(container).hasAttribute('disabled')).toBe(false);
  });

  it('제출하면 닉네임을 저장하고 기본 도착지(/home)로 이동한다', async () => {
    vi.mocked(updateMyProfile).mockResolvedValue({ ...profile, nickname: '새닉네임' });
    const { container, getByRole } = await renderOnboarding();
    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');

    await userEvent.clear(nicknameInput(container));
    await userEvent.type(nicknameInput(container), '새닉네임');
    await userEvent.click(privacyCheckbox(container));
    scrollBody(container).scrollTop = scrollBody(container).scrollHeight;
    await userEvent.click(getByRole('button', { name: '확인' }));
    await userEvent.click(submitButton(container));

    await expect.poll(() => container.textContent).toContain('개인 워크스페이스');
    expect(vi.mocked(updateMyProfile).mock.calls[0][0]).toEqual({
      nickname: '새닉네임',
      profileImageUrl: null,
      avatarColor: 'WHITE',
    });
  });

  it('가려던 목적지가 있으면 온보딩을 마친 뒤 그리로 보낸다', async () => {
    vi.mocked(updateMyProfile).mockResolvedValue(profile);
    const { container, getByRole } = await renderOnboarding('/workspace/9/library');
    await expect.poll(() => nicknameInput(container).value).toBe('구글유저');

    await userEvent.click(privacyCheckbox(container));
    scrollBody(container).scrollTop = scrollBody(container).scrollHeight;
    await userEvent.click(getByRole('button', { name: '확인' }));
    await userEvent.click(submitButton(container));

    await expect.poll(() => container.textContent).toContain('서재 화면');
  });
});
