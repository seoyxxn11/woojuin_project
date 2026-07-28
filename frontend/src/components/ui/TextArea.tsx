import type { TextareaHTMLAttributes } from 'react';
import { classNames } from '@/utils/classNames';
import { fieldClass } from './fieldStyles';

/**
 * 여러 줄 입력 — TextInput 과 같은 외형을 쓴다.
 * 좁은 팝오버 안에서 폭이 깨지지 않게 크기 조절 손잡이는 기본으로 끈다.
 */
const TextArea = ({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) => (
  <textarea className={classNames(fieldClass, 'resize-none', className)} {...rest} />
);

export default TextArea;
