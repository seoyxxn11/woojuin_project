import { useState } from 'react';
import { saveUrl } from '@/services/items';
import { useCreateItem } from '@/hooks/useCreateItem';
import SubmitButton from '@/components/ui/SubmitButton';
import TextInput from '@/components/ui/TextInput';

interface UrlFormProps {
  /** 저장이 끝나면 팝오버를 닫는다 */
  onDone: () => void;
}

/** 링크 저장 — { type: 'URL', url } 로 나간다 */
const UrlForm = ({ onDone }: UrlFormProps) => {
  const [url, setUrl] = useState('');
  const { save, isPending, errorMessage } = useCreateItem(saveUrl, onDone);

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        save(url.trim());
      }}
    >
      <TextInput
        type="url"
        placeholder="https://"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        autoFocus
        required
      />
      {errorMessage && <p className="text-sm text-red-500">{errorMessage}</p>}
      <SubmitButton pending={isPending} pendingLabel="저장 중...">
        저장
      </SubmitButton>
    </form>
  );
};

export default UrlForm;
