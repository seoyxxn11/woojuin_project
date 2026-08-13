import { z } from 'zod';

export const NICKNAME_GUIDE = '닉네임은 한글, 영문, 숫자로 2~20자 입력해 주세요.';

export const nicknameSchema = z
  .string()
  .trim()
  .min(2, NICKNAME_GUIDE)
  .max(20, NICKNAME_GUIDE)
  .regex(/^[가-힣A-Za-z0-9]+$/, NICKNAME_GUIDE);

/**
 * 로그인/회원가입 폼 검증 스키마.
 *
 * 백엔드 SignupRequest/LoginRequest의 Bean Validation 규칙과 맞춘다
 * (email @NotBlank @Email, password @NotBlank @Size(min=8), nickname @NotBlank @Size(max=50)).
 * 규칙이 바뀌면 백엔드 DTO와 이 파일을 같이 확인할 것.
 */
export const signupSchema = z.object({
  email: z.string().trim().min(1, '이메일은 필수입니다').email('이메일 형식이 올바르지 않습니다'),
  password: z.string().min(1, '비밀번호는 필수입니다').min(8, '비밀번호는 8자 이상이어야 합니다'),
  nickname: nicknameSchema,
});

export const loginSchema = z.object({
  email: z.string().trim().min(1, '이메일은 필수입니다').email('이메일 형식이 올바르지 않습니다'),
  password: z.string().min(1, '비밀번호는 필수입니다'),
});

export type SignupFormValues = z.infer<typeof signupSchema>;
export type LoginFormValues = z.infer<typeof loginSchema>;
