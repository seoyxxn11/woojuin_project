import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import Modal from '@/components/ui/Modal';
import { approveDeviceLink } from '@/services/auth';

interface WatchLinkModalProps {
  open: boolean;
  onClose: () => void;
  /** 승인 성공 시 — 부모가 기기 목록을 다시 받아 새 기기가 나타나게 한다 */
  onApproved: () => void;
  /**
   * 열릴 때 미리 채울 코드 — 크롬 익스텐션이 `?linkCode=` 로 들어올 때 쓴다(S15P11C105-498).
   * 익스텐션은 코드를 자기가 발급받았으므로 사용자가 옮겨 적을 필요가 없다.
   */
  initialCode?: string;
  /**
   * 참이면 승인 버튼까지 대신 누른다 — 0클릭. **이 코드가 정말 이 브라우저의 익스텐션이
   * 발급받은 것임을 대조로 확인한 경우에만** 부모가 켠다(ConnectedDevicesCard). URL 의
   * 코드를 무조건 자동 승인하면 아무 사이트나 계정에 제 기기를 붙일 수 있다.
   */
  autoApprove?: boolean;
}

/**
 * 기기 링크 코드 승인 (S15P11C105-458 워치, -498 크롬 익스텐션).
 *
 * 기기 화면의 6자리 코드를 여기 입력하면 서버가 그 코드에 이 계정을 붙이고,
 * 기기는 폴링으로 토큰을 받아 간다 — 기기 쪽 입력이 0회가 되는 흐름의 웹 절반이다.
 */
const WatchLinkModal = ({
  open,
  onClose,
  onApproved,
  initialCode,
  autoApprove = false,
}: WatchLinkModalProps) => {
  const [code, setCode] = useState('');
  // StrictMode(dev)의 이중 실행·리렌더에 자동 승인이 두 번 나가지 않게 잠근다.
  const autoSubmitted = useRef(false);

  const mutation = useMutation({
    // 함수 참조를 그대로 주면 react-query 가 두 번째 인자(컨텍스트)까지 넘긴다 — 코드만 고정
    mutationFn: (linkCode: string) => approveDeviceLink(linkCode),
    onSuccess: () => {
      setCode('');
      onApproved();
    },
  });

  // 프리필은 "열리는 순간"에만 — 열린 뒤 사용자가 고친 입력을 리렌더가 덮어쓰면 안 된다.
  useEffect(() => {
    if (open && initialCode) {
      const prefill = initialCode
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '')
        .slice(0, 6);
      setCode(prefill);
      if (autoApprove && prefill.length === 6 && !autoSubmitted.current) {
        autoSubmitted.current = true;
        mutation.mutate(prefill);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mutation 은 렌더마다 새 객체라 넣으면 무한 재실행
  }, [open, initialCode, autoApprove]);

  const close = () => {
    setCode('');
    mutation.reset();
    onClose();
  };

  const submit = () => {
    if (code.length === 6 && !mutation.isPending) mutation.mutate(code);
  };

  return (
    <Modal open={open} onClose={close} title="기기 연결">
      <p className="text-[13px] leading-relaxed text-text-2">
        워치나 크롬 익스텐션에 표시된 6자리 코드를 입력하세요. 승인하면 그 기기가 이 계정으로
        로그인됩니다.
      </p>

      <input
        aria-label="기기 코드"
        value={code}
        maxLength={6}
        autoCapitalize="characters"
        autoComplete="one-time-code"
        spellCheck={false}
        disabled={mutation.isPending}
        // 코드는 대문자만 발급된다 — 서버도 관용을 갖지만 화면에서 먼저 맞춰 보여준다
        onChange={(event) => setCode(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))}
        onKeyDown={(event) => {
          if (event.key === 'Enter') submit();
        }}
        className="mt-4 w-full rounded-lg bg-surface-2 px-4 py-3 text-center font-mono text-xl font-extrabold tracking-[0.4em] text-text-1 outline-none focus:ring-2 focus:ring-accent"
        placeholder="······"
      />

      {mutation.isError && (
        <p className="mt-2 text-xs text-[#C74E4B]">
          코드가 만료되었거나 올바르지 않습니다. 기기에서 새 코드를 확인해 주세요.
        </p>
      )}

      {mutation.isSuccess ? (
        <p className="mt-4 text-[13px] font-semibold text-accent">
          승인되었습니다. 기기가 곧 로그인되고 목록에 나타납니다.
        </p>
      ) : (
        <button
          type="button"
          disabled={code.length !== 6 || mutation.isPending}
          onClick={submit}
          className="mt-4 w-full rounded-lg bg-accent px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {mutation.isPending ? '승인 중…' : '기기 연결'}
        </button>
      )}
    </Modal>
  );
};

export default WatchLinkModal;
