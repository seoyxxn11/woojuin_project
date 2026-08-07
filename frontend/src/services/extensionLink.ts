/**
 * 크롬 익스텐션과의 0클릭 링크 승인 확인 (S15P11C105-498).
 *
 * 승인 페이지(/my?linkCode=)는 URL 의 코드를 **그냥 믿고 자동 승인하면 안 된다** — 아무
 * 사이트나 그 URL 로 창을 열 수 있어서, 로그인된 사용자의 계정에 공격자의 "기기"가 소리
 * 없이 붙는다. 그래서 익스텐션에게 "이 코드 네가 발급받은 것 맞아?"라고 물어보고, 맞다는
 * 답을 받았을 때만 자동 승인한다. 답을 못 받으면(익스텐션 없음·다른 코드·워치) 수동 승인
 * 버튼으로 남는다.
 *
 * 통로는 크롬의 externally_connectable 메시징이다 — 익스텐션이 manifest 에서 우주인
 * origin 에만 이 통로를 연다. 익스텐션 ID 는 manifest 의 key 로 고정돼 있어(스토어·팀원
 * 로컬 모두 동일) 상수로 둔다.
 */

const EXTENSION_ID = 'aifkmpjpjedlamliamnloliencimdfco';

/** 답이 없으면 수동으로 넘어가는 시한 — 익스텐션이 없으면 콜백이 아예 안 올 수 있다. */
const CONFIRM_TIMEOUT_MS = 700;

interface ChromeRuntimeMessaging {
  sendMessage?: (
    extensionId: string,
    message: unknown,
    callback: (response?: { mine?: boolean; linkCode?: string }) => void,
  ) => void;
  lastError?: unknown;
}

/**
 * 로그인 성공 순간, 이 브라우저의 익스텐션도 조용히 연결해 준다 (0클릭·창 없음).
 *
 * 익스텐션에게 "코드 하나 줘"라고 요청하고(requestLinkCode), 받은 코드를 방금 로그인한
 * 세션으로 곧바로 승인한다 — 코드가 **익스텐션에게서 직접 온 것**이라 linkCode URL 처럼
 * 위조될 표면이 없고, 통로 자체가 우주인 origin 전용이다. 익스텐션이 없거나 이미
 * 로그인돼 있으면 빈 응답이 와서 아무 일도 일어나지 않는다.
 *
 * 실패는 전부 삼킨다 — 로그인 흐름을 막을 이유가 없고, 수동 경로(익스텐션 팝업의
 * 시작하기 버튼)가 항상 남아 있다.
 */
export function offerExtensionAutoLink(): void {
  const runtime = (window as { chrome?: { runtime?: ChromeRuntimeMessaging } }).chrome?.runtime;
  const send = runtime?.sendMessage;
  if (!runtime || !send) return;
  try {
    send.call(runtime, EXTENSION_ID, { type: 'requestLinkCode' }, (response) => {
      void runtime.lastError;
      const code = response?.linkCode;
      if (typeof code !== 'string' || code.length !== 6) return;
      void import('@/services/auth').then(({ approveDeviceLink }) =>
        approveDeviceLink(code).catch(() => {
          // 승인 실패(코드 만료 등) — 익스텐션 폴링이 시한으로 접히고, 수동 경로가 남는다.
        }),
      );
    });
  } catch {
    // 통로가 없는 브라우저 — 조용히 넘어간다.
  }
}

/** 이 코드가 (이 브라우저의) 우주인 익스텐션이 방금 발급받은 것인지 확인한다. */
export function confirmExtensionLinkCode(code: string): Promise<boolean> {
  const runtime = (window as { chrome?: { runtime?: ChromeRuntimeMessaging } }).chrome?.runtime;
  const send = runtime?.sendMessage;
  // 익스텐션이 없거나(externally_connectable 미노출) 크롬이 아니면 통로 자체가 없다.
  if (!runtime || !send) return Promise.resolve(false);

  return new Promise((resolve) => {
    const timer = window.setTimeout(() => resolve(false), CONFIRM_TIMEOUT_MS);
    try {
      send.call(runtime, EXTENSION_ID, { type: 'isPendingLinkCode', code }, (response) => {
        window.clearTimeout(timer);
        // lastError 를 읽어야 크롬이 "Unchecked runtime.lastError" 경고를 안 남긴다.
        void runtime.lastError;
        resolve(response?.mine === true);
      });
    } catch {
      window.clearTimeout(timer);
      resolve(false);
    }
  });
}
