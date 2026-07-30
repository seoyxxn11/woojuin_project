# 카테고리 분류 테스트 보고서

## 실행 정보

- 모델: qwen-local
- 데이터셋: tester:url
- 전체 데이터: 41건
- 카테고리 설명: 포함
- 선택 정책: score 0.65 이상, 최대 2개
- 실행 일시: 2026-07-28T10:45:35.004163+09:00 ~ 2026-07-28T10:48:42.310695+09:00

## 정확도 요약

| 구분 | 데이터 수 | 정답 포함 수 | Top-1 | 정확 일치 | 완화 정확도 | 평균 선택 수 | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|---|---|---|---|---|
| 전체 | 41 | 33 | 78.0% | 73.2% | 80.5% | 1.073 | 88.5% | 80.3% | 79.1% |
| memo | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| url | 41 | 33 | 78.0% | 73.2% | 80.5% | 1.073 | 88.5% | 80.3% | 79.1% |
| image | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## 전체 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 4 | 75.0% | 75.0% | 75.0% |
| 학습·지식 | 3 | 27.3% | 100.0% | 42.9% |
| 취업·커리어 | 4 | 100.0% | 50.0% | 66.7% |
| 여행·장소 | 4 | 100.0% | 100.0% | 100.0% |
| 음식·맛집 | 5 | 71.4% | 100.0% | 83.3% |
| 쇼핑·제품 | 2 | 100.0% | 100.0% | 100.0% |
| 건강·운동 | 4 | 100.0% | 100.0% | 100.0% |
| 문화·콘텐츠 | 4 | 100.0% | 100.0% | 100.0% |
| 돈·재테크 | 4 | 100.0% | 75.0% | 85.7% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 기타 | 4 | 100.0% | 50.0% | 66.7% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.90 | https://news.hidoc.co.kr/news/articleView.html?idxno=33488 |
| URL-003 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.90 | https://www.100ssd.co.kr/news/articleView.html?idxno=79546 |
| URL-004 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.80 | https://www.hinews.co.kr/news/articleView.html?idxno=27771 |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 / 생활·할 일 | O | 건강·운동 0.90 / 생활·할 일 0.70 | https://jhhaus.com/entry/수면-질-높이는-방법-오늘부터-실천하는-숙면-습관-6가지 |
| URL-006 | 기타 | 기타 | 기타 | O | 기타 0.50 | https://www.weather.go.kr/w/community/news.do |
| URL-008 | 기타 | 기타 | 기타 | O | 기타 0.50 | https://fortune.nate.com/contents/freeunse/freeunseframe.nate?freeUnseId=today04 |
| URL-009 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 1.00 | https://www.16personalities.com/ko/무료-성격-유형-검사 |
| URL-010 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://testmoa.com/ |
| URL-011 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.90 | https://www.wegive.co.kr/wezine/detail/1399 |
| URL-012 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://finvoramoney.com/etf-investment-guide/ |
| URL-013 | 돈·재테크 | 학습·지식 | 학습·지식 / 돈·재테크 | O | 학습·지식 0.90 / 돈·재테크 0.70 | https://macroinsightlab.com/주식-초보자-시작-방법/ |
| URL-014 | 돈·재테크 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 기타 0.20 | https://brunch.co.kr/@kimsun4015/32 |
| URL-016 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://about.netflix.com/ko/news/next-on-netflix-korea-2026 |
| URL-017 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.80 | https://tickets.interpark.com/contents/genre/concert |
| URL-019 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.90 | https://design.co.kr/article/144657/ |
| URL-020 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://culture.seoul.go.kr/culture/bbs/B0000001/view.do?nttId=15480&menuNo=200051&pageIndex=1 |
| URL-021 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.homehappyhelper.com/2026/03/cleaning-routine-for-people-living-alone.html |
| URL-023 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.90 | https://brunch.co.kr/@euni8828/75 |
| URL-024 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.90 / 음식·맛집 0.60 | https://steemit.com/kr/@realsunny/6xndqr |
| URL-025 | 생활·할 일 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.80 | https://m.10000recipe.com/recipe/ingredients.html |
| URL-028 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://m.gmarket.co.kr/n/list?category=300010404 |
| URL-029 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/search?q=텐트 |
| URL-031 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 0.80 | https://www.elancer.co.kr/blog/detail/103 |
| URL-034 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 취업·커리어 0.60 | https://brunch.co.kr/@radiantmoon33/80 |
| URL-035 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 취업·커리어 0.60 | https://bizviking.com/스마트스토어-부업-현실-다들-포기하는-이유/ |
| URL-036 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://www.kkday.com/ko/blog/40239/asia-korea-jeju-travel |
| URL-037 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://www.visitbusan.net/index.do?menuCd=DOM_000000202002001000&uc_seq=1211&lang_cd=ko |
| URL-038 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://triple.guide/articles/cfc384b6-011c-454a-b466-8f9ed00f1f75 |
| URL-040 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.90 / 음식·맛집 0.80 | https://tripsoda.com/article/1288 |
| URL-041 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=홍대입구역+파스타 |
| URL-042 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://tour.jeonju.go.kr/board/view.jeonju?boardId=BBS_0000038&menuCd=DOM_000000112010000000&dataSid=14264 |
| URL-043 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://guide.michelin.com/kr/ko/busan-region/busan_1025838/restaurant/hapcheon-gukbapjip |
| URL-044 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남+삼겡살 |
| URL-045 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남역+룸+삼겡살 |
| URL-046 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 1.00 | https://www.jobkorea.co.kr/goodjob/tip/view?News_No=18441 |
| URL-047 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 0.90 | https://nowgnas.github.io/posts/lotte/ |
| URL-049 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 1.00 | https://velog.io/@iameunyu/코딩테스트-후기 |
| URL-050 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://velog.io/@soonyoung/회사별-코딩테스트-스타일-및-후기 |
| URL-052 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@joy37/자료구조-CS-지식-정리 |
| URL-053 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@kkyes1210/면접-정리-신입-개발자-CS-지식-정리-운영체제 |
| URL-054 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@min9288/백엔드-기술-면접-질문디자인패턴 |

## memo 결과

- 테스트 데이터 없음

## url 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 4 | 75.0% | 75.0% | 75.0% |
| 학습·지식 | 3 | 27.3% | 100.0% | 42.9% |
| 취업·커리어 | 4 | 100.0% | 50.0% | 66.7% |
| 여행·장소 | 4 | 100.0% | 100.0% | 100.0% |
| 음식·맛집 | 5 | 71.4% | 100.0% | 83.3% |
| 쇼핑·제품 | 2 | 100.0% | 100.0% | 100.0% |
| 건강·운동 | 4 | 100.0% | 100.0% | 100.0% |
| 문화·콘텐츠 | 4 | 100.0% | 100.0% | 100.0% |
| 돈·재테크 | 4 | 100.0% | 75.0% | 85.7% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 기타 | 4 | 100.0% | 50.0% | 66.7% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.90 | https://news.hidoc.co.kr/news/articleView.html?idxno=33488 |
| URL-003 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.90 | https://www.100ssd.co.kr/news/articleView.html?idxno=79546 |
| URL-004 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.80 | https://www.hinews.co.kr/news/articleView.html?idxno=27771 |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 / 생활·할 일 | O | 건강·운동 0.90 / 생활·할 일 0.70 | https://jhhaus.com/entry/수면-질-높이는-방법-오늘부터-실천하는-숙면-습관-6가지 |
| URL-006 | 기타 | 기타 | 기타 | O | 기타 0.50 | https://www.weather.go.kr/w/community/news.do |
| URL-008 | 기타 | 기타 | 기타 | O | 기타 0.50 | https://fortune.nate.com/contents/freeunse/freeunseframe.nate?freeUnseId=today04 |
| URL-009 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 1.00 | https://www.16personalities.com/ko/무료-성격-유형-검사 |
| URL-010 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://testmoa.com/ |
| URL-011 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.90 | https://www.wegive.co.kr/wezine/detail/1399 |
| URL-012 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://finvoramoney.com/etf-investment-guide/ |
| URL-013 | 돈·재테크 | 학습·지식 | 학습·지식 / 돈·재테크 | O | 학습·지식 0.90 / 돈·재테크 0.70 | https://macroinsightlab.com/주식-초보자-시작-방법/ |
| URL-014 | 돈·재테크 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 기타 0.20 | https://brunch.co.kr/@kimsun4015/32 |
| URL-016 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://about.netflix.com/ko/news/next-on-netflix-korea-2026 |
| URL-017 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.80 | https://tickets.interpark.com/contents/genre/concert |
| URL-019 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.90 | https://design.co.kr/article/144657/ |
| URL-020 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://culture.seoul.go.kr/culture/bbs/B0000001/view.do?nttId=15480&menuNo=200051&pageIndex=1 |
| URL-021 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.homehappyhelper.com/2026/03/cleaning-routine-for-people-living-alone.html |
| URL-023 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.90 | https://brunch.co.kr/@euni8828/75 |
| URL-024 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.90 / 음식·맛집 0.60 | https://steemit.com/kr/@realsunny/6xndqr |
| URL-025 | 생활·할 일 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.80 | https://m.10000recipe.com/recipe/ingredients.html |
| URL-028 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://m.gmarket.co.kr/n/list?category=300010404 |
| URL-029 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/search?q=텐트 |
| URL-031 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 0.80 | https://www.elancer.co.kr/blog/detail/103 |
| URL-034 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 취업·커리어 0.60 | https://brunch.co.kr/@radiantmoon33/80 |
| URL-035 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 취업·커리어 0.60 | https://bizviking.com/스마트스토어-부업-현실-다들-포기하는-이유/ |
| URL-036 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://www.kkday.com/ko/blog/40239/asia-korea-jeju-travel |
| URL-037 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://www.visitbusan.net/index.do?menuCd=DOM_000000202002001000&uc_seq=1211&lang_cd=ko |
| URL-038 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://triple.guide/articles/cfc384b6-011c-454a-b466-8f9ed00f1f75 |
| URL-040 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.90 / 음식·맛집 0.80 | https://tripsoda.com/article/1288 |
| URL-041 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=홍대입구역+파스타 |
| URL-042 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://tour.jeonju.go.kr/board/view.jeonju?boardId=BBS_0000038&menuCd=DOM_000000112010000000&dataSid=14264 |
| URL-043 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://guide.michelin.com/kr/ko/busan-region/busan_1025838/restaurant/hapcheon-gukbapjip |
| URL-044 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남+삼겡살 |
| URL-045 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남역+룸+삼겡살 |
| URL-046 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 1.00 | https://www.jobkorea.co.kr/goodjob/tip/view?News_No=18441 |
| URL-047 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 0.90 | https://nowgnas.github.io/posts/lotte/ |
| URL-049 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 1.00 | https://velog.io/@iameunyu/코딩테스트-후기 |
| URL-050 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://velog.io/@soonyoung/회사별-코딩테스트-스타일-및-후기 |
| URL-052 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@joy37/자료구조-CS-지식-정리 |
| URL-053 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@kkyes1210/면접-정리-신입-개발자-CS-지식-정리-운영체제 |
| URL-054 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@min9288/백엔드-기술-면접-질문디자인패턴 |

## image 결과

- 테스트 데이터 없음

## 카테고리 설명

| ID | 카테고리 | 설명 | 예시 |
|---|---|---|---|
| LIFE_TASK | 생활·할 일 | 개인 일정, 준비물, 청소, 정리, 행정 처리와 실행해야 할 체크리스트 등 일상 행동 중심의 내용 | 주말 방 정리 계획, 기숙사 준비물, 전입 신고 서류 챙기기 |
| LEARNING_KNOWLEDGE | 학습·지식 | 시험 공부, 강의, 개념 정리, 기술 구현, 개발·IT 참고 자료 등 배우거나 다시 확인할 지식 중심의 내용 | SQLD 시험 공부 계획, JWT 재발급 구조 정리, Docker 실행 방법 |
| CAREER | 취업·커리어 | 채용 공고, 자기소개서, 면접, 이력서, 직무 선택과 경력 개발에 관한 내용 | 공기업 채용 공고 확인, 백엔드 면접 준비, 자기소개서 수정 |
| TRAVEL_PLACE | 여행·장소 | 여행 일정, 방문할 장소, 교통, 숙소와 지역 탐방에 관한 내용 | 제주 여행 일정, 서울 전시회 방문 후보, 부산 숙소와 교통 계획 |
| FOOD_RESTAURANT | 음식·맛집 | 요리법, 식재료, 식당, 메뉴, 맛집 방문과 식사 계획에 관한 내용 | 닭가슴살 볶음밥 레시피, 성수동 식당 후보, 김치찌개 조리 순서 |
| SHOPPING_PRODUCT | 쇼핑·제품 | 상품 구매 후보, 제품 비교, 가격과 기능 검토, 구매 의사결정 중심의 내용 | 무선 키보드 구매 후보, 이어폰 배터리 성능 비교, 노트북 가격 확인 |
| HEALTH_EXERCISE | 건강·운동 | 운동 계획, 신체 활동, 건강 관리, 수면, 식단과 생활 습관 개선에 관한 내용 | 주 3회 근력 운동 계획, 건강검진 일정, 수면 시간 개선 기록 |
| CULTURE_CONTENT | 문화·콘텐츠 | 책, 영화, 드라마, 웹툰, 공연, 전시 등 음악을 제외하고 감상하거나 소비하는 문화 콘텐츠 중심의 내용 | 읽어볼 개발 에세이, 주말에 본 다큐멘터리 감상, 서울 전시회 후보 |
| MONEY_FINANCE | 돈·재테크 | 예산, 저축, 투자, 보험, 세금, 대출과 자산 관리 등 개인 금융 중심의 내용 | 월간 예산 정리, 적금 금리 비교, ETF 투자 기록 |
| IDEA_INSPIRATION | 아이디어·영감 | 새로운 서비스나 기능 발상, 창작 아이디어, 브레인스토밍, 개선 방향과 영감을 기록한 내용 | 앱 기능 아이디어, 콘텐츠 기획 메모, URL 처리 구조 개선 방향 |
| OTHER | 기타 | 다른 카테고리로 명확히 분류하기 어렵거나 맥락이 부족한 단편적인 내용 | 나중에 다시 확인할 메모, 출처가 불분명한 짧은 기록 |
