# 카테고리 분류 테스트 보고서

## 실행 정보

- 모델: qwen-local
- 데이터셋: test:url
- 전체 데이터: 31건
- 카테고리 설명: 포함
- 선택 정책: score 0.65 이상, 최대 2개
- 실행 일시: 2026-07-26T18:57:19.146204+09:00 ~ 2026-07-26T19:00:50.031281+09:00

## 정확도 요약

| 구분 | 데이터 수 | 정답 포함 수 | Top-1 | 정확 일치 | 완화 정확도 | 평균 선택 수 | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|---|---|---|---|---|
| 전체 | 31 | 25 | 80.6% | 67.7% | 80.6% | 1.129 | 78.2% | 86.1% | 78.4% |
| memo | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| url | 31 | 25 | 80.6% | 67.7% | 80.6% | 1.129 | 78.2% | 86.1% | 78.4% |
| image | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## 전체 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 1 | 100.0% | 100.0% | 100.0% |
| 학습·지식 | 6 | 57.1% | 66.7% | 61.5% |
| 취업·커리어 | 1 | 100.0% | 100.0% | 100.0% |
| 여행·장소 | 2 | 100.0% | 100.0% | 100.0% |
| 음식·맛집 | 3 | 75.0% | 100.0% | 85.7% |
| 쇼핑·제품 | 1 | 50.0% | 100.0% | 66.7% |
| 건강·운동 | 5 | 100.0% | 100.0% | 100.0% |
| 문화·콘텐츠 | 2 | 66.7% | 100.0% | 80.0% |
| 음악 | 1 | 50.0% | 100.0% | 66.7% |
| 돈·재테크 | 3 | 100.0% | 66.7% | 80.0% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 기타 | 3 | 40.0% | 66.7% | 50.0% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.90 / 학습·지식 0.70 | https://www.instagram.com/reel/Da443z7pFQr/?igsh=anJpbTZoZGFuNnA1 |
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 / 쇼핑·제품 | O | 건강·운동 0.90 / 쇼핑·제품 0.70 | https://www.instagram.com/reel/DaePl8rSnJ0/?igsh=ZmI0ZGM4bnhqdnd1 |
| URL-003 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.instagram.com/reel/Dam0TYJKhg7/?igsh=Y2YzMzRjdjV4dzRp |
| URL-004 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.90 / 학습·지식 0.70 | https://www.instagram.com/reel/Dar1_KmBwHk/?igsh=cTk1OHlodjQ3c2k2 |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.instagram.com/reel/DZTqt4Uhx4s/?igsh=d3AzZXVobWQ5NnRu |
| URL-006 | 기타 | 기타 | 기타 | O | 기타 1.00 | https://news.kbs.co.kr/news/pc/main/main.html |
| URL-008 | 기타 | 기타 | 기타 | O | 기타 0.80 | https://www.jeonmae.co.kr/news/articleView.html?idxno=1277183 |
| URL-009 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 1.00 | https://youtu.be/ADXVtUTgdA4?si=nw60Fg7dymSCu1C2 |
| URL-010 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://n.news.naver.com/mnews/article/001/0016212899?sid=101 |
| URL-011 | 돈·재테크 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 취업·커리어 0.60 | https://www.instagram.com/p/Dav8FMmk5iy/?igsh=czk4aWY4cmdqZjBs |
| URL-012 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.90 / 학습·지식 0.60 | https://youtu.be/1AFnKX2-rt0?si=ySbLjlVATwHcyGBp |
| URL-015 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.instagram.com/p/DONUNIgE4GR/?igsh=aDk1MHo4dTUxNnUw |
| URL-016 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.youtube.com/shorts/XlDmdpT0_HY |
| URL-017 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://youtu.be/0sTWDcz1xaE?si=GNJkXaz9Xr6WA_c4 |
| URL-021 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.90 / 학습·지식 0.60 | https://www.instagram.com/p/DXdzEGBGnhg/?igsh=MTRhdjhwZzF5cHc4aQ== |
| URL-022 | 아이디어·영감 | 기타 | 기타 | X | 기타 0.80 | https://cafe.naver.com/canon450dclub/649041 |
| URL-023 | 아이디어·영감 | 기타 | 기타 | X | 기타 0.80 | https://kr.pinterest.com/pin/9288742977535425/ |
| URL-024 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 1.00 | https://youtu.be/pokSYhJ2w4Y?si=hygz_EWccmLDj8iE |
| URL-026 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.95 / 음식·맛집 0.85 | https://www.instagram.com/p/DWpyY9Xjy3D/?igsh=MXgzcm56M2QxZHQybQ== |
| URL-027 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.90 | https://youtu.be/Axghk4p6Qq8?si=t5Kzxk4qG-em98k6 |
| URL-028 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://blog.naver.com/sinjum77/224347923705 |
| URL-031 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://little-cat.tistory.com/entry/수완지구-카페-추천-베스트-10-순위 |
| URL-033 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://youtu.be/lOPvMP1H27Y?si=mXV0-dLS9Y70j1iB |
| URL-034 | 음악 | 음악 | 음악 | O | 음악 1.00 | https://music.apple.com/us/album/been-by-now/6792676858?i=6792676860 |
| URL-036 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 1.00 | https://www.instagram.com/p/DXUC_5uicRF/?igsh=cGt3NXg4aGkwYno3 |
| URL-038 | 학습·지식 | 기타 | 기타 | X | 기타 0.80 | https://news.hada.io/topic?id=29408 |
| URL-039 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@hye0n/Redis-공식문서-톺아보기-1.-Redis-개요 |
| URL-040 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@yonghun16/레디스-스트림-Redis-Streams-이란 |
| URL-041 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://www.instagram.com/reel/DUfrGalkVqz/ |
| URL-042 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://www.youtube.com/watch?v=i0NcKL1JLfg |
| URL-043 | 학습·지식 | 음악 | 음악 | X | 음악 1.00 | https://www.youtube.com/watch?v=OKjcchoQVRo |

## memo 결과

- 테스트 데이터 없음

## url 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 1 | 100.0% | 100.0% | 100.0% |
| 학습·지식 | 6 | 57.1% | 66.7% | 61.5% |
| 취업·커리어 | 1 | 100.0% | 100.0% | 100.0% |
| 여행·장소 | 2 | 100.0% | 100.0% | 100.0% |
| 음식·맛집 | 3 | 75.0% | 100.0% | 85.7% |
| 쇼핑·제품 | 1 | 50.0% | 100.0% | 66.7% |
| 건강·운동 | 5 | 100.0% | 100.0% | 100.0% |
| 문화·콘텐츠 | 2 | 66.7% | 100.0% | 80.0% |
| 음악 | 1 | 50.0% | 100.0% | 66.7% |
| 돈·재테크 | 3 | 100.0% | 66.7% | 80.0% |
| 아이디어·영감 | 3 | 100.0% | 33.3% | 50.0% |
| 기타 | 3 | 40.0% | 66.7% | 50.0% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.90 / 학습·지식 0.70 | https://www.instagram.com/reel/Da443z7pFQr/?igsh=anJpbTZoZGFuNnA1 |
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 / 쇼핑·제품 | O | 건강·운동 0.90 / 쇼핑·제품 0.70 | https://www.instagram.com/reel/DaePl8rSnJ0/?igsh=ZmI0ZGM4bnhqdnd1 |
| URL-003 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.instagram.com/reel/Dam0TYJKhg7/?igsh=Y2YzMzRjdjV4dzRp |
| URL-004 | 건강·운동 | 건강·운동 | 건강·운동 / 학습·지식 | O | 건강·운동 0.90 / 학습·지식 0.70 | https://www.instagram.com/reel/Dar1_KmBwHk/?igsh=cTk1OHlodjQ3c2k2 |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.instagram.com/reel/DZTqt4Uhx4s/?igsh=d3AzZXVobWQ5NnRu |
| URL-006 | 기타 | 기타 | 기타 | O | 기타 1.00 | https://news.kbs.co.kr/news/pc/main/main.html |
| URL-008 | 기타 | 기타 | 기타 | O | 기타 0.80 | https://www.jeonmae.co.kr/news/articleView.html?idxno=1277183 |
| URL-009 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 1.00 | https://youtu.be/ADXVtUTgdA4?si=nw60Fg7dymSCu1C2 |
| URL-010 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://n.news.naver.com/mnews/article/001/0016212899?sid=101 |
| URL-011 | 돈·재테크 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 / 취업·커리어 0.60 | https://www.instagram.com/p/Dav8FMmk5iy/?igsh=czk4aWY4cmdqZjBs |
| URL-012 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.90 / 학습·지식 0.60 | https://youtu.be/1AFnKX2-rt0?si=ySbLjlVATwHcyGBp |
| URL-015 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.instagram.com/p/DONUNIgE4GR/?igsh=aDk1MHo4dTUxNnUw |
| URL-016 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.youtube.com/shorts/XlDmdpT0_HY |
| URL-017 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://youtu.be/0sTWDcz1xaE?si=GNJkXaz9Xr6WA_c4 |
| URL-021 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.90 / 학습·지식 0.60 | https://www.instagram.com/p/DXdzEGBGnhg/?igsh=MTRhdjhwZzF5cHc4aQ== |
| URL-022 | 아이디어·영감 | 기타 | 기타 | X | 기타 0.80 | https://cafe.naver.com/canon450dclub/649041 |
| URL-023 | 아이디어·영감 | 기타 | 기타 | X | 기타 0.80 | https://kr.pinterest.com/pin/9288742977535425/ |
| URL-024 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 1.00 | https://youtu.be/pokSYhJ2w4Y?si=hygz_EWccmLDj8iE |
| URL-026 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.95 / 음식·맛집 0.85 | https://www.instagram.com/p/DWpyY9Xjy3D/?igsh=MXgzcm56M2QxZHQybQ== |
| URL-027 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.90 | https://youtu.be/Axghk4p6Qq8?si=t5Kzxk4qG-em98k6 |
| URL-028 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://blog.naver.com/sinjum77/224347923705 |
| URL-031 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://little-cat.tistory.com/entry/수완지구-카페-추천-베스트-10-순위 |
| URL-033 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://youtu.be/lOPvMP1H27Y?si=mXV0-dLS9Y70j1iB |
| URL-034 | 음악 | 음악 | 음악 | O | 음악 1.00 | https://music.apple.com/us/album/been-by-now/6792676858?i=6792676860 |
| URL-036 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 1.00 | https://www.instagram.com/p/DXUC_5uicRF/?igsh=cGt3NXg4aGkwYno3 |
| URL-038 | 학습·지식 | 기타 | 기타 | X | 기타 0.80 | https://news.hada.io/topic?id=29408 |
| URL-039 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@hye0n/Redis-공식문서-톺아보기-1.-Redis-개요 |
| URL-040 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@yonghun16/레디스-스트림-Redis-Streams-이란 |
| URL-041 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://www.instagram.com/reel/DUfrGalkVqz/ |
| URL-042 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://www.youtube.com/watch?v=i0NcKL1JLfg |
| URL-043 | 학습·지식 | 음악 | 음악 | X | 음악 1.00 | https://www.youtube.com/watch?v=OKjcchoQVRo |

## image 결과

- 테스트 데이터 없음

## 카테고리 설명

| ID | 카테고리 | 설명 | 예시 |
|---|---|---|---|
| LIFE_TASK | 생활·할 일 | 생활·할 일은 일상생활에서 필요한 준비물, 습관 형성, 일정 관리 등을 다루는 콘텐츠를 의미합니다. 일상적인 생활을 돕고, 효율적인 일정을 계획하는 데 초점을 맞춥니다. | 기숙사에 필요한 물품 목록을 정리한 가이드, 아이의 생활습관을 길러주는 교육용 동영상, 일상생활에서 실용적인 팁을 제공하는 블로그 글 |
| LEARNING_KNOWLEDGE | 학습·지식 | 학습·지식은 새로운 지식을 습득하거나 기존 지식을 체계화하여 개인의 학습과 성장에 도움을 주는 내용을 다룹니다. | 새로운 언어를 배우는 방법에 대한 안내, 컴퓨터 공학 전공자가 갖춰야 할 역량에 대한 분석, 효과적인 학습 환경을 조성하는 음악 소개 |
| CAREER | 취업·커리어 | 취업·커리어 카테고리는 취업 준비, 채용 정보, 경력 개발, 직무 관련 자료 등을 제공하는 콘텐츠를 다룹니다. 이는 개인의 직업적 성장과 경력 관리에 도움을 주는 정보를 중심으로 구성됩니다. | 취업 준비 필수 채용 사이트 안내, 직무별 면접 팁 공유, 경력 개발을 위한 학습 자료 제공 |
| TRAVEL_PLACE | 여행·장소 | 이 카테고리는 특정 장소나 여행 경험에 대한 정보를 제공하며, 여행 계획 수립, 관광지 탐방, 현지 문화 체험 등에 대한 내용을 다룹니다. | 명소 탐방 및 관광 정보 제공, 지역별 여행 팁과 추천 코스 안내, 현지 맛집과 카페 추천 |
| FOOD_RESTAURANT | 음식·맛집 | 음식·맛집은 특정 지역 또는 음식 종류에 대한 식당, 요리, 음식 재료, 맛집 추천, 음식 관련 경험 등을 다루는 카테고리로, 음식을 중심으로 한 정보나 경험 공유를 목적으로 합니다. | 광주 수완지구의 인기 맛집 10곳을 소개한 글, 한국 음식을 처음 접하는 외국인의 시도 모습을 담은 영상, 특정 음식 재료를 사용한 요리법이나 조합에 대한 설명 |
| SHOPPING_PRODUCT | 쇼핑·제품 | 쇼핑·제품은 소비자가 구매할 수 있는 상품이나 쇼핑 관련 정보를 제공하는 콘텐츠를 의미합니다. 이 카테고리는 구체적인 상품 목록, 할인 정보, 쇼핑 팁 등 쇼핑 활동을 지원하는 내용을 중심으로 합니다. | 가성비 좋은 상품 추천 리스트, 할인 기간 중인 쇼핑몰의 특가 상품 안내, 구매할 상품을 정리한 장보기 목록 |
| HEALTH_EXERCISE | 건강·운동 | 이 카테고리는 건강 관리와 운동을 통한 체력 향상, 식습관 개선, 운동 기술 및 장비 선택 등에 대한 정보를 제공하는 것을 목적으로 합니다. | 러닝 기록 개선을 위한 코어 운동의 중요성에 대한 설명, 다이어트 중 햄버거 선택 시 고려해야 할 영양 성분 비교, 러닝화 선택 시 사용자 평가와 신체 조건에 따른 적합성 분석 |
| CULTURE_CONTENT | 문화·콘텐츠 | 문화·콘텐츠는 예술, 음악, 공연, 콘서트, 콘텐츠 제작 및 관련 정보를 다루는 카테고리로, 문화적 활동과 콘텐츠 소비에 대한 정보를 제공합니다. | 경기도에서 열리는 무료 콘서트 일정 및 장소 정보, 뉴진스의 컴백 영상 공유, 디지털 콘텐츠 제작 및 관리 방법 |
| MUSIC | 음악 | 음악 카테고리는 음악 콘텐츠의 제공, 감상, 또는 관련 정보를 다루는 목적을 가진 데이터를 포함합니다. | 음악 앨범의 공식 제공 URL, 음악 작곡가의 창작 배경 설명, 음악 장르에 따른 분류 기준 |
| MONEY_FINANCE | 돈·재테크 | 돈·재테크는 개인의 재무 관리, 투자 전략, 자산 형성 및 금융 상품에 대한 정보를 제공하는 카테고리로, 개인의 경제적 안정과 성장에 도움을 주는 내용을 다룹니다. | 투자 수익률 비교 및 자산 배분 전략, 청년 주택 구입을 위한 지원 정책 안내, 개인 연금 계획 수립 방법 |
| IDEA_INSPIRATION | 아이디어·영감 | 이 카테고리는 창의적인 아이디어 도출, 영감 부여, 창의적 사고 방법에 대한 정보를 제공하는 목적을 가진 콘텐츠를 분류합니다. | 창의적인 아이디어를 유도하는 사고 기법에 대한 설명, 새로운 아이디어를 떠올리기 위한 실천 방법, 영감을 얻기 위한 창의적 사고 프로세스 |
| OTHER | 기타 | 기타 카테고리는 주제나 목적에 따라 명확히 분류되지 않거나, 여러 카테고리와 중복될 수 있는 다양한 정보나 콘텐츠를 포함합니다. 주로 특정 주제에 대한 보도, 일반적인 정보 공유, 또는 특별한 목적을 가진 콘텐츠를 다룹니다. | 다양한 소식을 전하는 뉴스 사이트, 국제 시장 진출 관련한 경제 활동 보도, 유쾌한 동물 행동을 담은 영상 콘텐츠 |
