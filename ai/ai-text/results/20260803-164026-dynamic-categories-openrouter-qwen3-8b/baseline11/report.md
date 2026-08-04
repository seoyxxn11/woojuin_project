# 카테고리 분류 테스트 보고서

## 실행 정보

- 모델: openrouter-qwen3-8b
- 데이터셋: dynamic-baseline
- 전체 데이터: 112건
- 카테고리 설명: 포함
- 선택 정책: score 0.65 이상, 최대 2개
- 실행 일시: 2026-08-03T16:40:26.834983+09:00 ~ 2026-08-03T16:45:34.921654+09:00

## 정확도 요약

| 구분 | 데이터 수 | 정답 포함 수 | Top-1 | 정확 일치 | 완화 정확도 | 평균 선택 수 | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|---|---|---|---|---|
| 전체 | 112 | 73 | 64.3% | 62.5% | 65.2% | 1.027 | 70.2% | 64.9% | 63.1% |
| memo | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| url | 112 | 73 | 64.3% | 62.5% | 65.2% | 1.027 | 70.2% | 64.9% | 63.1% |
| image | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## 전체 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 10 | 100.0% | 60.0% | 75.0% |
| 학습·지식 | 11 | 33.3% | 81.8% | 47.4% |
| 취업·커리어 | 10 | 33.3% | 20.0% | 25.0% |
| 여행·장소 | 9 | 88.9% | 88.9% | 88.9% |
| 음식·맛집 | 10 | 71.4% | 100.0% | 83.3% |
| 쇼핑·제품 | 11 | 90.9% | 90.9% | 90.9% |
| 건강·운동 | 11 | 100.0% | 81.8% | 90.0% |
| 문화·콘텐츠 | 10 | 61.5% | 80.0% | 69.6% |
| 돈·재테크 | 10 | 80.0% | 80.0% | 80.0% |
| 아이디어·영감 | 10 | 100.0% | 20.0% | 33.3% |
| 기타 | 10 | 12.5% | 10.0% | 11.1% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://kormedi.com/1341895/ |
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://brunch.co.kr/@tenbody/1122 |
| URL-003 | 건강·운동 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://en.wikipedia.org/wiki/Nerve_glide |
| URL-004 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.95 | https://www.emotiv.com/ko/neuroscience/insomnia |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.psychiatricnews.net/news/articleView.html?idxno=36398 |
| URL-006 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.95 | https://healthlab.ai.kr/수면의-질-높이는-7가지-과학적-방법/ |
| URL-007 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.90 | https://yuyuteijin.co.kr/blog/7368ecdf-a987-4315-9e31-e7a3dfe2e6ee/ |
| URL-008 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://namu.wiki/w/유산소%20운동 |
| URL-009 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://brunch.co.kr/@tenbody/743 |
| URL-010 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.95 | https://www.nhis.or.kr/magazin/168/html/sub7.html |
| URL-011 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://news.hidoc.co.kr/news/articleView.html?idxno=44199 |
| URL-012 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.90 | https://unse.daily.co.kr/?p=horoscope |
| URL-013 | 기타 | 기타 | 기타 | O | 기타 1.00 | https://fortune.nate.com/contents/freeunse/freeunseframe.nate?freeUnseId=week02 |
| URL-014 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.80 | https://m.fortunade.com/unse/free/star/daily.php?gtype=2 |
| URL-015 | 기타 | 돈·재테크 | 돈·재테크 | X | 돈·재테크 0.85 | https://apt2.me/saju/saju.jsp |
| URL-016 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.85 / 문화·콘텐츠 0.60 | https://kr.vonvon.me/ko/ |
| URL-017 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://test-it.co.kr/ |
| URL-018 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.90 | https://poomang.com/en-US |
| URL-019 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.70 | https://temon.kr/ |
| URL-020 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 | https://answer.moaform.com/answers/EnPBng |
| URL-021 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.70 | https://simritest.com/ |
| URL-022 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://www.kcie.or.kr/mobile/guide/3/18/web_view?content_idx=902 |
| URL-023 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://finance.greatsisyphus.com/2026/07/etf-investing-for-beginners-easy-start.html |
| URL-024 | 돈·재테크 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://eanews.kr/news/932322 |
| URL-025 | 돈·재테크 | 학습·지식 | 학습·지식 / 돈·재테크 | O | 학습·지식 0.95 / 돈·재테크 0.85 | https://weolbu.com/product/5237 |
| URL-026 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://weolbu.com/community/2613662/ |
| URL-027 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.70 | https://homedubu.com/10754/ |
| URL-028 | 돈·재테크 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 1.00 | https://www.gqkorea.co.kr/2026/04/26/ |
| URL-029 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://www.jobkorea.co.kr/goodjob/tip/view?News_No=11223 |
| URL-030 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://www.cardif.co.kr/life-stage/rich-daily-account-book-tips.do |
| URL-031 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://info-pickle.co.kr/79 |
| URL-032 | 문화·콘텐츠 | 기타 | 기타 | X | 기타 0.50 | https://www.youtube.com/watch?v=8sDiWUV46FI&list=RD8sDiWUV46FI&start_radio=1&t=18s |
| URL-033 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://kr.trip.com/events/9109368-2026-south-korea-concerts-collection/ |
| URL-034 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://kr.trip.com/events/8867097-2026-concerts-collection/ |
| URL-035 | 문화·콘텐츠 | 여행·장소 | 여행·장소 | X | 여행·장소 0.90 | https://kr.trip.com/moments/theme/poi-sema-seoul-museum-of-art-95224-guides-993135/ |
| URL-036 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://jcks100.com/entry/2025-트로트-콘서트-4월-5월-페스티벌-공연-티켓-예매 |
| URL-037 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://kr.trip.com/moments/theme/poi-sema-seoul-museum-of-art-95224-exhibitions-990362/ |
| URL-038 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://www.marieclairekorea.com/pinpage/2026/01/2026-exhibition/ |
| URL-039 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://ddoing.co.kr/ddoing_exhibition_schedule |
| URL-040 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://ko.wikipedia.org/wiki/2026년_대한민국의_영화_목록 |
| URL-041 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.d-art.co.kr/news/articleView.html?idxno=4764 |
| URL-042 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.95 | https://bravo.etoday.co.kr/view/atc_view/13057 |
| URL-043 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.home-learn.co.kr/newsroom/news/A/2069 |
| URL-044 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.seouland.com/arti/society/society_general/2749.html |
| URL-045 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.95 | https://www.woowarhanclean.com/honeyinfotidy/?bmode=view&idx=7086792 |
| URL-046 | 생활·할 일 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.95 | https://brunch.co.kr/magazine/single-person |
| URL-047 | 생활·할 일 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.85 / 돈·재테크 0.15 | https://play.google.com/store/apps/details?id=com.lazyheroes.erfe&hl=ko |
| URL-048 | 생활·할 일 | 기타 | 기타 | X | 기타 0.80 | https://apps.apple.com/kr/app/id6745560834 |
| URL-049 | 생활·할 일 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.95 | https://brunch.co.kr/@ylangylang/116 |
| URL-050 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.95 | https://namu.wiki/w/자취/조언 |
| URL-051 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.threads.com/@prozachi/post/DIuf95oNelD/ |
| URL-052 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.85 | https://www.apple.com/kr/mac-studio/ |
| URL-053 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 | https://m.compuzone.co.kr/product/product_list.htm?BigDivNo=2&MediumDivNo=1076 |
| URL-054 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://m.gsshop.com/search/searchSect.gs?tq=노트북가방&mseq=406355&ab=a |
| URL-055 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/search?q=노트북가방백팝 |
| URL-056 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 | https://dorishop.oopy.io/397d87ba-6a5e-4dd3-ba9f-601eed0eef18 |
| URL-057 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://shinsegaemall.ssg.com/search.ssg?query=명품노트북가방 |
| URL-058 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 | https://chicpap.com/blog/명품-노트북-가방-매일-들-수-있는-5가지-선택지 |
| URL-059 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/categories/328791 |
| URL-060 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/search?q=실내텐트 |
| URL-061 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.90 | https://bodyitlove.com/캠핑-텐트/ |
| URL-062 | 쇼핑·제품 |  | 기타 | X |  | https://www.youtube.com/watch?v=mJTE8JBOkkw |
| URL-063 | 아이디어·영감 | 기타 | 기타 | X | 기타 0.30 | https://brunch.co.kr/@solobiznight |
| URL-064 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 1.00 | https://brunch.co.kr/@solobiznight/33 |
| URL-065 | 아이디어·영감 | 쇼핑·제품 | 쇼핑·제품 | X | 쇼핑·제품 0.95 | https://www.mobiinside.co.kr/2023/05/03/dana-smartstore-interview/ |
| URL-066 | 아이디어·영감 | 취업·커리어 | 취업·커리어 | X | 취업·커리어 0.85 | https://www.teamblind.com/kr/post/HHomJcfW |
| URL-067 | 아이디어·영감 | 돈·재테크 | 돈·재테크 | X | 돈·재테크 1.00 | https://bepractice01.com/ |
| URL-068 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 0.95 | https://underdogs.co.kr/contents/blogs/집에서-시작할-수-있는-창업-아이디어-20가지/ |
| URL-069 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 / 취업·커리어 0.15 | https://claireclass.com/ |
| URL-070 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.70 | https://brunch.co.kr/@e8362cab2f0c484/45 |
| URL-071 | 아이디어·영감 |  | 기타 | X |  | https://www.junsungki.com/magazine/post-detail.do?id=2744 |
| URL-072 | 아이디어·영감 | 기타 | 기타 | X | 기타 1.00 | https://apps.apple.com/kr/app/id1610260075 |
| URL-073 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.70 / 음식·맛집 0.30 | https://v.daum.net/v/7RSTWNtnjC |
| URL-074 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 | https://www.yeogi.com/content/dom-ko-busan-hotel-bx2-busan-haeundae-travel-course |
| URL-075 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.80 / 음식·맛집 0.70 | https://triple.guide/articles/fd0068b5-08c8-4949-8ff4-874233fe2ff5 |
| URL-076 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 | https://studio24.kr/3077 |
| URL-077 | 여행·장소 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.95 | https://uhflat.co.kr/badamaul/?bmode=view&idx=127804469 |
| URL-078 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.80 / 음식·맛집 0.60 | https://kr.trip.com/guide/theme/부산+혼자+여행.html |
| URL-079 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://kr.trip.com/moments/poi-best-louis-hamilton-hotel-haeundae-21485227 |
| URL-080 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 | https://news.airbnb.com/ko/2018-coastal-side-listings/ |
| URL-081 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.90 | https://kr.trip.com/moments/theme/destination-gangwon-state-1185-thorough-guides-993136 |
| URL-082 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=전주+콩나물국밥 |
| URL-083 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://korean.visitkorea.or.kr/detail/rem_detail.do?cotid=a2bfb276-ce31-4dd3-8154-4866e408664b |
| URL-084 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://brunch.co.kr/@bakilhong66uhji/513 |
| URL-085 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://www.welfarehello.com/community/hometownNews/048b6105-e854-469d-ad91-cbdb86808393 |
| URL-086 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://guide.michelin.com/kr/ko/seoul-capital-area/kr-seoul/restaurant/gwanghwamun-gukbap |
| URL-087 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://diningcode.com/list.dc?keyword=20대&query=강남+삼겡살 |
| URL-088 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남구+삼겡살 |
| URL-089 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://www.diningcode.com/list.dc?query=강남역+삼겡살 |
| URL-090 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://www.diningcode.com/list.dc?query=강남+삼겡살무한리필 |
| URL-091 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남역+돼지고기+가성비 |
| URL-092 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@ahn-sujin/React-Query-useInfiniteQuery-사용해서-무한스크롤-구현하기 |
| URL-093 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 0.95 | https://community.linkareer.com/employment_data/4953814 |
| URL-094 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 0.95 | https://www.ssafy.com/ksp/servlet/swp.board.controller.SwpBoardServlet?p_process=select-board-view&p_menu_cd=M0204&p_tabseq=226509&p_seq=80&p_pageno=2 |
| URL-095 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://csr.samsung.com/ko/programViewSSWA.do |
| URL-096 | 취업·커리어 | 기타 | 기타 | X | 기타 0.30 | https://csr.samsung.com/ko/newsroom/news/ |
| URL-097 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@hyeseong-int/알고리즘-스터디-진행방식 |
| URL-098 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@cmh2806/코딩테스트-스타디-1주차-회고 |
| URL-099 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@0715yk/MEMO-알고리즘-잡스-후기 |
| URL-100 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@rimgosu/99클럽-코딩테스트-스터디-4기-후기 |
| URL-101 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://velog.io/@jkseo50/Programmers-코딩테스트와-실무-역량-모두-잡는-알고리즘-스터디-후기 |
| URL-102 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.90 | https://www.youtube.com/watch?v=3aNtTUHJeDY |
| URL-103 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@1w2k/cs-과목-길잡이 |
| URL-104 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@jojehuni_9759/CS-전공지식-정리-네트워크-1-네트워크의-기초 |
| URL-105 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@dbwlgns98/네트워크-CS정리1탄 |
| URL-106 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@dbstjrwnekd/네트워크-정리1 |
| URL-107 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 | https://velog.io/@jincode93/CS-네트워크-요약-정리 |
| URL-108 | 학습·지식 | 학습·지식 | 학습·지식 / 취업·커리어 | O | 학습·지식 0.95 / 취업·커리어 0.70 | https://velog.io/@munhyojin7338/신입-백엔드-개발자-기술-면접-질문-정리 |
| URL-109 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 | https://velog.io/@kk1112k/백엔드-개발-기술면접-정리-Java-추가중 |
| URL-110 | 학습·지식 | 취업·커리어 | 취업·커리어 | X | 취업·커리어 1.00 | https://velog.io/@yukina1418/최근-면접을-다니면서-받았던-질문들 |
| URL-111 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@namdaeun/요즘-프론트엔드-디자인-패턴-뭐가-정답일까 |
| URL-112 | 학습·지식 | 취업·커리어 | 취업·커리어 | X | 취업·커리어 1.00 | https://velog.io/@oojoo/백엔드-자기소개서면접-꿀Tip |

## memo 결과

- 테스트 데이터 없음

## url 결과

### 카테고리별 지표

| 카테고리 | 표본 | Precision | Recall | F1 |
|---|---|---|---|---|
| 생활·할 일 | 10 | 100.0% | 60.0% | 75.0% |
| 학습·지식 | 11 | 33.3% | 81.8% | 47.4% |
| 취업·커리어 | 10 | 33.3% | 20.0% | 25.0% |
| 여행·장소 | 9 | 88.9% | 88.9% | 88.9% |
| 음식·맛집 | 10 | 71.4% | 100.0% | 83.3% |
| 쇼핑·제품 | 11 | 90.9% | 90.9% | 90.9% |
| 건강·운동 | 11 | 100.0% | 81.8% | 90.0% |
| 문화·콘텐츠 | 10 | 61.5% | 80.0% | 69.6% |
| 돈·재테크 | 10 | 80.0% | 80.0% | 80.0% |
| 아이디어·영감 | 10 | 100.0% | 20.0% | 33.3% |
| 기타 | 10 | 12.5% | 10.0% | 11.1% |

### 개별 테스트 결과

| ID | 정답 | Top-1 | 최종 선택 | 정답 포함 | 점수 | 제목 |
|---|---|---|---|---|---|---|
| URL-001 | 건강·운동 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://kormedi.com/1341895/ |
| URL-002 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://brunch.co.kr/@tenbody/1122 |
| URL-003 | 건강·운동 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://en.wikipedia.org/wiki/Nerve_glide |
| URL-004 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.95 | https://www.emotiv.com/ko/neuroscience/insomnia |
| URL-005 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://www.psychiatricnews.net/news/articleView.html?idxno=36398 |
| URL-006 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.95 | https://healthlab.ai.kr/수면의-질-높이는-7가지-과학적-방법/ |
| URL-007 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.90 | https://yuyuteijin.co.kr/blog/7368ecdf-a987-4315-9e31-e7a3dfe2e6ee/ |
| URL-008 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://namu.wiki/w/유산소%20운동 |
| URL-009 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://brunch.co.kr/@tenbody/743 |
| URL-010 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 0.95 | https://www.nhis.or.kr/magazin/168/html/sub7.html |
| URL-011 | 건강·운동 | 건강·운동 | 건강·운동 | O | 건강·운동 1.00 | https://news.hidoc.co.kr/news/articleView.html?idxno=44199 |
| URL-012 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.90 | https://unse.daily.co.kr/?p=horoscope |
| URL-013 | 기타 | 기타 | 기타 | O | 기타 1.00 | https://fortune.nate.com/contents/freeunse/freeunseframe.nate?freeUnseId=week02 |
| URL-014 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.80 | https://m.fortunade.com/unse/free/star/daily.php?gtype=2 |
| URL-015 | 기타 | 돈·재테크 | 돈·재테크 | X | 돈·재테크 0.85 | https://apt2.me/saju/saju.jsp |
| URL-016 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.85 / 문화·콘텐츠 0.60 | https://kr.vonvon.me/ko/ |
| URL-017 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://test-it.co.kr/ |
| URL-018 | 기타 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.90 | https://poomang.com/en-US |
| URL-019 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.70 | https://temon.kr/ |
| URL-020 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.80 | https://answer.moaform.com/answers/EnPBng |
| URL-021 | 기타 | 학습·지식 | 학습·지식 | X | 학습·지식 0.70 | https://simritest.com/ |
| URL-022 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://www.kcie.or.kr/mobile/guide/3/18/web_view?content_idx=902 |
| URL-023 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://finance.greatsisyphus.com/2026/07/etf-investing-for-beginners-easy-start.html |
| URL-024 | 돈·재테크 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://eanews.kr/news/932322 |
| URL-025 | 돈·재테크 | 학습·지식 | 학습·지식 / 돈·재테크 | O | 학습·지식 0.95 / 돈·재테크 0.85 | https://weolbu.com/product/5237 |
| URL-026 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://weolbu.com/community/2613662/ |
| URL-027 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.70 | https://homedubu.com/10754/ |
| URL-028 | 돈·재테크 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 1.00 | https://www.gqkorea.co.kr/2026/04/26/ |
| URL-029 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://www.jobkorea.co.kr/goodjob/tip/view?News_No=11223 |
| URL-030 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 1.00 | https://www.cardif.co.kr/life-stage/rich-daily-account-book-tips.do |
| URL-031 | 돈·재테크 | 돈·재테크 | 돈·재테크 | O | 돈·재테크 0.95 | https://info-pickle.co.kr/79 |
| URL-032 | 문화·콘텐츠 | 기타 | 기타 | X | 기타 0.50 | https://www.youtube.com/watch?v=8sDiWUV46FI&list=RD8sDiWUV46FI&start_radio=1&t=18s |
| URL-033 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://kr.trip.com/events/9109368-2026-south-korea-concerts-collection/ |
| URL-034 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://kr.trip.com/events/8867097-2026-concerts-collection/ |
| URL-035 | 문화·콘텐츠 | 여행·장소 | 여행·장소 | X | 여행·장소 0.90 | https://kr.trip.com/moments/theme/poi-sema-seoul-museum-of-art-95224-guides-993135/ |
| URL-036 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://jcks100.com/entry/2025-트로트-콘서트-4월-5월-페스티벌-공연-티켓-예매 |
| URL-037 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://kr.trip.com/moments/theme/poi-sema-seoul-museum-of-art-95224-exhibitions-990362/ |
| URL-038 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 0.95 | https://www.marieclairekorea.com/pinpage/2026/01/2026-exhibition/ |
| URL-039 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://ddoing.co.kr/ddoing_exhibition_schedule |
| URL-040 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://ko.wikipedia.org/wiki/2026년_대한민국의_영화_목록 |
| URL-041 | 문화·콘텐츠 | 문화·콘텐츠 | 문화·콘텐츠 | O | 문화·콘텐츠 1.00 | https://www.d-art.co.kr/news/articleView.html?idxno=4764 |
| URL-042 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.95 | https://bravo.etoday.co.kr/view/atc_view/13057 |
| URL-043 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.home-learn.co.kr/newsroom/news/A/2069 |
| URL-044 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.seouland.com/arti/society/society_general/2749.html |
| URL-045 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.95 | https://www.woowarhanclean.com/honeyinfotidy/?bmode=view&idx=7086792 |
| URL-046 | 생활·할 일 | 문화·콘텐츠 | 문화·콘텐츠 | X | 문화·콘텐츠 0.95 | https://brunch.co.kr/magazine/single-person |
| URL-047 | 생활·할 일 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.85 / 돈·재테크 0.15 | https://play.google.com/store/apps/details?id=com.lazyheroes.erfe&hl=ko |
| URL-048 | 생활·할 일 | 기타 | 기타 | X | 기타 0.80 | https://apps.apple.com/kr/app/id6745560834 |
| URL-049 | 생활·할 일 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.95 | https://brunch.co.kr/@ylangylang/116 |
| URL-050 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 0.95 | https://namu.wiki/w/자취/조언 |
| URL-051 | 생활·할 일 | 생활·할 일 | 생활·할 일 | O | 생활·할 일 1.00 | https://www.threads.com/@prozachi/post/DIuf95oNelD/ |
| URL-052 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.85 | https://www.apple.com/kr/mac-studio/ |
| URL-053 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 | https://m.compuzone.co.kr/product/product_list.htm?BigDivNo=2&MediumDivNo=1076 |
| URL-054 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://m.gsshop.com/search/searchSect.gs?tq=노트북가방&mseq=406355&ab=a |
| URL-055 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/search?q=노트북가방백팝 |
| URL-056 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 | https://dorishop.oopy.io/397d87ba-6a5e-4dd3-ba9f-601eed0eef18 |
| URL-057 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://shinsegaemall.ssg.com/search.ssg?query=명품노트북가방 |
| URL-058 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.95 | https://chicpap.com/blog/명품-노트북-가방-매일-들-수-있는-5가지-선택지 |
| URL-059 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/categories/328791 |
| URL-060 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 1.00 | https://www.coupang.com/np/search?q=실내텐트 |
| URL-061 | 쇼핑·제품 | 쇼핑·제품 | 쇼핑·제품 | O | 쇼핑·제품 0.90 | https://bodyitlove.com/캠핑-텐트/ |
| URL-062 | 쇼핑·제품 |  | 기타 | X |  | https://www.youtube.com/watch?v=mJTE8JBOkkw |
| URL-063 | 아이디어·영감 | 기타 | 기타 | X | 기타 0.30 | https://brunch.co.kr/@solobiznight |
| URL-064 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 1.00 | https://brunch.co.kr/@solobiznight/33 |
| URL-065 | 아이디어·영감 | 쇼핑·제품 | 쇼핑·제품 | X | 쇼핑·제품 0.95 | https://www.mobiinside.co.kr/2023/05/03/dana-smartstore-interview/ |
| URL-066 | 아이디어·영감 | 취업·커리어 | 취업·커리어 | X | 취업·커리어 0.85 | https://www.teamblind.com/kr/post/HHomJcfW |
| URL-067 | 아이디어·영감 | 돈·재테크 | 돈·재테크 | X | 돈·재테크 1.00 | https://bepractice01.com/ |
| URL-068 | 아이디어·영감 | 아이디어·영감 | 아이디어·영감 | O | 아이디어·영감 0.95 | https://underdogs.co.kr/contents/blogs/집에서-시작할-수-있는-창업-아이디어-20가지/ |
| URL-069 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 / 취업·커리어 0.15 | https://claireclass.com/ |
| URL-070 | 아이디어·영감 | 학습·지식 | 학습·지식 | X | 학습·지식 0.70 | https://brunch.co.kr/@e8362cab2f0c484/45 |
| URL-071 | 아이디어·영감 |  | 기타 | X |  | https://www.junsungki.com/magazine/post-detail.do?id=2744 |
| URL-072 | 아이디어·영감 | 기타 | 기타 | X | 기타 1.00 | https://apps.apple.com/kr/app/id1610260075 |
| URL-073 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.70 / 음식·맛집 0.30 | https://v.daum.net/v/7RSTWNtnjC |
| URL-074 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 | https://www.yeogi.com/content/dom-ko-busan-hotel-bx2-busan-haeundae-travel-course |
| URL-075 | 여행·장소 | 여행·장소 | 여행·장소 / 음식·맛집 | O | 여행·장소 0.80 / 음식·맛집 0.70 | https://triple.guide/articles/fd0068b5-08c8-4949-8ff4-874233fe2ff5 |
| URL-076 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 | https://studio24.kr/3077 |
| URL-077 | 여행·장소 | 음식·맛집 | 음식·맛집 | X | 음식·맛집 0.95 | https://uhflat.co.kr/badamaul/?bmode=view&idx=127804469 |
| URL-078 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.80 / 음식·맛집 0.60 | https://kr.trip.com/guide/theme/부산+혼자+여행.html |
| URL-079 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 1.00 | https://kr.trip.com/moments/poi-best-louis-hamilton-hotel-haeundae-21485227 |
| URL-080 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.95 | https://news.airbnb.com/ko/2018-coastal-side-listings/ |
| URL-081 | 여행·장소 | 여행·장소 | 여행·장소 | O | 여행·장소 0.90 | https://kr.trip.com/moments/theme/destination-gangwon-state-1185-thorough-guides-993136 |
| URL-082 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=전주+콩나물국밥 |
| URL-083 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://korean.visitkorea.or.kr/detail/rem_detail.do?cotid=a2bfb276-ce31-4dd3-8154-4866e408664b |
| URL-084 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://brunch.co.kr/@bakilhong66uhji/513 |
| URL-085 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://www.welfarehello.com/community/hometownNews/048b6105-e854-469d-ad91-cbdb86808393 |
| URL-086 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://guide.michelin.com/kr/ko/seoul-capital-area/kr-seoul/restaurant/gwanghwamun-gukbap |
| URL-087 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://diningcode.com/list.dc?keyword=20대&query=강남+삼겡살 |
| URL-088 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남구+삼겡살 |
| URL-089 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://www.diningcode.com/list.dc?query=강남역+삼겡살 |
| URL-090 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 0.95 | https://www.diningcode.com/list.dc?query=강남+삼겡살무한리필 |
| URL-091 | 음식·맛집 | 음식·맛집 | 음식·맛집 | O | 음식·맛집 1.00 | https://www.diningcode.com/list.dc?query=강남역+돼지고기+가성비 |
| URL-092 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@ahn-sujin/React-Query-useInfiniteQuery-사용해서-무한스크롤-구현하기 |
| URL-093 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 0.95 | https://community.linkareer.com/employment_data/4953814 |
| URL-094 | 취업·커리어 | 취업·커리어 | 취업·커리어 | O | 취업·커리어 0.95 | https://www.ssafy.com/ksp/servlet/swp.board.controller.SwpBoardServlet?p_process=select-board-view&p_menu_cd=M0204&p_tabseq=226509&p_seq=80&p_pageno=2 |
| URL-095 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://csr.samsung.com/ko/programViewSSWA.do |
| URL-096 | 취업·커리어 | 기타 | 기타 | X | 기타 0.30 | https://csr.samsung.com/ko/newsroom/news/ |
| URL-097 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@hyeseong-int/알고리즘-스터디-진행방식 |
| URL-098 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@cmh2806/코딩테스트-스타디-1주차-회고 |
| URL-099 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@0715yk/MEMO-알고리즘-잡스-후기 |
| URL-100 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.95 | https://velog.io/@rimgosu/99클럽-코딩테스트-스터디-4기-후기 |
| URL-101 | 취업·커리어 | 학습·지식 | 학습·지식 | X | 학습·지식 0.90 | https://velog.io/@jkseo50/Programmers-코딩테스트와-실무-역량-모두-잡는-알고리즘-스터디-후기 |
| URL-102 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.90 | https://www.youtube.com/watch?v=3aNtTUHJeDY |
| URL-103 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@1w2k/cs-과목-길잡이 |
| URL-104 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@jojehuni_9759/CS-전공지식-정리-네트워크-1-네트워크의-기초 |
| URL-105 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@dbwlgns98/네트워크-CS정리1탄 |
| URL-106 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@dbstjrwnekd/네트워크-정리1 |
| URL-107 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 | https://velog.io/@jincode93/CS-네트워크-요약-정리 |
| URL-108 | 학습·지식 | 학습·지식 | 학습·지식 / 취업·커리어 | O | 학습·지식 0.95 / 취업·커리어 0.70 | https://velog.io/@munhyojin7338/신입-백엔드-개발자-기술-면접-질문-정리 |
| URL-109 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 0.95 | https://velog.io/@kk1112k/백엔드-개발-기술면접-정리-Java-추가중 |
| URL-110 | 학습·지식 | 취업·커리어 | 취업·커리어 | X | 취업·커리어 1.00 | https://velog.io/@yukina1418/최근-면접을-다니면서-받았던-질문들 |
| URL-111 | 학습·지식 | 학습·지식 | 학습·지식 | O | 학습·지식 1.00 | https://velog.io/@namdaeun/요즘-프론트엔드-디자인-패턴-뭐가-정답일까 |
| URL-112 | 학습·지식 | 취업·커리어 | 취업·커리어 | X | 취업·커리어 1.00 | https://velog.io/@oojoo/백엔드-자기소개서면접-꿀Tip |

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
