import type { InputHTMLAttributes } from 'react';
import { classNames } from '@/utils/classNames';
import { fieldClass } from './fieldStyles';

/** 한 줄 입력 — 여러 줄이 필요하면 TextArea 를 쓴다 */
const TextInput = ({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) => (
  <input className={classNames(fieldClass, className)} {...rest} />
);

export default TextInput;
