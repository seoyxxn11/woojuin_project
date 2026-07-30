# 카테고리 분류 테스트 보고서

## 실행 정보

- 모델: qwen-local
- 데이터셋: test:memo+url
- 전체 데이터: 49건
- 카테고리 설명: 포함
- 실행 일시: 2026-07-25T19:35:04.879282+09:00 ~ 2026-07-25T19:39:27.980879+09:00

## 정확도 요약

| 구분 | 데이터 수 | 정답 수 | 정확도 | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|---|---|
| 전체 | 49 | 24 | 49.0% | 59.5% | 51.9% | 51.7% |
| memo | 6 | 4 | 66.7% | 75.0% | 83.3% | 88.9% |
| url | 43 | 20 | 46.5% | 59.5% | 46.9% | 48.6% |
| image | 0 | 0 | N/A | N/A | N/A | N/A |

## 전체 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 건강·운동 | 5 | N/A | 0.0% | N/A |
| 기타 | 4 | 0.0% | 0.0% | 0.0% |
| 돈·재테크 | 3 | 100.0% | 66.7% | 80.0% |
| 문화·콘텐츠 | 4 | 20.0% | 25.0% | 22.2% |
| 생활·할 일 | 2 | 20.0% | 50.0% | 28.6% |
| 쇼핑·제품 | 5 | 31.2% | 100.0% | 47.6% |
| 아이디어·영감 | 7 | 100.0% | 42.9% | 60.0% |
| 여행·장소 | 3 | 100.0% | 66.7% | 80.0% |
| 음식·맛집 | 6 | 50.0% | 50.0% | 50.0% |
| 음악 | 1 | 33.3% | 100.0% | 50.0% |
| 취업·커리어 | 2 | 100.0% | 50.0% | 66.7% |
| 학습·지식 | 7 | 100.0% | 71.4% | 83.3% |

### 개별 테스트 결과

| ID | 정답 | 예측 | 정답 여부 | 신뢰도 | 제목 |
|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 생활·할 일 | X | 0.900 | https://www.instagram.com/reel/Da443z7pFQr/?igsh=anJpbTZoZGFuNnA1 |
| URL-002 | 건강·운동 | 쇼핑·제품 | X | 0.950 | https://www.instagram.com/reel/DaePl8rSnJ0/?igsh=ZmI0ZGM4bnhqdnd1 |
| URL-003 | 건강·운동 | 생활·할 일 | X | 0.950 | https://www.instagram.com/reel/Dam0TYJKhg7/?igsh=Y2YzMzRjdjV4dzRp |
| URL-004 | 건강·운동 | 음식·맛집 | X | 0.950 | https://www.instagram.com/reel/Dar1_KmBwHk/?igsh=cTk1OHlodjQ3c2k2 |
| URL-005 | 건강·운동 | 생활·할 일 | X | 0.950 | https://www.instagram.com/reel/DZTqt4Uhx4s/?igsh=d3AzZXVobWQ5NnRu |
| URL-006 | 기타 | 쇼핑·제품 | X | 0.500 | https://news.kbs.co.kr/news/pc/main/main.html |
| URL-007 | 기타 | 쇼핑·제품 | X | 0.500 | https://news.kbs.co.kr/news/pc/view |
| URL-008 | 기타 | 쇼핑·제품 | X | 0.900 | https://www.jeonmae.co.kr/news/articleView.html?idxno=1277183 |
| URL-009 | 기타 | 문화·콘텐츠 | X | 0.900 | https://youtu.be/ADXVtUTgdA4?si=nw60Fg7dymSCu1C2 |
| URL-010 | 돈·재테크 | 돈·재테크 | O | 0.950 | https://n.news.naver.com/mnews/article/001/0016212899?sid=101 |
| URL-011 | 돈·재테크 | 생활·할 일 | X | 0.950 | https://www.instagram.com/p/Dav8FMmk5iy/?igsh=czk4aWY4cmdqZjBs |
| URL-012 | 돈·재테크 | 돈·재테크 | O | 1.000 | https://youtu.be/1AFnKX2-rt0?si=ySbLjlVATwHcyGBp |
| URL-013 | 문화·콘텐츠 | 쇼핑·제품 | X | 0.800 | https://blog.naver.com/qhrfks1004/224349386864 |
| URL-014 | 문화·콘텐츠 | 기타 | X | 1.000 | https://gall.dcinside.com/board/view/?id=dcbest&no=448144 |
| URL-015 | 문화·콘텐츠 | 문화·콘텐츠 | O | 0.950 | https://www.instagram.com/p/DONUNIgE4GR/?igsh=aDk1MHo4dTUxNnUw |
| URL-016 | 문화·콘텐츠 | 음악 | X | 0.900 | https://www.youtube.com/shorts/XlDmdpT0_HY |
| MEMO-001 | 생활·할 일 | 생활·할 일 | O | 1.000 | 기숙사 준비물 |
| URL-017 | 생활·할 일 | 문화·콘텐츠 | X | 0.900 | https://youtu.be/0sTWDcz1xaE?si=GNJkXaz9Xr6WA_c4 |
| MEMO-002 | 쇼핑·제품 | 쇼핑·제품 | O | 1.000 | 장보기 목록 - 쇼핑·제품 |
| URL-018 | 쇼핑·제품 | 쇼핑·제품 | O | 0.800 | https://blog.naver.com/onedayfoodmall/224342678366 |
| URL-019 | 쇼핑·제품 | 쇼핑·제품 | O | 0.900 | https://smartstore.naver.com/e-sandl/products/273918551 |
| URL-020 | 쇼핑·제품 | 쇼핑·제품 | O | 0.900 | https://www.coupang.com/vp/products/9457512460 |
| URL-021 | 쇼핑·제품 | 쇼핑·제품 | O | 0.950 | https://www.instagram.com/p/DXdzEGBGnhg/?igsh=MTRhdjhwZzF5cHc4aQ== |
| MEMO-003 | 아이디어·영감 | 아이디어·영감 | O | 0.950 | 동준이의 염감 노트 - 아이디어·영감 |
| MEMO-004 | 아이디어·영감 | 아이디어·영감 | O | 0.950 | 동준이의 영감 노트 - 아이디어·영감 |
| MEMO-005 | 아이디어·영감 | 음식·맛집 | X | 1.000 | 레시피 - 음식·맛집 |
| MEMO-006 | 아이디어·영감 | 음식·맛집 | X | 0.900 | 텍스트 노트 0817 - 음식·맛집 |
| URL-022 | 아이디어·영감 | 쇼핑·제품 | X | 0.800 | https://cafe.naver.com/canon450dclub/649041 |
| URL-023 | 아이디어·영감 | 쇼핑·제품 | X | 0.800 | https://kr.pinterest.com/pin/9288742977535425/ |
| URL-024 | 아이디어·영감 | 아이디어·영감 | O | 1.000 | https://youtu.be/pokSYhJ2w4Y?si=hygz_EWccmLDj8iE |
| URL-025 | 여행·장소 | 문화·콘텐츠 | X | 0.800 | https://blog.naver.com/bjstour/224344268733 |
| URL-026 | 여행·장소 | 여행·장소 | O | 0.950 | https://www.instagram.com/p/DWpyY9Xjy3D/?igsh=MXgzcm56M2QxZHQybQ== |
| URL-027 | 여행·장소 | 여행·장소 | O | 0.900 | https://youtu.be/Axghk4p6Qq8?si=t5Kzxk4qG-em98k6 |
| URL-028 | 음식·맛집 | 음식·맛집 | O | 0.900 | https://blog.naver.com/sinjum77/224347923705 |
| URL-029 | 음식·맛집 | 쇼핑·제품 | X | 0.800 | https://even-1today.tistory.com/581 |
| URL-030 | 음식·맛집 | 음식·맛집 | O | 0.980 | https://little-cat.tistory.com/entry/수완맛집-베스트-10-순위-추천 |
| URL-031 | 음식·맛집 | 음식·맛집 | O | 1.000 | https://little-cat.tistory.com/entry/수완지구-카페-추천-베스트-10-순위 |
| URL-032 | 음식·맛집 | 쇼핑·제품 | X | 0.800 | https://m.blog.naver.com/ssbarato/222803352685 |
| URL-033 | 음식·맛집 | 문화·콘텐츠 | X | 0.900 | https://youtu.be/lOPvMP1H27Y?si=mXV0-dLS9Y70j1iB |
| URL-034 | 음악 | 음악 | O | 1.000 | https://music.apple.com/us/album/been-by-now/6792676858?i=6792676860 |
| URL-035 | 취업·커리어 | 쇼핑·제품 | X | 0.800 | https://blog.naver.com/rlawkdrn85/224270747417 |
| URL-036 | 취업·커리어 | 취업·커리어 | O | 0.950 | https://www.instagram.com/p/DXUC_5uicRF/?igsh=cGt3NXg4aGkwYno3 |
| URL-037 | 학습·지식 | 쇼핑·제품 | X | 0.500 | https://dev.tistory.com/368 |
| URL-038 | 학습·지식 | 학습·지식 | O | 0.950 | https://news.hada.io/topic?id=29408 |
| URL-039 | 학습·지식 | 학습·지식 | O | 0.950 | https://velog.io/@hye0n/Redis-공식문서-톺아보기-1.-Redis-개요 |
| URL-040 | 학습·지식 | 학습·지식 | O | 0.950 | https://velog.io/@yonghun16/레디스-스트림-Redis-Streams-이란 |
| URL-041 | 학습·지식 | 학습·지식 | O | 0.900 | https://www.instagram.com/reel/DUfrGalkVqz/ |
| URL-042 | 학습·지식 | 학습·지식 | O | 0.900 | https://www.youtube.com/watch?v=i0NcKL1JLfg |
| URL-043 | 학습·지식 | 음악 | X | 0.950 | https://www.youtube.com/watch?v=OKjcchoQVRo |

## memo 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 건강·운동 | 0 | N/A | N/A | N/A |
| 기타 | 0 | N/A | N/A | N/A |
| 돈·재테크 | 0 | N/A | N/A | N/A |
| 문화·콘텐츠 | 0 | N/A | N/A | N/A |
| 생활·할 일 | 1 | 100.0% | 100.0% | 100.0% |
| 쇼핑·제품 | 1 | 100.0% | 100.0% | 100.0% |
| 아이디어·영감 | 4 | 100.0% | 50.0% | 66.7% |
| 여행·장소 | 0 | N/A | N/A | N/A |
| 음식·맛집 | 0 | 0.0% | N/A | N/A |
| 음악 | 0 | N/A | N/A | N/A |
| 취업·커리어 | 0 | N/A | N/A | N/A |
| 학습·지식 | 0 | N/A | N/A | N/A |

### 개별 테스트 결과

| ID | 정답 | 예측 | 정답 여부 | 신뢰도 | 제목 |
|---|---|---|---|---|---|
| MEMO-001 | 생활·할 일 | 생활·할 일 | O | 1.000 | 기숙사 준비물 |
| MEMO-002 | 쇼핑·제품 | 쇼핑·제품 | O | 1.000 | 장보기 목록 - 쇼핑·제품 |
| MEMO-003 | 아이디어·영감 | 아이디어·영감 | O | 0.950 | 동준이의 염감 노트 - 아이디어·영감 |
| MEMO-004 | 아이디어·영감 | 아이디어·영감 | O | 0.950 | 동준이의 영감 노트 - 아이디어·영감 |
| MEMO-005 | 아이디어·영감 | 음식·맛집 | X | 1.000 | 레시피 - 음식·맛집 |
| MEMO-006 | 아이디어·영감 | 음식·맛집 | X | 0.900 | 텍스트 노트 0817 - 음식·맛집 |

## url 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 건강·운동 | 5 | N/A | 0.0% | N/A |
| 기타 | 4 | 0.0% | 0.0% | 0.0% |
| 돈·재테크 | 3 | 100.0% | 66.7% | 80.0% |
| 문화·콘텐츠 | 4 | 20.0% | 25.0% | 22.2% |
| 생활·할 일 | 1 | 0.0% | 0.0% | 0.0% |
| 쇼핑·제품 | 4 | 26.7% | 100.0% | 42.1% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 여행·장소 | 3 | 100.0% | 66.7% | 80.0% |
| 음식·맛집 | 6 | 75.0% | 50.0% | 60.0% |
| 음악 | 1 | 33.3% | 100.0% | 50.0% |
| 취업·커리어 | 2 | 100.0% | 50.0% | 66.7% |
| 학습·지식 | 7 | 100.0% | 71.4% | 83.3% |

### 개별 테스트 결과

| ID | 정답 | 예측 | 정답 여부 | 신뢰도 | 제목 |
|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 생활·할 일 | X | 0.900 | https://www.instagram.com/reel/Da443z7pFQr/?igsh=anJpbTZoZGFuNnA1 |
| URL-002 | 건강·운동 | 쇼핑·제품 | X | 0.950 | https://www.instagram.com/reel/DaePl8rSnJ0/?igsh=ZmI0ZGM4bnhqdnd1 |
| URL-003 | 건강·운동 | 생활·할 일 | X | 0.950 | https://www.instagram.com/reel/Dam0TYJKhg7/?igsh=Y2YzMzRjdjV4dzRp |
| URL-004 | 건강·운동 | 음식·맛집 | X | 0.950 | https://www.instagram.com/reel/Dar1_KmBwHk/?igsh=cTk1OHlodjQ3c2k2 |
| URL-005 | 건강·운동 | 생활·할 일 | X | 0.950 | https://www.instagram.com/reel/DZTqt4Uhx4s/?igsh=d3AzZXVobWQ5NnRu |
| URL-006 | 기타 | 쇼핑·제품 | X | 0.500 | https://news.kbs.co.kr/news/pc/main/main.html |
| URL-007 | 기타 | 쇼핑·제품 | X | 0.500 | https://news.kbs.co.kr/news/pc/view |
| URL-008 | 기타 | 쇼핑·제품 | X | 0.900 | https://www.jeonmae.co.kr/news/articleView.html?idxno=1277183 |
| URL-009 | 기타 | 문화·콘텐츠 | X | 0.900 | https://youtu.be/ADXVtUTgdA4?si=nw60Fg7dymSCu1C2 |
| URL-010 | 돈·재테크 | 돈·재테크 | O | 0.950 | https://n.news.naver.com/mnews/article/001/0016212899?sid=101 |
| URL-011 | 돈·재테크 | 생활·할 일 | X | 0.950 | https://www.instagram.com/p/Dav8FMmk5iy/?igsh=czk4aWY4cmdqZjBs |
| URL-012 | 돈·재테크 | 돈·재테크 | O | 1.000 | https://youtu.be/1AFnKX2-rt0?si=ySbLjlVATwHcyGBp |
| URL-013 | 문화·콘텐츠 | 쇼핑·제품 | X | 0.800 | https://blog.naver.com/qhrfks1004/224349386864 |
| URL-014 | 문화·콘텐츠 | 기타 | X | 1.000 | https://gall.dcinside.com/board/view/?id=dcbest&no=448144 |
| URL-015 | 문화·콘텐츠 | 문화·콘텐츠 | O | 0.950 | https://www.instagram.com/p/DONUNIgE4GR/?igsh=aDk1MHo4dTUxNnUw |
| URL-016 | 문화·콘텐츠 | 음악 | X | 0.900 | https://www.youtube.com/shorts/XlDmdpT0_HY |
| URL-017 | 생활·할 일 | 문화·콘텐츠 | X | 0.900 | https://youtu.be/0sTWDcz1xaE?si=GNJkXaz9Xr6WA_c4 |
| URL-018 | 쇼핑·제품 | 쇼핑·제품 | O | 0.800 | https://blog.naver.com/onedayfoodmall/224342678366 |
| URL-019 | 쇼핑·제품 | 쇼핑·제품 | O | 0.900 | https://smartstore.naver.com/e-sandl/products/273918551 |
| URL-020 | 쇼핑·제품 | 쇼핑·제품 | O | 0.900 | https://www.coupang.com/vp/products/9457512460 |
| URL-021 | 쇼핑·제품 | 쇼핑·제품 | O | 0.950 | https://www.instagram.com/p/DXdzEGBGnhg/?igsh=MTRhdjhwZzF5cHc4aQ== |
| URL-022 | 아이디어·영감 | 쇼핑·제품 | X | 0.800 | https://cafe.naver.com/canon450dclub/649041 |
| URL-023 | 아이디어·영감 | 쇼핑·제품 | X | 0.800 | https://kr.pinterest.com/pin/9288742977535425/ |
| URL-024 | 아이디어·영감 | 아이디어·영감 | O | 1.000 | https://youtu.be/pokSYhJ2w4Y?si=hygz_EWccmLDj8iE |
| URL-025 | 여행·장소 | 문화·콘텐츠 | X | 0.800 | https://blog.naver.com/bjstour/224344268733 |
| URL-026 | 여행·장소 | 여행·장소 | O | 0.950 | https://www.instagram.com/p/DWpyY9Xjy3D/?igsh=MXgzcm56M2QxZHQybQ== |
| URL-027 | 여행·장소 | 여행·장소 | O | 0.900 | https://youtu.be/Axghk4p6Qq8?si=t5Kzxk4qG-em98k6 |
| URL-028 | 음식·맛집 | 음식·맛집 | O | 0.900 | https://blog.naver.com/sinjum77/224347923705 |
| URL-029 | 음식·맛집 | 쇼핑·제품 | X | 0.800 | https://even-1today.tistory.com/581 |
| URL-030 | 음식·맛집 | 음식·맛집 | O | 0.980 | https://little-cat.tistory.com/entry/수완맛집-베스트-10-순위-추천 |
| URL-031 | 음식·맛집 | 음식·맛집 | O | 1.000 | https://little-cat.tistory.com/entry/수완지구-카페-추천-베스트-10-순위 |
| URL-032 | 음식·맛집 | 쇼핑·제품 | X | 0.800 | https://m.blog.naver.com/ssbarato/222803352685 |
| URL-033 | 음식·맛집 | 문화·콘텐츠 | X | 0.900 | https://youtu.be/lOPvMP1H27Y?si=mXV0-dLS9Y70j1iB |
| URL-034 | 음악 | 음악 | O | 1.000 | https://music.apple.com/us/album/been-by-now/6792676858?i=6792676860 |
| URL-035 | 취업·커리어 | 쇼핑·제품 | X | 0.800 | https://blog.naver.com/rlawkdrn85/224270747417 |
| URL-036 | 취업·커리어 | 취업·커리어 | O | 0.950 | https://www.instagram.com/p/DXUC_5uicRF/?igsh=cGt3NXg4aGkwYno3 |
| URL-037 | 학습·지식 | 쇼핑·제품 | X | 0.500 | https://dev.tistory.com/368 |
| URL-038 | 학습·지식 | 학습·지식 | O | 0.950 | https://news.hada.io/topic?id=29408 |
| URL-039 | 학습·지식 | 학습·지식 | O | 0.950 | https://velog.io/@hye0n/Redis-공식문서-톺아보기-1.-Redis-개요 |
| URL-040 | 학습·지식 | 학습·지식 | O | 0.950 | https://velog.io/@yonghun16/레디스-스트림-Redis-Streams-이란 |
| URL-041 | 학습·지식 | 학습·지식 | O | 0.900 | https://www.instagram.com/reel/DUfrGalkVqz/ |
| URL-042 | 학습·지식 | 학습·지식 | O | 0.900 | https://www.youtube.com/watch?v=i0NcKL1JLfg |
| URL-043 | 학습·지식 | 음악 | X | 0.950 | https://www.youtube.com/watch?v=OKjcchoQVRo |

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
| MUSIC | 음악 | 노래, 음원, 앨범, 가수, 플레이리스트와 음악 감상에 직접 관련된 내용 | Apple Music 음원, 집중할 때 듣는 플레이리스트, 가수의 새 앨범 |
| MONEY_FINANCE | 돈·재테크 | 예산, 저축, 투자, 보험, 세금, 대출과 자산 관리 등 개인 금융 중심의 내용 | 월간 예산 정리, 적금 금리 비교, ETF 투자 기록 |
| IDEA_INSPIRATION | 아이디어·영감 | 새로운 서비스나 기능 발상, 창작 아이디어, 브레인스토밍, 개선 방향과 영감을 기록한 내용 | 앱 기능 아이디어, 콘텐츠 기획 메모, URL 처리 구조 개선 방향 |
| OTHER | 기타 | 다른 카테고리로 명확히 분류하기 어렵거나 맥락이 부족한 단편적인 내용 | 나중에 다시 확인할 메모, 출처가 불분명한 짧은 기록 |
