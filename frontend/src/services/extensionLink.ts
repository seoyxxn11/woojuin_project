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
    callback: (response?: { mine?: boolean }) => void,
  ) => void;
  lastError?: unknown;
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
