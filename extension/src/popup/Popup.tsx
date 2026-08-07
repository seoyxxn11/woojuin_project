import { useCallback, useEffect, useRef, useState } from 'react';
import { logout } from '@/api/auth';
import { ApiError, WEB_ORIGIN } from '@/api/client';
import { ItemStatus } from '@/api/items';
import { LAST_RESULT_KEY } from '@/background/watchItem';
import { saveUrl } from '@/api/items';
import { getWorkspaces, Workspace } from '@/api/workspaces';
import SpacePicker from '@/popup/SpacePicker';
import { isNotifyOnSaveEnabled, setNotifyOnSaveEnabled } from '@/storage/settingsStorage';
import InteractiveLogo from '@/ui/InteractiveLogo';
import { AUTH_STORAGE, getAccessToken, getRefreshToken } from '@/storage/authStorage';
import {
  clearCachedWorkspaces,
  clearSelectedWorkspaceId,
  getSelectedWorkspaceId,
  setCachedWorkspaces,
  setSelectedWorkspaceId,
} from '@/storage/workspaceStorage';

type Status = 'idle' | 'loading' | 'saving' | 'analyzing' | 'done' | 'error';
interface ContextSaveFeedback {
  success: boolean;
  message: string;
  createdAt: number;
}

const CONTEXT_FEEDBACK_KEY = 'contextSaveFeedback';
const messageFrom = (error: unknown) =>
  error instanceof ApiError && error.status === 401
    ? '로그인이 만료되었습니다. 우주인에서 다시 로그인해 주세요.'
    : error instanceof Error ? error.message : '요청을 처리하지 못했습니다.';

function isSavableUrl(value: string): boolean {
  try { return ['http:', 'https:'].includes(new URL(value).protocol); } catch { return false; }
}


/**
 * 저장 완료 표시 — 로고가 페이드아웃하는 자리에 원과 체크가 그려진다.
 * stroke-dashoffset 을 애니메이션해 "그려지는" 느낌을 낸다(키프레임은 popup.html).
 */
const SaveDoneMark = ({ size = 64, failed = false }: { size?: number; failed?: boolean }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 64 64"
    fill="none"
    aria-hidden="true"
    style={{ display: 'block', animation: 'wj-mark-in 0.28s cubic-bezier(0.22, 1, 0.36, 1) both' }}
  >
    <circle
      cx="32" cy="32" r="27"
      stroke={failed ? DANGER : ACCENT} strokeWidth="3" strokeLinecap="round"
      strokeDasharray="170"
      style={{ animation: 'wj-ring-draw 0.5s ease-out both', transform: 'rotate(-90deg)', transformOrigin: '32px 32px' }}
    />
    <path
      d={failed ? 'M23 23 L41 41 M41 23 L23 41' : 'M20 33.5 L28.5 42 L44 25'}
      stroke={failed ? DANGER : ACCENT} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"
      strokeDasharray="30"
      style={{ animation: 'wj-check-draw 0.32s 0.22s ease-out both' }}
    />
  </svg>
);

export default function Popup() {
  const [url, setUrl] = useState('');
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState('');
  const [notifyOnSave, setNotifyOnSave] = useState(true);
  const [watchedItemId, setWatchedItemId] = useState<number | null>(null);
  const [doneStatus, setDoneStatus] = useState<ItemStatus | null>(null);
  const [urlExpanded, setUrlExpanded] = useState(false);
  const [urlOverflowing, setUrlOverflowing] = useState(false);
  const [contextFeedback, setContextFeedback] = useState<ContextSaveFeedback | null>(null);
  const urlRef = useRef<HTMLParagraphElement>(null);

  /** @returns 목록을 실제로 받았는지 — 물려받은 토큰이 살아 있는지의 판정으로도 쓴다. */
  const loadWorkspaces = useCallback(async (): Promise<boolean> => {
    setStatus('loading');
    try {
      const [items, previousId] = await Promise.all([getWorkspaces(), getSelectedWorkspaceId()]);
      const selected = items.find((item) => item.id === previousId)
        ?? items.find((item) => item.type === 'PERSONAL') ?? items[0] ?? null;
      setWorkspaces(items);
      setWorkspaceId(selected?.id ?? null);
      // 우클릭 메뉴가 이 목록으로 저장할 곳 하위 메뉴를 짠다(background/contextMenus.ts).
      await setCachedWorkspaces(items);
      if (selected) await setSelectedWorkspaceId(selected.id);
      setStatus('idle');
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setAuthenticated(false);
      setStatus('error');
      setMessage(messageFrom(error));
      return false;
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const [[tab], accessToken, refreshToken] = await Promise.all([
        chrome.tabs.query({ active: true, currentWindow: true }),
        getAccessToken(),
        getRefreshToken(),
      ]);
      setUrl(tab?.url ?? '');
      // 확장은 자기 세션만 본다 — 웹 세션 물려받기는 링크 코드 로그인으로 대체됐다(-498).
      const hasSession = Boolean(accessToken || refreshToken);
      setAuthenticated(hasSession);
      if (hasSession) await loadWorkspaces();
    })();
  }, [loadWorkspaces]);

  /**
   * 우클릭 저장의 **실패**만 받아 온다. 성공은 배지·툴팁과 완료 알림으로 이미 알리므로
   * 여기까지 띄우면 같은 말을 네 번 하게 되고, 팝업을 안 여는 게 요점인 기능의 결과를
   * 팝업에서 확인시키는 꼴이 된다(background 의 showFeedback 주석 참고).
   *
   * 받은 뒤에는 **지운다.** 안 지우면 팝업을 열 때마다 지나간 실패가 다시 뜬다 —
   * 배지는 8초, 저장 완료 표시는 1.4초 만에 사라지는데 이 줄만 남는 게 지금 문제였다.
   */
  useEffect(() => {
    const consume = (feedback: ContextSaveFeedback | undefined) => {
      // success 검사는 예전 버전이 남긴 성공 기록을 걸러 낸다(그때는 성공도 저장했다).
      if (!feedback || feedback.success) return false;
      setContextFeedback(feedback);
      return true;
    };
    void chrome.storage.local.get(CONTEXT_FEEDBACK_KEY).then((result) => {
      const feedback = result[CONTEXT_FEEDBACK_KEY] as ContextSaveFeedback | undefined;
      if (!feedback) return;
      // 오래된 실패는 되살리지 않는다 — 지금 하려는 일과 무관한 이야기가 된다.
      if (Date.now() - feedback.createdAt < 60_000) consume(feedback);
      void chrome.storage.local.remove(CONTEXT_FEEDBACK_KEY);
    });
    const handleStorageChange = (changes: Record<string, chrome.storage.StorageChange>) => {
      const feedback = changes[CONTEXT_FEEDBACK_KEY]?.newValue as ContextSaveFeedback | undefined;
      // 아래 remove 가 부르는 변경은 newValue 가 없어 여기서 걸러진다(되돌이 없음).
      if (consume(feedback)) void chrome.storage.local.remove(CONTEXT_FEEDBACK_KEY);
    };
    chrome.storage.onChanged.addListener(handleStorageChange);
    return () => chrome.storage.onChanged.removeListener(handleStorageChange);
  }, []);

  // 백그라운드가 로그인 토큰을 저장하는 순간 화면을 바꾼다 — 팝업을 열어 둔 채로 로그인하면
  // 창이 닫히면서 그대로 로그인 상태가 된다(닫았다 다시 열 필요가 없다).
  useEffect(() => {
    const handleTokenArrival = (
      changes: Record<string, chrome.storage.StorageChange>,
      areaName: string,
    ) => {
      const arrived = (Object.values(AUTH_STORAGE) as { area: string; key: string }[])
        .some(({ area, key }) => areaName === area && changes[key]?.newValue);
      if (!arrived) return;
      setAuthenticated(true);
      setStatus('idle');
      setMessage('');
      void loadWorkspaces();
    };
    chrome.storage.onChanged.addListener(handleTokenArrival);
    return () => chrome.storage.onChanged.removeListener(handleTokenArrival);
  }, [loadWorkspaces]);

  useEffect(() => {
    void isNotifyOnSaveEnabled().then(setNotifyOnSave);
  }, []);

  // 분석 완료를 기다린다 — 감시는 백그라운드가 하고(watchItem.ts) 결과만 storage 로 받는다.
  // 팝업이 따로 폴링하면 같은 API 를 두 곳에서 두드리게 된다.
  useEffect(() => {
    if (status !== 'analyzing' || watchedItemId === null) return;
    const handleResult = (changes: Record<string, chrome.storage.StorageChange>) => {
      const result = changes[LAST_RESULT_KEY]?.newValue as
        { itemId: number; status: ItemStatus } | undefined;
      if (!result || result.itemId !== watchedItemId) return;
      setDoneStatus(result.status);
      setStatus('done');
    };
    chrome.storage.onChanged.addListener(handleResult);
    return () => chrome.storage.onChanged.removeListener(handleResult);
  }, [status, watchedItemId]);

  // 완료 표시를 잠깐 보여 준 뒤 **접는다**(창을 닫지 않는다) — 이어서 다른 페이지를 저장할 수 있다.
  useEffect(() => {
    if (status !== 'done') return;
    const timer = setTimeout(() => {
      setStatus('idle');
      setWatchedItemId(null);
      setDoneStatus(null);
    }, 1400);
    return () => clearTimeout(timer);
  }, [status]);

  useEffect(() => {
    setUrlExpanded(false);
    const frame = requestAnimationFrame(() => {
      const element = urlRef.current;
      setUrlOverflowing(Boolean(element && element.scrollHeight > element.clientHeight + 1));
    });
    return () => cancelAnimationFrame(frame);
  }, [url]);

  /**
   * 링크 코드 로그인 시작(-498). 흐름 전체(코드 발급 → 승인 창 → 폴링 → 토큰 저장)는
   * 백그라운드가 진행한다 — 승인 창이 포커스를 가져가는 순간 이 팝업은 닫히기 때문이다.
   * 여기서 처리할 수 있는 실패는 시작 실패(통신 없음 등)뿐이고, 그건 창이 열리기 전이라
   * 팝업이 아직 살아 있어 보여줄 수 있다.
   */
  async function handleLinkLogin() {
    setStatus('loading');
    setMessage('');
    const response = (await chrome.runtime.sendMessage({ type: 'deviceLinkLogin' })) as
      | { ok: boolean; message?: string }
      | undefined;
    if (response?.ok) {
      setStatus('idle');
      return;
    }
    setStatus('error');
    setMessage(response?.message ?? '로그인을 시작하지 못했습니다.');
  }

  async function handleSave() {
    if (!workspaceId) {
      setStatus('error'); setMessage('저장할 워크스페이스를 선택해 주세요.'); return;
    }
    if (!isSavableUrl(url)) {
      setStatus('error'); setMessage('이 페이지 주소는 저장할 수 없습니다.'); return;
    }
    setStatus('saving');
    setMessage('');
    try {
      // 최소 노출 시간: 접수 응답은 금방 오는데 그대로 두면 로딩이 한 프레임 번쩍이고 사라진다.
      const [created] = await Promise.all([
        saveUrl(workspaceId, url),
        new Promise((resolve) => setTimeout(resolve, 700)),
      ]);
      // 완료 알림은 백그라운드가 실제 처리(크롤·AI)가 끝난 걸 확인한 뒤에 띄운다 —
      // 팝업은 포커스를 잃으면 닫히므로 여기서 기다릴 수 없다(background/watchItem.ts).
      await chrome.runtime.sendMessage({
        type: 'watchItem',
        itemId: created.itemId,
        status: created.status,
        workspaceId,
      });
      setWatchedItemId(created.itemId);
      setStatus('analyzing');
      setMessage('');
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setAuthenticated(false);
      // 멤버십 403 = 지금 계정이 그 워크스페이스의 멤버가 아니다. 세션 물려받기 때문에
      // 토큰은 팝업 밖에서 다른 계정으로 바뀔 수 있는데(웹 로그인 자동 이어받기) 워크스페이스
      // 선택은 저장소에 남아, 이전 계정의 공간을 들고 있는 어긋남이 생긴다. 목록을 다시
      // 받으면 loadWorkspaces 가 선택을 현재 계정의 공간으로 바로잡는다 — 사용자는 한 번 더
      // 누르기만 하면 된다.
      //
      // 서버 문구로 멤버십 건만 가려낸다(WorkspaceAccessDeniedException 의 메시지) — 403 을
      // 전부 이걸로 처리하면 안 된다. 확장 Origin 이 CORS 허용 목록에 없을 때도 저장만 403 이
      // 나는데(SecurityConfig 주석의 "조회는 되는데 저장만 403"), 그건 본문 없는 평문 응답이라
      // 이 문구가 없고, 목록을 다시 받아 봐야 고쳐지지 않는다.
      if (error instanceof ApiError && error.status === 403
          && error.message.includes('워크스페이스 멤버가 아닙니다')) {
        const synced = await loadWorkspaces();
        setStatus('error');
        // 재동기화가 실패했으면 loadWorkspaces 가 이미 원인 메시지를 남겼다 — 덮지 않는다.
        if (synced) setMessage('저장할 공간이 예전 계정의 것이었어요. 다시 한 번 눌러 주세요.');
        return;
      }
      setStatus('error');
      setMessage(messageFrom(error));
    }
  }

  async function handleLogout() {
    // 확장 전용 세션(-498)이라 서버에서 이 세션만 끊으면 끝이다(api/auth.ts). 웹은 자기
    // 세션이 따로라 아무 영향이 없다 — 물려받기 시절의 차단 플래그·웹 탭 정리가 다 사라졌다.
    await Promise.all([
      logout(),
      clearSelectedWorkspaceId(),
      clearCachedWorkspaces(),
    ]);
    setAuthenticated(false);
    setWorkspaces([]);
    setWorkspaceId(null);
    setStatus('idle');
    setMessage('');
  }

  if (authenticated === null) {
    return <main style={styles.main}><p style={styles.muted}>불러오는 중…</p></main>;
  }

  if (!authenticated) {
    return (
      <main style={styles.main}>
        <h1 style={styles.title}>우주인에 저장</h1>
        <p style={styles.muted}>
          로그인하면 지금 보는 페이지를 바로 담을 수 있어요.
        </p>
        {/* 로그인 수단을 문구에 박지 않는다. 이 버튼이 하는 일은 **우주인 승인 화면을 여는
            것**(링크 코드, -498)이고, 웹에 로그인돼 있지 않으면 그 창이 로그인·가입부터
            이어준다 — 어떤 수단을 쓸지는 웹앱이 정하므로 여기 적어 두면 그 목록이 바뀔 때마다
            버튼이 거짓말을 한다. 마크도 같은 이유로 우주인 아이콘이다.
            '로그인'이 아니라 '시작하기'인 이유: 같은 버튼이 가입으로도 이어진다. */}
        <button onClick={handleLinkLogin} disabled={status === 'loading'} style={styles.login}>
          <img src="/icon128.png" alt="" width={18} height={18} style={{ flexShrink: 0 }} />
          {status === 'loading' ? '여는 중…' : '우주인 계정으로 시작하기'}
        </button>
        {/* 로그인 중 팝업은 포커스를 잃어 닫힌다 — 창에서 로그인만 마치면 연결·닫힘이
            자동이고, 아이콘을 다시 열면 로그인돼 있다. 그 한 문장이 안내의 전부다.
            웹에 로그인돼 있어도 다시 로그인한다(완전 격리, -498). */}
        <p style={styles.hint}>
          우주인 창에서 로그인하면 자동으로 연결되고 창이 닫혀요.
        </p>
        {message && <p style={styles.error}>{message}</p>}
      </main>
    );
  }

  const pendingOpen = status === 'saving' || status === 'analyzing' || status === 'done';

  return (
    <main style={styles.main}>
      <div style={styles.header}>
        {/* 표시용 브랜드 — 클릭도 호버 반응도 없다. 움직이는 로고는 저장 진행 표시에만 쓴다.
            확장 아이콘(icon128.png)을 그대로 재사용해 자산을 늘리지 않는다.
            모서리는 자산(icon128.png) 자체를 둥글게 깎았다 — CSS 로 자르면 툴바·확장 목록·
            알림처럼 우리가 스타일을 못 주는 곳에서는 그대로 사각형이다. */}
        <div style={styles.brand}>
          <img
            src="/icon128.png"
            alt=""
            width={20}
            height={20}
            style={{ display: 'block' }}
          />
          <h1 style={styles.title}>우주인에 저장</h1>
        </div>
        <button onClick={handleLogout} style={styles.link}>로그아웃</button>
      </div>
      {/* label 이 아니라 div 인 이유: 감싸는 대상이 form 컨트롤이 아니라 버튼+패널 조합이라
          label 로 두면 연결된 컨트롤이 없는 빈 라벨이 된다(접근성 경고). 선택기 쪽에
          aria-label 을 붙여 이름을 준다. */}
      <div style={styles.label}>저장할 곳
        <SpacePicker
          workspaces={workspaces}
          selectedId={workspaceId}
          disabled={status === 'loading'}
          onSelect={(id) => {
            setWorkspaceId(id);
            void setSelectedWorkspaceId(id);
          }}
        />
      </div>
      <div style={styles.urlBox}>
        <p ref={urlRef} style={urlExpanded ? styles.url : styles.urlCollapsed}>
          {url || '현재 탭의 주소를 읽지 못했습니다.'}
        </p>
        {urlOverflowing && (
          <button onClick={() => setUrlExpanded((expanded) => !expanded)} style={styles.more}>
            {urlExpanded ? '접기' : '더보기'}
          </button>
        )}
      </div>
      {/* 저장 진행 영역은 **접히고 펼쳐진다**(창을 닫지 않는다). max-height 를 전환해 높이가
          늘어나고 줄어드는 것처럼 보이게 한다 — 갑자기 나타나고 사라지면 팝업이 튀어 보인다.
          내용을 항상 렌더해 두는 이유: 언마운트되면 접히는 애니메이션을 보여 줄 대상이 없다. */}
      <div style={{ ...styles.collapsible, maxHeight: pendingOpen ? 200 : 0, opacity: pendingOpen ? 1 : 0 }}>
        <div style={styles.pending}>
          {status === 'done' ? (
            <div style={styles.markSlot}>
              {/* 로고는 자리에 남겨 두고 페이드아웃시켜야 체크가 같은 위치에서 커진다 */}
              <div style={styles.markFading}><InteractiveLogo size={64} hovered /></div>
              <div style={styles.markOverlay}>
                <SaveDoneMark size={64} failed={doneStatus === 'FAILED'} />
              </div>
            </div>
          ) : (
            /* hovered 를 켜 두면 스파클이 궤도를 공전한다 — 그게 곧 진행 표시다 */
            <InteractiveLogo size={64} hovered />
          )}
          <p style={styles.pendingTitle}>
            {status === 'saving' ? '우주인으로 보내는 중…'
              : status === 'analyzing' ? '우주인에서 분석 중…'
              : doneStatus === 'FAILED' ? '분석에 실패했어요'
              /* PARTIAL 도 완료로 본다 — 아이템은 저장됐고 미리보기도 나온다. 1.4초 뒤 접히는
                 문구에서 굳이 구분할 이유가 없다(자세한 내용은 알림 문구가 알려 준다). */
              : '분석 완료!'}
          </p>
          {status === 'analyzing' && (
            <p style={styles.hint}>창을 닫아도 알림으로 알려드려요.</p>
          )}
        </div>
      </div>

      {!pendingOpen && (
        <button onClick={handleSave}
          disabled={status === 'loading' || !workspaceId}
          style={styles.primary}>
          현재 페이지 저장
        </button>
      )}
      {!workspaces.length && status !== 'loading' &&
        <p style={styles.error}>사용 가능한 워크스페이스가 없습니다.</p>}
      {message && <p style={styles.error}>{message}</p>}
      {contextFeedback && (
        <p style={styles.error}>우클릭 저장: {contextFeedback.message}</p>
      )}

      <div style={styles.footer}>
        {/* 알림은 완료를 알리는 유일한 수단이라 기본 켜짐이지만, 방해가 되면 끌 수 있어야 한다 */}
        <label style={styles.toggle}>
          <input
            type="checkbox"
            checked={notifyOnSave}
            onChange={(e) => {
              setNotifyOnSave(e.target.checked);
              void setNotifyOnSaveEnabled(e.target.checked);
            }}
            style={{ accentColor: ACCENT, margin: 0 }}
          />
          완료 알림 받기
        </label>
        {/* 아이콘만으로는 바로가기인 줄 모른다는 피드백 — 문구를 그대로 노출한다 */}
        {/* 지금 고른 스페이스로 바로 간다 — 방금 저장한 게 라이브러리에 쌓이므로 그 화면을 연다.
            아직 목록을 못 불러왔으면 /home 이 개인 스페이스로 넘겨준다. */}
        <button
          type="button"
          onClick={() => void chrome.tabs.create({
            url: workspaceId
              ? `${WEB_ORIGIN}/workspace/${workspaceId}/library`
              : `${WEB_ORIGIN}/home`,
          })}
          style={styles.footerLink}
        >
          우주인 열기 ↗
        </button>
      </div>
    </main>
  );
}

// 색은 웹앱 테마 토큰(frontend/src/styles/theme.css 다크 값)을 그대로 옮긴 것이다 —
// 확장은 Tailwind 를 쓰지 않으므로 변수 대신 값으로 박는다.
const SPACE = '#0e1017';
const SURFACE = '#20242f';
const SURFACE_2 = '#2a2e3a';
const SURFACE_3 = '#343947';
const BORDER = '#313543';
const TEXT_1 = '#f0f2f6';
const TEXT_2 = '#b0b6c3';
const TEXT_3 = '#7b8290';
const ACCENT = '#7c6cf0';
const DANGER = '#ef7a72';

const buttonBase: React.CSSProperties = {
  boxSizing: 'border-box',
  width: '100%',
  height: 40,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  border: 0,
  borderRadius: 12,
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
};

const styles: Record<string, React.CSSProperties> = {
  main: {
    width: 320, padding: 18, background: SPACE, color: TEXT_1,
    // 웹앱 --font-sans 와 같은 스택. Pretendard 는 popup.html 의 @font-face 로 실려 있고,
    // 뒤쪽 후보는 폰트 로드 실패 시 웹앱과 같은 모습으로 떨어지게 하려고 그대로 옮겼다.
    fontFamily: "'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, 'Segoe UI', sans-serif",
    display: 'flex', flexDirection: 'column', gap: 10,
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  // 표시용이라 cursor 를 주지 않는다 — 버튼이던 시절의 pointer 가 남아 눌릴 것처럼 보였다
  brand: { display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, color: TEXT_1 },
  footer: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
    marginTop: 2, paddingTop: 10, borderTop: `1px solid ${BORDER}`,
  },
  toggle: {
    display: 'flex', alignItems: 'center', gap: 6,
    color: TEXT_3, fontSize: 12, cursor: 'pointer',
  },
  footerLink: {
    padding: 0, border: 0, background: 'transparent',
    color: ACCENT, fontFamily: 'inherit', fontSize: 12, fontWeight: 600, cursor: 'pointer',
  },
  pending: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
    padding: '10px 0 2px',
  },
  pendingTitle: { margin: 0, fontSize: 14, fontWeight: 600, color: TEXT_1 },
  collapsible: {
    overflow: 'hidden',
    transition: 'max-height 0.34s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.24s ease-out',
  },
  markSlot: { position: 'relative', width: 64, height: 64 },
  markFading: { animation: 'wj-fade-out 0.24s ease-out both' },
  markOverlay: { position: 'absolute', inset: 0 },
  title: { margin: 0, fontSize: 16, fontWeight: 600 },
  muted: { margin: 0, fontSize: 14.5, lineHeight: 1.6, color: TEXT_2 },
  hint: { margin: 0, fontSize: 11, lineHeight: 1.6, color: TEXT_3, textAlign: 'center' },
  // minWidth: 0 이 필요한 이유 — flex/grid 자식의 기본값은 min-width:auto 라서 내용보다
  // 작아지지 못한다. 긴 워크스페이스 이름이 들어오면 이 칸이 부풀어 팝업 밖으로 삐져나간다
  // (실측: 320px 컨테이너에서 트리거가 423px 까지 커졌다). 0 을 주면 줄어들며 … 로 잘린다.
  label: { display: 'grid', gap: 6, minWidth: 0, fontSize: 12, fontWeight: 600, color: TEXT_2 },
  input: {
    boxSizing: 'border-box', width: '100%', height: 36, padding: '0 10px',
    border: `1px solid ${BORDER}`, borderRadius: 12,
    background: SURFACE_2, color: TEXT_1, fontSize: 14,
    // 네이티브 select 의 펼침 목록(optgroup 헤더 포함)은 OS 가 그린다 — 이걸 안 주면
    // 다크 팝업인데 목록만 흰 배경으로 떠서 튄다.
    colorScheme: 'dark',
  },
  // 웹앱 GoogleAuthButton 과 같은 껍데기 — 흰 버튼은 다크 테마에서 혼자 튄다
  login: { ...buttonBase, border: `1px solid ${BORDER}`, background: SURFACE_2, color: TEXT_1 },
  primary: { ...buttonBase, background: ACCENT, color: '#ffffff' },
  link: { border: 0, background: 'transparent', color: TEXT_3, fontSize: 12, cursor: 'pointer' },
  urlBox: { padding: 10, borderRadius: 12, background: SURFACE, border: `1px solid ${BORDER}` },
  url: { margin: 0, fontSize: 12, lineHeight: 1.5, color: TEXT_2, wordBreak: 'break-all' },
  urlCollapsed: {
    margin: 0, fontSize: 12, lineHeight: 1.5, color: TEXT_2, wordBreak: 'break-all',
    display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden',
  },
  more: {
    display: 'block', margin: '8px 0 0 auto', padding: 0, border: 0,
    background: 'transparent', color: ACCENT, fontSize: 12, fontWeight: 600, cursor: 'pointer',
  },
  error: { margin: 0, color: DANGER, fontSize: 12, lineHeight: 1.5 },
};
