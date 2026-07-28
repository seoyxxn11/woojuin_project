import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import SubmitButton from '@/components/ui/SubmitButton';

const btnOf = (c: HTMLElement) => c.querySelector('button')!;

describe('SubmitButton', () => {
  it('기본은 type=submit 이다', async () => {
    // 폼 안에서 엔터·클릭으로 제출되려면 submit 이어야 한다
    const { container } = await render(<SubmitButton>저장</SubmitButton>);
    expect(btnOf(container)).toHaveAttribute('type', 'submit');
  });

  describe('pending — 요청 중', () => {
    it('pending 이면 스스로 잠긴다', async () => {
      // 호출부가 disabled 에 isPending 을 또 넣지 않아도 중복 제출이 막혀야 한다
      const { container } = await render(<SubmitButton pending>저장</SubmitButton>);
      expect(btnOf(container).disabled).toBe(true);
    });

    it('pending 이면 pendingLabel 을 보여준다', async () => {
      const { container } = await render(
        <SubmitButton pending pendingLabel="저장 중...">
          저장
        </SubmitButton>,
      );
      expect(btnOf(container).textContent).toBe('저장 중...');
    });

    it('pendingLabel 이 없으면 라벨을 그대로 둔다', async () => {
      const { container } = await render(<SubmitButton pending>저장</SubmitButton>);
      expect(btnOf(container).textContent).toBe('저장');
    });

    it('pending 이 아니면 children 을 보여준다', async () => {
      const { container } = await render(
        <SubmitButton pendingLabel="저장 중...">저장</SubmitButton>,
      );
      expect(btnOf(container).textContent).toBe('저장');
    });
  });

  describe('disabled — 입력이 아직 유효하지 않을 때', () => {
    it('disabled 만으로도 잠긴다', async () => {
      const { container } = await render(<SubmitButton disabled>저장</SubmitButton>);
      expect(btnOf(container).disabled).toBe(true);
    });

    it('둘 다 아니면 눌린다', async () => {
      const { container } = await render(<SubmitButton>저장</SubmitButton>);
      expect(btnOf(container).disabled).toBe(false);
    });
  });

  it('나머지 속성은 그대로 통과시킨다', async () => {
    const { container } = await render(<SubmitButton title="설명">저장</SubmitButton>);
    expect(btnOf(container)).toHaveAttribute('title', '설명');
  });
});
