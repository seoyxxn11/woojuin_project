# 카테고리 분류 테스트 보고서

## 실행 정보

- 모델: qwen-local
- 데이터셋: test:url
- 전체 데이터: 43건
- 카테고리 설명: 포함
- 선택 정책: score 0.65 이상, 최대 2개
- 실행 일시: 2026-07-25T22:58:29.155031+09:00 ~ 2026-07-25T23:05:47.665590+09:00

## 정확도 요약

| 구분 | 데이터 수 | 정답 포함 수 | Top-1 | 정확 일치 | 완화 정확도 | 평균 선택 수 | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|---|---|---|---|---|
| 전체 | 43 | 30 | 65.1% | 51.2% | 69.8% | 1.233 | 62.8% | 72.6% | 62.1% |
| memo | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| url | 43 | 30 | 65.1% | 51.2% | 69.8% | 1.233 | 62.8% | 72.6% | 62.1% |
| image | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## 전체 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 1 | 25.0% | 100.0% | 40.0% |
| 학습·지식 | 7 | 62.5% | 71.4% | 66.7% |
| 취업·커리어 | 2 | 25.0% | 50.0% | 33.3% |
| 여행·장소 | 3 | 75.0% | 100.0% | 85.7% |
| 음식·맛집 | 6 | 60.0% | 50.0% | 54.5% |
| 쇼핑·제품 | 4 | 66.7% | 100.0% | 80.0% |
| 건강·운동 | 5 | 100.0% | 100.0% | 100.0% |
| 문화·콘텐츠 | 4 | 66.7% | 50.0% | 57.1% |
| 음악 | 1 | 50.0% | 100.0% | 66.7% |
| 돈·재테크 | 3 | 100.0% | 66.7% | 80.0% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 기타 | 4 | 22.2% | 50.0% | 30.8% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.95 / 학습·지식 0.85 | https://www.instagram.com/reel/Da443z7pFQr/?igsh=anJpbTZoZGFuNnA1 |
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.95 / 학습·지식 0.75 | https://www.instagram.com/reel/DaePl8rSnJ0/?igsh=ZmI0ZGM4bnhqdnd1 |
| URL-003 | 건강·운동 | 건강·운동 | 건강·운동 / 생활·할 일 | O | 건강·운동 1.00 / 생활·할 일 0.70 | https://www.instagram.com/reel/Dam0TYJKhg7/?igsh=Y2YzMzRjdjV4dzRp |
| URL-004 | 건강·운동 | 음식·맛집 | 음식·맛집 / 건강·운동 | O | 음식·맛집 0.98 / 건강·운동 0.92 / 생활·할 일 0.85 | https://www.instagram.com/reel/Dar1_KmBwHk/?igsh=cTk1OHlodjQ3c2k2 |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.instagram.com/reel/DZTqt4Uhx4s/?igsh=d3AzZXVobWQ5NnRu |
| URL-006 | 기타 | 기타 | 기타 | O | 기타 1.00 | https://news.kbs.co.kr/news/pc/main/main.html |
| URL-007 | 기타 |  | 기타 | O |  | https://news.kbs.co.kr/news/pc/view |
| URL-008 | 기타 | 쇼핑·제품 | 쇼핑·제품 | X | 쇼핑·제품 0.80 / 여행·장소 0.60 | https://www.jeonmae.co.kr/news/articleView.html?idxno=1277183 |
| URL-009 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.80 | https://youtu.be/ADXVtUTgdA4?si=nw60Fg7dymSCu1C2 |
| URL-010 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://n.news.naver.com/mnews/article/001/0016212899?sid=101 |
| URL-011 | 돈·재테크 | 취업·커리어 | 취업·커리어 / 학습·지식 | X | 취업·커리어 0.95 / 학습·지식 0.85 | https://www.instagram.com/p/Dav8FMmk5iy/?igsh=czk4aWY4cmdqZjBs |
| URL-012 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://youtu.be/1AFnKX2-rt0?si=ySbLjlVATwHcyGBp |
| URL-013 | 문화·콘텐츠 |  | 기타 | X |  | https://blog.naver.com/qhrfks1004/224349386864 |
| URL-014 | 문화·콘텐츠 |  | 기타 | X |  | https://gall.dcinside.com/board/view/?id=dcbest&no=448144 |
| URL-015 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 / 생활·할 일 | O | 문화·콘텐츠 0.98 / 생활·할 일 0.85 | https://www.instagram.com/p/DONUNIgE4GR/?igsh=aDk1MHo4dTUxNnUw |
| URL-016 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.youtube.com/shorts/XlDmdpT0_HY |
| URL-017 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://youtu.be/0sTWDcz1xaE?si=GNJkXaz9Xr6WA_c4 |
| URL-018 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://blog.naver.com/onedayfoodmall/224342678366 |
| URL-019 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://smartstore.naver.com/e-sandl/products/273918551 |
| URL-020 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/vp/products/9457512460 |
| URL-021 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 / 학습·지식 0.05 | https://www.instagram.com/p/DXdzEGBGnhg/?igsh=MTRhdjhwZzF5cHc4aQ== |
| URL-022 | 아이디어·영감 | 쇼핑·제품 | 쇼핑·제품 | X | 쇼핑·제품 0.80 / 여행·장소 0.50 | https://cafe.naver.com/canon450dclub/649041 |
| URL-023 | 아이디어·영감 | 기타 | 기타 | X | 기타 1.00 | https://kr.pinterest.com/pin/9288742977535425/ |
| URL-024 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 1.00 | https://youtu.be/pokSYhJ2w4Y?si=hygz_EWccmLDj8iE |
| URL-025 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.80 | https://blog.naver.com/bjstour/224344268733 |
| URL-026 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.95 / 음식·맛집 0.85 | https://www.instagram.com/p/DWpyY9Xjy3D/?igsh=MXgzcm56M2QxZHQybQ== |
| URL-027 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 / 학습·지식 0.05 | https://youtu.be/Axghk4p6Qq8?si=t5Kzxk4qG-em98k6 |
| URL-028 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://blog.naver.com/sinjum77/224347923705 |
| URL-029 | 음식·맛집 |  | 기타 | X |  | https://even-1today.tistory.com/581 |
| URL-030 | 음식·맛집 |  | 기타 | X |  | https://little-cat.tistory.com/entry/수완맛집-베스트-10-순위-추천 |
| URL-031 | 음식·맛집 | 여행·장소 | 여행·장소 | X | 여행·장소 1.00 / 취업·커리어 0.00 / 생활·할 일 0.00 / 쇼핑·제품 0.00 | https://little-cat.tistory.com/entry/수완지구-카페-추천-베스트-10-순위 |
| URL-032 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://m.blog.naver.com/ssbarato/222803352685 |
| URL-033 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://youtu.be/lOPvMP1H27Y?si=mXV0-dLS9Y70j1iB |
| URL-034 | 음악 | 음악 | 음악 | O | 음악 1.00 | https://music.apple.com/us/album/been-by-now/6792676858?i=6792676860 |
| URL-035 | 취업·커리어 |  | 기타 | X |  | https://blog.naver.com/rlawkdrn85/224270747417 |
| URL-036 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 1.00 | https://www.instagram.com/p/DXUC_5uicRF/?igsh=cGt3NXg4aGkwYno3 |
| URL-037 | 학습·지식 |  | 기타 | X |  | https://dev.tistory.com/368 |
| URL-038 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 / 기타 0.05 | https://news.hada.io/topic?id=29408 |
| URL-039 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 / 기타 0.05 | https://velog.io/@hye0n/Redis-공식문서-톺아보기-1.-Redis-개요 |
| URL-040 | 학습·지식 | 취업·커리어 | 취업·커리어 / 생활·할 일 | X | 취업·커리어 0.85 / 생활·할 일 0.75 / 여행·장소 0.65 / 음식·맛집 0.55 / 쇼핑·제품 0.45 / 문화·콘텐츠 0.35 / 건강·운동 0.25 / 기타 0.15 | https://velog.io/@yonghun16/레디스-스트림-Redis-Streams-이란 |
| URL-041 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://www.instagram.com/reel/DUfrGalkVqz/ |
| URL-042 | 학습·지식 | 학습·지식 | 학습·지식 / 취업·커리어 | O | 학습·지식 0.95 / 취업·커리어 0.85 | https://www.youtube.com/watch?v=i0NcKL1JLfg |
| URL-043 | 학습·지식 | 학습·지식 | 학습·지식 / 음악 | O | 학습·지식 0.80 / 음악 0.70 | https://www.youtube.com/watch?v=OKjcchoQVRo |

## memo 결과

- 테스트 데이터 없음

## url 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 1 | 25.0% | 100.0% | 40.0% |
| 학습·지식 | 7 | 62.5% | 71.4% | 66.7% |
| 취업·커리어 | 2 | 25.0% | 50.0% | 33.3% |
| 여행·장소 | 3 | 75.0% | 100.0% | 85.7% |
| 음식·맛집 | 6 | 60.0% | 50.0% | 54.5% |
| 쇼핑·제품 | 4 | 66.7% | 100.0% | 80.0% |
| 건강·운동 | 5 | 100.0% | 100.0% | 100.0% |
| 문화·콘텐츠 | 4 | 66.7% | 50.0% | 57.1% |
| 음악 | 1 | 50.0% | 100.0% | 66.7% |
| 돈·재테크 | 3 | 100.0% | 66.7% | 80.0% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 기타 | 4 | 22.2% | 50.0% | 30.8% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.95 / 학습·지식 0.85 | https://www.instagram.com/reel/Da443z7pFQr/?igsh=anJpbTZoZGFuNnA1 |
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.95 / 학습·지식 0.75 | https://www.instagram.com/reel/DaePl8rSnJ0/?igsh=ZmI0ZGM4bnhqdnd1 |
| URL-003 | 건강·운동 | 건강·운동 | 건강·운동 / 생활·할 일 | O | 건강·운동 1.00 / 생활·할 일 0.70 | https://www.instagram.com/reel/Dam0TYJKhg7/?igsh=Y2YzMzRjdjV4dzRp |
| URL-004 | 건강·운동 | 음식·맛집 | 음식·맛집 / 건강·운동 | O | 음식·맛집 0.98 / 건강·운동 0.92 / 생활·할 일 0.85 | https://www.instagram.com/reel/Dar1_KmBwHk/?igsh=cTk1OHlodjQ3c2k2 |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.instagram.com/reel/DZTqt4Uhx4s/?igsh=d3AzZXVobWQ5NnRu |
| URL-006 | 기타 | 기타 | 기타 | O | 기타 1.00 | https://news.kbs.co.kr/news/pc/main/main.html |
| URL-007 | 기타 |  | 기타 | O |  | https://news.kbs.co.kr/news/pc/view |
| URL-008 | 기타 | 쇼핑·제품 | 쇼핑·제품 | X | 쇼핑·제품 0.80 / 여행·장소 0.60 | https://www.jeonmae.co.kr/news/articleView.html?idxno=1277183 |
| URL-009 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.80 | https://youtu.be/ADXVtUTgdA4?si=nw60Fg7dymSCu1C2 |
| URL-010 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://n.news.naver.com/mnews/article/001/0016212899?sid=101 |
| URL-011 | 돈·재테크 | 취업·커리어 | 취업·커리어 / 학습·지식 | X | 취업·커리어 0.95 / 학습·지식 0.85 | https://www.instagram.com/p/Dav8FMmk5iy/?igsh=czk4aWY4cmdqZjBs |
| URL-012 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://youtu.be/1AFnKX2-rt0?si=ySbLjlVATwHcyGBp |
| URL-013 | 문화·콘텐츠 |  | 기타 | X |  | https://blog.naver.com/qhrfks1004/224349386864 |
| URL-014 | 문화·콘텐츠 |  | 기타 | X |  | https://gall.dcinside.com/board/view/?id=dcbest&no=448144 |
| URL-015 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 / 생활·할 일 | O | 문화·콘텐츠 0.98 / 생활·할 일 0.85 | https://www.instagram.com/p/DONUNIgE4GR/?igsh=aDk1MHo4dTUxNnUw |
| URL-016 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.youtube.com/shorts/XlDmdpT0_HY |
| URL-017 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://youtu.be/0sTWDcz1xaE?si=GNJkXaz9Xr6WA_c4 |
| URL-018 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://blog.naver.com/onedayfoodmall/224342678366 |
| URL-019 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://smartstore.naver.com/e-sandl/products/273918551 |
| URL-020 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/vp/products/9457512460 |
| URL-021 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 / 학습·지식 0.05 | https://www.instagram.com/p/DXdzEGBGnhg/?igsh=MTRhdjhwZzF5cHc4aQ== |
| URL-022 | 아이디어·영감 | 쇼핑·제품 | 쇼핑·제품 | X | 쇼핑·제품 0.80 / 여행·장소 0.50 | https://cafe.naver.com/canon450dclub/649041 |
| URL-023 | 아이디어·영감 | 기타 | 기타 | X | 기타 1.00 | https://kr.pinterest.com/pin/9288742977535425/ |
| URL-024 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 1.00 | https://youtu.be/pokSYhJ2w4Y?si=hygz_EWccmLDj8iE |
| URL-025 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.80 | https://blog.naver.com/bjstour/224344268733 |
| URL-026 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.95 / 음식·맛집 0.85 | https://www.instagram.com/p/DWpyY9Xjy3D/?igsh=MXgzcm56M2QxZHQybQ== |
| URL-027 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 / 학습·지식 0.05 | https://youtu.be/Axghk4p6Qq8?si=t5Kzxk4qG-em98k6 |
| URL-028 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://blog.naver.com/sinjum77/224347923705 |
| URL-029 | 음식·맛집 |  | 기타 | X |  | https://even-1today.tistory.com/581 |
| URL-030 | 음식·맛집 |  | 기타 | X |  | https://little-cat.tistory.com/entry/수완맛집-베스트-10-순위-추천 |
| URL-031 | 음식·맛집 | 여행·장소 | 여행·장소 | X | 여행·장소 1.00 / 취업·커리어 0.00 / 생활·할 일 0.00 / 쇼핑·제품 0.00 | https://little-cat.tistory.com/entry/수완지구-카페-추천-베스트-10-순위 |
| URL-032 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://m.blog.naver.com/ssbarato/222803352685 |
| URL-033 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://youtu.be/lOPvMP1H27Y?si=mXV0-dLS9Y70j1iB |
| URL-034 | 음악 | 음악 | 음악 | O | 음악 1.00 | https://music.apple.com/us/album/been-by-now/6792676858?i=6792676860 |
| URL-035 | 취업·커리어 |  | 기타 | X |  | https://blog.naver.com/rlawkdrn85/224270747417 |
| URL-036 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 1.00 | https://www.instagram.com/p/DXUC_5uicRF/?igsh=cGt3NXg4aGkwYno3 |
| URL-037 | 학습·지식 |  | 기타 | X |  | https://dev.tistory.com/368 |
| URL-038 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 / 기타 0.05 | https://news.hada.io/topic?id=29408 |
| URL-039 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 / 기타 0.05 | https://velog.io/@hye0n/Redis-공식문서-톺아보기-1.-Redis-개요 |
| URL-040 | 학습·지식 | 취업·커리어 | 취업·커리어 / 생활·할 일 | X | 취업·커리어 0.85 / 생활·할 일 0.75 / 여행·장소 0.65 / 음식·맛집 0.55 / 쇼핑·제품 0.45 / 문화·콘텐츠 0.35 / 건강·운동 0.25 / 기타 0.15 | https://velog.io/@yonghun16/레디스-스트림-Redis-Streams-이란 |
| URL-041 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://www.instagram.com/reel/DUfrGalkVqz/ |
| URL-042 | 학습·지식 | 학습·지식 | 학습·지식 / 취업·커리어 | O | 학습·지식 0.95 / 취업·커리어 0.85 | https://www.youtube.com/watch?v=i0NcKL1JLfg |
| URL-043 | 학습·지식 | 학습·지식 | 학습·지식 / 음악 | O | 학습·지식 0.80 / 음악 0.70 | https://www.youtube.com/watch?v=OKjcchoQVRo |

## image 결과

- 테스트 데이터 없음

## 카테고리 설명

| ID | 카테고리 | 설명 | 예시 |
|---|---|---|---|
| LIFE_TASK | 생활·할 일 | 생활·할 일은 일상생활에서 필요한 준비물, 습관 형성, 일정 관리 등을 다루는 콘텐츠를 의미합니다. 일상적인 생활을 돕고, 효율적인 일정을 계획하는 데 초점을 맞춥니다. | 기숙사에 필요한 물품 목록을 정리한 가이드, 아이의 생활습관을 길러주는 교육용 동영상, 일상생활에서 실용적인 팁을 제공하는 블로그 글 |
| LEARNING_KNOWLEDGE | 학습·지식 | 학습·지식은 학습 방법, 지식 전달, 기술 습득, 학습 도구 및 학습 환경에 대한 정보를 제공하는 카테고리로, 학습자에게 실질적인 도움을 주는 내용을 다룹니다. | 언어 학습 방법에 대한 인스타그램 게시물, AI 기술을 활용한 코딩 역량 개발에 대한 영상, 백색소음 ASMR을 활용한 집중력 향상 방법 소개 |
| CAREER | 취업·커리어 | 취업·커리어 카테고리는 취업 준비, 채용 정보, 경력 개발, 직무 관련 지식 등을 제공하는 콘텐츠를 다룹니다. 이는 취업을 위한 실용적인 정보와 도구를 중심으로 구성되며, 개인의 경력 성장과 직업적 성공을 지원하는 목적을 가집니다. | 취업 준비 필수 채용 사이트 정리, 직무별 면접 팁 공유, 경력 개발을 위한 학습 자료 추천 |
| TRAVEL_PLACE | 여행·장소 | 이 카테고리는 특정 장소나 여행 관련 정보를 제공하며, 여행 계획, 여행지 추천, 여행 경험 등에 대한 내용을 다룹니다. 여행의 목적, 경로, 관광지, 맛집, 코스 등과 관련된 정보를 포함합니다. | 소도시 여행지 추천 및 당일치기 코스 안내, 해외 여행의 난이도와 준비 사항 소개, 지역별 명소 및 카페 정보 제공 |
| FOOD_RESTAURANT | 음식·맛집 | 이 카테고리는 특정 지역 또는 장소에서 제공되는 음식점, 맛집, 관련 식사 경험 및 요리 방법에 대한 정보를 제공하는 데 목적이 있습니다. 사용자는 해당 지역의 인기 메뉴, 추천 식당, 방문 팁 등을 참고하여 식사 계획을 수립하거나 음식에 대한 정보를 얻는 데 활용합니다. | 광주광역시 수완지구의 인기 맛집 10곳을 소개합니다., 수완지구에서 추천하는 소바 전문점과 그 메뉴를 안내합니다., 한국 음식을 처음 접하는 외국인의 식사 경험을 영상으로 소개합니다. |
| SHOPPING_PRODUCT | 쇼핑·제품 | 이 카테고리는 소비자가 구매할 제품이나 쇼핑 관련 정보를 제공하는 콘텐츠를 다룹니다. 주로 구매 목록, 상품 링크, 쇼핑 팁 등 쇼핑 활동을 지원하는 정보를 포함합니다. | 가성비 좋은 상품 추천 리스트, 쇼핑 할인 정보 및 구매 가이드, 필요한 물품을 정리한 장보기 목록 |
| HEALTH_EXERCISE | 건강·운동 | 이 카테고리는 건강 관리와 운동을 통한 체력 향상, 식습관 개선, 운동 기술 및 장비 선택 등에 대한 정보를 제공하는 것을 목적으로 합니다. | 러닝 기록 개선을 위한 코어 운동의 중요성에 대한 설명, 다이어트 중 햄버거 선택 시 단백질과 당분 함량을 고려한 식단 조언, 러닝화 선택 시 발 모양과 체중에 따른 적합성 비교 |
| CULTURE_CONTENT | 문화·콘텐츠 | 문화·콘텐츠 카테고리는 예술, 음악, 콘서트, 콘텐츠 제작 및 공유 관련 정보를 다루며, 문화적 활동과 창작물에 대한 접근성을 높이는 데 목적을 두고 있습니다. | 경기도에서 열리는 무료 콘서트 일정 안내, 뉴진스의 컴백 영상 공유, 갤러리에서 자동 짤방 이미지 설정 방법 |
| MUSIC | 음악 | 음악 카테고리는 음악 콘텐츠의 제공, 감상, 또는 관련 정보를 다루는 목적을 가진 데이터를 포함합니다. | 음악 앨범의 공식 제공 URL, 음악 작곡가의 창작 배경 설명, 음악 장르에 따른 분류 기준 |
| MONEY_FINANCE | 돈·재테크 | 돈·재테크는 개인의 재무 관리, 투자 전략, 자산 형성 및 금융 상품에 대한 정보를 제공하는 카테고리로, 개인의 경제적 안정과 성장에 도움을 주는 내용을 다룹니다. | 투자 수익률 비교 및 자산 배분 전략, 청년 주택 구입을 위한 지원 정책 안내, 개인 연금 계획 수립 방법 |
| IDEA_INSPIRATION | 아이디어·영감 | 이 카테고리는 창의적인 아이디어 도출, 영감 부여, 창의적 사고 방법에 대한 정보를 제공하는 목적을 가진 콘텐츠를 분류합니다. | 창의적인 아이디어를 유도하는 사고 기법에 대한 설명, 새로운 아이디어를 떠올리기 위한 실천 방법, 영감을 얻기 위한 창의적 사고 프로세스 |
| OTHER | 기타 | 기타 카테고리는 주로 뉴스 사이트, 영상 콘텐츠, 또는 특정 주제에 대한 보도 및 정보 제공을 목적으로 하며, 다른 카테고리에 포함되지 않는 다양한 형태의 정보를 담고 있습니다. | 언론사 홈페이지를 통해 제공되는 뉴스 기사 링크, 영상 플랫폼에서 제공되는 콘텐츠 영상 링크, 특정 주제에 대한 보도나 정보를 담고 있는 웹사이트 링크 |
