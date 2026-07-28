import { useEffect, useState } from 'react';
import { classNames } from '@/utils/classNames';
import { saveImage } from '@/services/items';
import { useCreateItem } from '@/hooks/useCreateItem';
import SubmitButton from '@/components/ui/SubmitButton';

interface ImageFormProps {
  /** 저장이 끝나면 팝오버를 닫는다 */
  onDone: () => void;
}

/** 사진 저장 — 셋 중 유일하게 multipart/form-data 로 나간다 */
const ImageForm = ({ onDone }: ImageFormProps) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const { save, isPending, errorMessage } = useCreateItem(saveImage, onDone);

  /* 미리보기 URL 은 파일이 바뀔 때마다 새로 만들고 반드시 되돌린다 (누수 방지) */
  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setPreview(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (file) save(file);
      }}
    >
      <label
        className={classNames(
          'flex cursor-pointer flex-col items-center justify-center gap-1 rounded-md',
          'border border-dashed border-border bg-surface-2 px-3 py-6 text-center',
          'hover:border-accent',
        )}
      >
        <input
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        {preview ? (
          <img
            src={preview}
            alt={file?.name ?? '선택한 사진'}
            className="max-h-28 rounded-sm object-contain"
          />
        ) : (
          <>
            <span className="text-sm font-semibold text-text-2">사진 선택</span>
            <span className="text-xs text-text-3">클릭해서 파일 고르기</span>
          </>
        )}
      </label>

      {file && <p className="truncate text-xs text-text-3">{file.name}</p>}
      {errorMessage && <p className="text-sm text-red-500">{errorMessage}</p>}

      <SubmitButton pending={isPending} disabled={!file} pendingLabel="저장 중...">
        저장
      </SubmitButton>
    </form>
  );
};

export default ImageForm;
