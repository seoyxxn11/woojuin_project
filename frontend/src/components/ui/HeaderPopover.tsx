import {
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
  type MouseEvent,
  type ReactElement,
  type ReactNode,
} from 'react';
import { classNames } from '@/utils/classNames';

interface HeaderPopoverProps {
  /**
   * 여는 버튼. onClick 을 가로채 토글로 쓰고, 원래 onClick 도 함께 호출한다.
   * aria-haspopup·aria-expanded·aria-controls 를 자동으로 붙인다.
   */
  trigger: ReactElement<{
    onClick?: (e: MouseEvent) => void;
    'aria-haspopup'?: boolean;
    'aria-expanded'?: boolean;
    'aria-controls'?: string;
  }>;
  /**
   * 패널 내용. 함수로 주면 close 를 받아 안에서 닫을 수 있다
   * (예: 폼 제출 후 자동으로 닫기).
   */
  children: ReactNode | ((close: () => void) => ReactNode);
}

/**
 * 헤더 버튼 아래로 뜨는 팝오버 껍데기.
 *
 * 알림·공유·새로 만들기처럼 "버튼 밑에 카드 하나 띄우는" 패턴의 공통부.
 * 여기서 책임지는 건 **여닫기·바깥클릭·ESC·위치·카드 룩** 뿐이고,
 * 카드 안 내용물(목록/폼/…)은 children 이 각자 디자인한다.
 *
 * 가운데 뜨는 전체화면 모달은 Modal.tsx 를 쓴다 — 이건 트리거에 붙는 팝오버다.
 */
const HeaderPopover = ({ trigger, children }: HeaderPopoverProps) => {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  const close = () => setOpen(false);

  useEffect(() => {
    if (!open) return;

    // 바깥 클릭 — 트리거·패널을 감싼 wrap 밖이면 닫는다
    const onPointerDown = (e: PointerEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) close();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const triggerNode = isValidElement(trigger)
    ? cloneElement(trigger, {
        onClick: (e: MouseEvent) => {
          trigger.props.onClick?.(e);
          setOpen((v) => !v);
        },
        'aria-haspopup': true,
        'aria-expanded': open,
        'aria-controls': panelId,
      })
    : trigger;

  return (
    <div ref={wrapRef} className="relative inline-flex">
      {triggerNode}

      {open && (
        <>
          {/*
            모바일에서만 뒤를 덮는다 — 가운데 뜬 패널이 성좌 배경에 묻히지 않게.
            wrapRef 안이라 바깥클릭 판정에 안 걸리므로 직접 close 를 건다.
          */}
          <div className="fixed inset-0 z-40 bg-black/50 desktop:hidden" onClick={close} />

          <div
            id={panelId}
            role="dialog"
            className={classNames(
              'z-[45] overflow-hidden rounded-lg border border-border bg-surface p-4 shadow-float',
              // 모바일 — 화면 한가운데. 좁은 기기에서 넘치지 않게 폭을 제한한다
              'fixed left-1/2 top-1/2 max-w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2',
              // 데스크톱 — 트리거 바로 아래, 오른쪽 끝 맞춤
              'desktop:absolute desktop:left-auto desktop:top-[calc(100%+8px)] desktop:right-0 desktop:translate-x-0 desktop:translate-y-0',
            )}
          >
            {typeof children === 'function' ? children(close) : children}
          </div>
        </>
      )}
    </div>
  );
};

export default HeaderPopover;
