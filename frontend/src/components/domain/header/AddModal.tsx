import { useState } from 'react';
import { classNames } from '@/utils/classNames';
import type { ItemType } from '@/types/item';
import UrlForm from './UrlForm';
import ImageForm from './ImageForm';
import MemoForm from './MemoForm';

interface AddModalProps {
  /** 저장 후 팝오버를 닫는다 */
  onDone: () => void;
}

const TABS: { type: ItemType; label: string }[] = [
  { type: 'URL', label: '링크' },
  { type: 'IMAGE', label: '사진' },
  { type: 'MEMO', label: '텍스트' },
];

/**
 * 새로 만들기 팝오버 내용 — 탭 전환만 맡는다.
 *
 * 각 폼은 자기 상태를 자기가 들고 있고, 탭을 벗어나면 언마운트되며 정리된다.
 * 바깥 껍데기(HeaderPopover)가 padding 을 주므로 여기서는 주지 않는다.
 */
const AddModal = ({ onDone }: AddModalProps) => {
  const [tab, setTab] = useState<ItemType>('URL');

  return (
    <section className="w-[300px]">
      <div
        role="tablist"
        aria-label="추가할 종류"
        className="flex gap-1 rounded-md bg-surface-2 p-1"
      >
        {TABS.map(({ type, label }) => (
          <button
            key={type}
            type="button"
            role="tab"
            aria-selected={tab === type}
            onClick={() => setTab(type)}
            className={classNames(
              'flex-1 cursor-pointer rounded-sm px-3 py-1.5 text-[13px] font-semibold transition-colors',
              tab === type ? 'bg-surface-3 text-text-1' : 'text-text-3 hover:text-text-1',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-3">
        {tab === 'URL' && <UrlForm onDone={onDone} />}
        {tab === 'IMAGE' && <ImageForm onDone={onDone} />}
        {tab === 'MEMO' && <MemoForm onDone={onDone} />}
      </div>
    </section>
  );
};

export default AddModal;
