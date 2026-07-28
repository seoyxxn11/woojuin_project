import { createStore } from 'jotai';

// axios 인터셉터처럼 React 트리 밖(컴포넌트가 아닌 모듈)에서도 토큰 atom을
// 읽고 쓸 수 있도록 Jotai 스토어를 직접 만들어 main.tsx의 <Provider>와 공유한다.
export const jotaiStore = createStore();
