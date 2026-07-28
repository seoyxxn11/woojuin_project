import { ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

/** 배경 클릭 또는 esc 버튼 없이 X로만 닫는 단순 모달 — 도메인을 모르는 디자인 시스템 조각 */
const Modal = ({ open, onClose, title, children }: ModalProps) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-lg bg-surface p-5 shadow-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-bold text-text-1">{title}</h2>
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            className="text-text-3 hover:text-text-1"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

export default Modal;
