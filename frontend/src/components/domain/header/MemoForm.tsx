import { useState } from 'react';
import { saveMemo } from '@/services/items';
import { useCreateItem } from '@/hooks/useCreateItem';
import SubmitButton from '@/components/ui/SubmitButton';
import TextArea from '@/components/ui/TextArea';

interface MemoFormProps {
  /** 저장이 끝나면 팝오버를 닫는다 */
  onDone: () => void;
}

/**
 * 메모 저장 — { type: 'MEMO', content } 로 나간다.
 * 요청 필드가 content 뿐이라 제목 입력은 두지 않는다.
 */
const MemoForm = ({ onDone }: MemoFormProps) => {
  const [body, setBody] = useState('');
  const { save, isPending, errorMessage } = useCreateItem(saveMemo, onDone);

  const content = body.trim();

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        save(content);
      }}
    >
      <TextArea
        rows={5}
        placeholder="내용을 적어보세요"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        autoFocus
        required
      />
      {errorMessage && <p className="text-sm text-red-500">{errorMessage}</p>}
      <SubmitButton pending={isPending} disabled={!content} pendingLabel="저장 중...">
        저장
      </SubmitButton>
    </form>
  );
};

export default MemoForm;
