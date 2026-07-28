// true나 false가 들어가는 것을 막는 함수
export const classNames = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(' ');
