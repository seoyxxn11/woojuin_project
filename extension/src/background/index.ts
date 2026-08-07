import { ApiError, WEB_ORIGIN } from '@/api/client';
import { saveImage, saveMemo } from '@/api/items';
import { beginDeviceLinkLogin, closeLinkWindow, isPendingLinkCode } from '@/auth/deviceLink';
import { getWorkspaces } from '@/api/workspaces';
import { AUTH_STORAGE, getAccessToken, getRefreshToken } from '@/storage/authStorage';
import { openFromNotification, resumeWatchOnAlarm, watchItem } from '@/background/watchItem';
import {
  findWorkspaceLabel,
  isImageSaveMenu,
  refreshContextMenus,
  SAVE_SELECTION_ID,
  workspaceIdFromMenu,
} from '@/background/contextMenus';
import {
  getSelectedWorkspaceId,
  setCachedWorkspaces,
  WORKSPACE_LIST_KEY,
} from '@/storage/workspaceStorage';

const IMAGE_MAX_BYTES = 10 * 1024 * 1024;
const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp']);
const activeSaves = new Set<string>();
const FEEDBACK_KEY = 'contextSaveFeedback';
const NOTIFICATION_ICON = chrome.runtime.getURL('icon128.png');

/**
 * 워크스페이스 목록을 서버에서 새로 받아 캐시한다.
 *
 * 팝업을 한 번도 열지 않아도 우클릭 메뉴에 스페이스가 떠야 한다 — 로그인은 웹앱 세션에서
 * 링크 승인만으로 끝나므로(deviceLink.ts) 팝업을 안 거치고 저장부터 하는 경로가 실제로 있다.
 * 실패는 삼킨다: 목록이 없으면 메뉴가 단일 항목으로 뜰 뿐 저장 자체는 막히지 않는다.
 */
async function syncWorkspaces(): Promise<void> {
  const [accessToken, refreshToken] = await Promise.all([getAccessToken(), getRefreshToken()]);
  if (!accessToken && !refreshToken) return;
  try {
    await setCachedWorkspaces(await getWorkspaces());
  } catch (error) {
    console.debug('워크스페이스 목록 동기화 실패:', error);
  }
}

function bootstrap(): void {
  void refreshContextMenus();
  void syncWorkspaces();
}

chrome.runtime.onInstalled.addListener(bootstrap);
chrome.runtime.onStartup.addListener(bootstrap);

// 목록이 바뀌면 메뉴를 다시 짠다 — 팝업이 새로 받아 왔거나, 로그아웃으로 비워졌을 때다.
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local' && WORKSPACE_LIST_KEY in changes) void refreshContextMenus();
});

// 아이템 처리 완료 감시 — 팝업은 닫히면 끝나므로 감시는 여기서 한다(watchItem.ts 참고).
chrome.alarms.onAlarm.addListener(resumeWatchOnAlarm);
chrome.notifications.onClicked.addListener(openFromNotification);
chrome.runtime.onMessage.addListener((message: unknown) => {
  const request = message as {
    type?: string;
    itemId?: number;
    workspaceId?: number;
    status?: 'PROCESSING' | 'DONE' | 'PARTIAL' | 'FAILED';
  };
  if (request?.type !== 'watchItem' || typeof request.itemId !== 'number'
      || typeof request.workspaceId !== 'number' || !request.status) return;
  void watchItem(request.itemId, request.status, request.workspaceId);
});

// 링크 코드 로그인(S15P11C105-498) — 팝업이 시작을 요청하면 흐름 전체는 여기서 진행한다.
// 승인 창이 포커스를 가져가는 순간 팝업은 닫히므로 폴링을 팝업에 둘 수 없다.
// 승인 결과는 storage 의 토큰 변화로 전달된다(팝업의 handleTokenArrival 이 듣는다).
// 토큰이 저장되는 순간 우클릭 메뉴도 채워지도록 목록 동기화를 함께 건다.
chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
  if ((message as { type?: string })?.type !== 'deviceLinkLogin') return;
  beginDeviceLinkLogin()
    .then(() => sendResponse({ ok: true }))
    .catch((error: unknown) => sendResponse({
      ok: false,
      message: error instanceof Error ? error.message : '로그인을 시작하지 못했습니다.',
    }));
  return true; // sendResponse 를 비동기로 쓴다
});

// 승인 페이지(우주인 웹)의 0클릭 확인 — "이 코드, 네가 발급받은 것 맞아?"에만 답한다.
// 대조가 성립해야 페이지가 자동 승인하므로, 아무 사이트가 열어 둔 linkCode URL 로는
// 자동 승인이 일어나지 않는다(그 코드는 여기 저장된 코드와 다르다). manifest 의
// externally_connectable 이 발신자를 우주인 origin 으로 제한하고, 아래 origin 검사가
// 빌드 모드의 웹 주소까지 좁힌다.
chrome.runtime.onMessageExternal.addListener((message: unknown, sender, sendResponse) => {
  const request = message as { type?: string; code?: string };
  if (request?.type !== 'isPendingLinkCode' || typeof request.code !== 'string') return;
  if (sender.origin !== WEB_ORIGIN) {
    sendResponse({ mine: false });
    return;
  }
  void isPendingLinkCode(request.code).then((mine) => sendResponse({ mine }));
  return true; // sendResponse 를 비동기로 쓴다
});

// 링크 승인으로 토큰이 저장되면 우클릭 메뉴 재료(워크스페이스 목록)를 받아 두고,
// 승인 창도 닫는다. 닫기는 폴링 루프도 하지만(deviceLink.ts) 여기가 안전망이다 —
// 저장과 지연 닫기 사이에 서비스워커가 재시작하는 등 루프의 닫기가 못 도는 경우를
// "토큰이 도착했다"는 사실 자체로 잡는다(창이 이미 없으면 아무 일도 안 한다).
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === AUTH_STORAGE.refresh.area && changes[AUTH_STORAGE.refresh.key]?.newValue) {
    void syncWorkspaces();
    void closeLinkWindow(1_200);
  }
});

/**
 * 우클릭 저장의 **접수** 결과를 알린다.
 *
 * 성공은 배지·툴팁으로만 알린다 — 완료 알림은 실제 처리가 끝난 뒤 watchItem 이 띄우므로,
 * 여기서도 알림을 띄우면 한 번의 저장에 알림이 두 번 뜬다.
 * 실패는 알림으로 띄운다: 사용자가 조치해야 하고(권한 거부·미로그인 등) 배지만으로는 못 알아챈다.
 * 그래서 실패 알림은 '완료 알림 받기' 설정과 무관하게 항상 띄운다.
 *
 * storage 에는 **실패만** 남긴다. 이 값을 읽는 곳은 팝업뿐인데, 성공까지 남기면 우클릭으로
 * 끝낸 저장을 팝업에서 또 알리게 된다 — 배지·툴팁·완료 알림에 이어 네 번째다. 우클릭 저장의
 * 요점이 팝업을 안 여는 것이라 더욱 앞뒤가 안 맞는다. 실패는 팝업에 이유가 남아 있어야
 * 조치할 수 있어 남긴다(알림은 놓치거나 OS 에서 막혀 있을 수 있다).
 */
async function showFeedback(success: boolean, message: string): Promise<void> {
  await Promise.all([
    chrome.action.setBadgeBackgroundColor({ color: success ? '#16784b' : '#c33030' }),
    chrome.action.setBadgeText({ text: success ? 'OK' : '!' }),
    chrome.action.setTitle({ title: message }),
    ...(success ? [] : [
      chrome.storage.local.set({
        [FEEDBACK_KEY]: { success, message, createdAt: Date.now() },
      }),
      chrome.notifications.create(`context-save-failed-${Date.now()}`, {
        type: 'basic',
        iconUrl: NOTIFICATION_ICON,
        title: '우주인 저장 실패',
        message,
        priority: 1,
      }),
    ]),
  ]);
  setTimeout(() => void chrome.action.setBadgeText({ text: '' }), 8000);
}

/**
 * 저장할 스페이스를 정한다.
 *
 * 하위 메뉴로 고른 곳이 있으면 그걸 쓰고, 없으면(스페이스가 하나뿐이거나 목록을 아직 못 받아
 * 단일 메뉴로 떴을 때) 팝업에서 고른 곳으로 떨어진다. 하위 메뉴 선택은 그 저장 한 번에만
 * 적용한다 — 팝업의 기본 저장 위치까지 바꿔 버리면 우클릭 한 번이 다음 저장들의 목적지를
 * 조용히 옮겨 놓는다.
 */
async function requireSaveContext(chosenWorkspaceId: number | null): Promise<number> {
  const [accessToken, refreshToken, selectedWorkspaceId] = await Promise.all([
    getAccessToken(),
    getRefreshToken(),
    getSelectedWorkspaceId(),
  ]);
  if (!accessToken && !refreshToken) throw new ApiError('로그인이 필요합니다.', 401);
  const workspaceId = chosenWorkspaceId ?? selectedWorkspaceId;
  if (!workspaceId) throw new Error('팝업에서 워크스페이스를 먼저 선택해 주세요.');
  return workspaceId;
}

/**
 * 이미지 출처 권한을 확보한다.
 *
 * request 의 결과만 믿지 않는 이유: 서비스워커는 유휴 30초면 종료되고 **다음 우클릭이 그 워커를
 * 깨우면서** 이벤트를 전달하는데, 그렇게 깨어난 회차에는 사용자 제스처 토큰이 남아 있지 않아
 * request 가 거부되거나 false 로 돌아올 수 있다. 반면 한 번 허용한 출처는 그대로 남아 있으므로,
 * request 가 실패하면 **이미 가진 권한을 직접 확인해** 통과시킨다.
 * (contains 는 조회라 제스처가 필요 없다.)
 *
 * 이걸 안 하면 '처음 한 번만 저장되고 그 뒤로는 계속 실패'하는 증상이 된다.
 */
async function ensureImagePermission(origin: string, requested?: Promise<boolean>): Promise<boolean> {
  try {
    if (requested && (await requested)) return true;
  } catch (error) {
    console.debug('이미지 출처 권한 요청이 실패했다 — 보유 권한을 확인한다:', error);
  }
  return chrome.permissions.contains({ origins: [origin] });
}

async function downloadImage(srcUrl: string, requested?: Promise<boolean>): Promise<File> {
  const url = new URL(srcUrl);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('data: 및 blob: 이미지는 저장할 수 없습니다.');
  const origin = `${url.origin}/*`;
  if (!(await ensureImagePermission(origin, requested))) {
    throw new Error('이미지를 내려받을 사이트 권한이 필요합니다.');
  }

  let response: Response;
  try {
    response = await fetch(srcUrl, { credentials: 'include' });
  } catch (error) {
    // 요청이 아예 못 나간 경우다(출처 권한 미반영·네트워크·사이트 차단). 원문은 'Failed to fetch'
    // 한 줄뿐이라 그대로 띄우면 사용자가 할 수 있는 게 없다 — 판단용 정보는 콘솔에 남긴다.
    console.error('이미지 다운로드 실패:', { srcUrl, origin, error });
    throw new Error('이미지를 내려받지 못했어요. 사이트가 외부 접근을 막았을 수 있어요.');
  }
  if (!response.ok) throw new Error(`이미지 다운로드에 실패했습니다. (${response.status})`);
  if (Number(response.headers.get('content-length') || 0) > IMAGE_MAX_BYTES) {
    throw new Error('이미지는 10MB 이하여야 합니다.');
  }
  const blob = await response.blob();
  const contentType = blob.type.toLowerCase().split(';')[0];
  if (!IMAGE_TYPES.has(contentType)) {
    throw new Error(`지원하지 않는 이미지 형식입니다. (${contentType || '형식 정보 없음'})`);
  }
  if (blob.size > IMAGE_MAX_BYTES) throw new Error('이미지는 10MB 이하여야 합니다.');
  const extension = contentType.split('/')[1].replace('jpeg', 'jpg');
  return new File([blob], `woojuin-image.${extension}`, { type: contentType });
}

/** 저장한 스페이스 id 를 돌려준다 — 접수 문구에 어디로 갔는지 적는 데 쓴다. */
async function handleContextSave(
  info: chrome.contextMenus.OnClickData,
  imagePermission?: Promise<boolean>,
): Promise<number> {
  const workspaceId = await requireSaveContext(workspaceIdFromMenu(info.menuItemId));
  // 저장은 접수까지만이고 완료 알림은 watchItem 이 실제 처리가 끝난 뒤에 띄운다.
  if (info.menuItemId === SAVE_SELECTION_ID) {
    const content = info.selectionText?.trim();
    if (!content) throw new Error('빈 텍스트는 저장할 수 없습니다.');
    const created = await saveMemo(workspaceId, content);
    await watchItem(created.itemId, created.status, workspaceId);
  } else if (isImageSaveMenu(info.menuItemId) && info.srcUrl) {
    // imagePermission 이 없어도 downloadImage 가 보유 권한을 확인한다 — 워커가 클릭으로
    // 깨어난 회차에는 request 를 걸 제스처가 없을 수 있고, 그때도 이미 허용한 출처면 저장된다.
    const created = await saveImage(workspaceId, await downloadImage(info.srcUrl, imagePermission));
    await watchItem(created.itemId, created.status, workspaceId);
  }
  return workspaceId;
}

chrome.contextMenus.onClicked.addListener((info) => {
  // permissions.request는 사용자 제스처가 유지되는 동기 이벤트 구간에서 즉시 호출해야 한다.
  // 인증/워크스페이스 조회를 await한 뒤 호출하면 Chrome이 요청을 거부한다.
  let imagePermission: Promise<boolean> | undefined;
  if (isImageSaveMenu(info.menuItemId) && info.srcUrl) {
    const url = new URL(info.srcUrl);
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      imagePermission = chrome.permissions.request({ origins: [`${url.origin}/*`] });
    }
  }
  const requestKey = `${String(info.menuItemId)}:${info.srcUrl ?? info.selectionText?.trim() ?? ''}`;
  if (activeSaves.has(requestKey)) return;
  activeSaves.add(requestKey);
  void handleContextSave(info, imagePermission)
    // 어디로 갔는지 적는다 — 하위 메뉴로 고른 곳은 팝업에 표시된 스페이스와 다를 수 있어서,
    // 문구가 '우주인으로 보냈어요' 뿐이면 잘못 골랐는지 확인할 방법이 없다.
    // 조사는 '에'를 쓴다 — 이름이 한글이든 영문이든 받침에 따라 달라지지 않는다.
    .then(async (workspaceId) => {
      const label = await findWorkspaceLabel(workspaceId);
      return showFeedback(true, label
        ? `${label}에 보냈어요. 정리가 끝나면 알려드릴게요.`
        : '우주인으로 보냈어요. 정리가 끝나면 알려드릴게요.');
    })
    .catch((error: unknown) => {
      console.error('우주인 저장 실패:', error);
      const message = error instanceof Error ? error.message : '우클릭 저장에 실패했습니다.';
      return showFeedback(false, message);
    })
    .finally(() => activeSaves.delete(requestKey));
});
