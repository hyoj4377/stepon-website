# 부산 16개 구·군 SEO 최종 감사 및 최적화

점검일: 2026-10-20 (한국 시간). 기준 main: `ddb4737847aa4d1c9b9bd92377acaded1b8619e0`. 시작 시 로컬 HEAD와 origin/main이 일치했고 예상하지 못한 변경 사항이 없었습니다.

## 1. 부산 16개 구·군별 검사 결과

- 소스·빌드·로컬 접속 기준: 상세 16/16 정상. 부산 대표를 포함하면 17/17 정상.
- 공개 배포 HTTP 기준: 정상 확인 0, 사이트 오류 확정 0, 미확인 17. 실행 환경 프록시가 대상 서버에 도달하기 전에 CONNECT 403으로 차단. 사이트가 HTTP 403/404를 반환했다고 판정하지 않음.
- URL은 추정하지 않고 현재 지역 데이터의 부모·slug와 실제 생성 파일에서 확인.

| 구·군 | 파일 | 공개 URL | 소스·SEO·링크 | 공개 HTTP | 수정 |
|---|---|---|---|---|---|
| 중구 | `regions/busan/jung/index.html` | [jung/](https://hyoj4377.github.io/stepon-website/regions/busan/jung/) | 정상 | 미확인 | 없음 |
| 서구 | `regions/busan/seo/index.html` | [seo/](https://hyoj4377.github.io/stepon-website/regions/busan/seo/) | 정상 | 미확인 | 없음 |
| 동구 | `regions/busan/dong/index.html` | [dong/](https://hyoj4377.github.io/stepon-website/regions/busan/dong/) | 정상 | 미확인 | 없음 |
| 영도구 | `regions/busan/yeongdo/index.html` | [yeongdo/](https://hyoj4377.github.io/stepon-website/regions/busan/yeongdo/) | 정상 | 미확인 | 없음 |
| 부산진구 | `regions/busan/busanjin/index.html` | [busanjin/](https://hyoj4377.github.io/stepon-website/regions/busan/busanjin/) | 정상 | 미확인 | 없음 |
| 동래구 | `regions/busan/dongnae/index.html` | [dongnae/](https://hyoj4377.github.io/stepon-website/regions/busan/dongnae/) | 정상 | 미확인 | 없음 |
| 남구 | `regions/busan/nam/index.html` | [nam/](https://hyoj4377.github.io/stepon-website/regions/busan/nam/) | 정상 | 미확인 | 없음 |
| 북구 | `regions/busan/buk/index.html` | [buk/](https://hyoj4377.github.io/stepon-website/regions/busan/buk/) | 정상 | 미확인 | 없음 |
| 해운대구 | `regions/busan/haeundae/index.html` | [haeundae/](https://hyoj4377.github.io/stepon-website/regions/busan/haeundae/) | 정상 | 미확인 | 없음 |
| 사하구 | `regions/busan/saha/index.html` | [saha/](https://hyoj4377.github.io/stepon-website/regions/busan/saha/) | 정상 | 미확인 | 없음 |
| 금정구 | `regions/busan/geumjeong/index.html` | [geumjeong/](https://hyoj4377.github.io/stepon-website/regions/busan/geumjeong/) | 정상 | 미확인 | 없음 |
| 강서구 | `regions/busan/gangseo/index.html` | [gangseo/](https://hyoj4377.github.io/stepon-website/regions/busan/gangseo/) | 정상 | 미확인 | 없음 |
| 연제구 | `regions/busan/yeonje/index.html` | [yeonje/](https://hyoj4377.github.io/stepon-website/regions/busan/yeonje/) | 정상 | 미확인 | 없음 |
| 수영구 | `regions/busan/suyeong/index.html` | [suyeong/](https://hyoj4377.github.io/stepon-website/regions/busan/suyeong/) | 정상 | 미확인 | 없음 |
| 사상구 | `regions/busan/sasang/index.html` | [sasang/](https://hyoj4377.github.io/stepon-website/regions/busan/sasang/) | 정상 | 미확인 | 없음 |
| 기장군 | `regions/busan/gijang/index.html` | [gijang/](https://hyoj4377.github.io/stepon-website/regions/busan/gijang/) | 정상 | 미확인 | 없음 |

## 2. 부산 대표 페이지 검사

- 파일: `regions/busan/index.html`. URL: https://hyoj4377.github.io/stepon-website/regions/busan/
- 고유 title·description·H1과 실제 URL의 canonical·OG, 한국어 lang, viewport 정상. H1 1개.
- 15개 자치구와 1개 군을 구분하고 16개 카드 모두 실제 상세로 연결. 상세에서 대표와 전국 안내로 돌아가는 링크 정상.
- 전국 안내의 부산 링크와 메인 → 전국 → 부산 탐색 구조 확인. 기존 URL 변경 없음.
- 로컬 HTTP 200. 공개 HTTP·배포 완료는 미확인.

## 3. SEO 메타정보 및 구조화 데이터

- 17개 title·description·H1·canonical 모두 고유. title의 부산 지역명·과외·영어/수학·방문/화상 키워드를 확인. H1 각 1개이며 현재 원본과 생성 HTML 일치. 정상 메타는 변경하지 않음.
- og:title·og:description·og:url이 각 페이지 메타·canonical과 일치. `<html lang="ko">`, `width=device-width, initial-scale=1` 정상.
- robots 메타는 모두 없음: 기본 index/follow 상태이며 noindex/nofollow 삽입 없음. 실제 공개 서버의 X-Robots-Tag는 미확인.
- 상세 16개: BreadcrumbList·Service·FAQPage 각 1개, 충돌·중복 없음. breadcrumb 부모는 부산 대표, 서비스 지역은 부산광역시의 실제 구·군, URL은 해당 canonical과 일치.
- 대표: BreadcrumbList·FAQPage 사용, Service는 미사용. Service는 필수 태그가 아니므로 이를 오류로 간주해 추가하지 않음.
- 화면의 FAQ(대표 4개, 상세 각 5개)와 JSON-LD 질문·답변 일치. 임의 주소·지점·가격·평점·후기 없음. 구조화 데이터가 검색 결과 특수 노출을 보장하지 않음.

## 4. 콘텐츠 중복 및 품질

- 부산 상호 120쌍과 부산–서울 400쌍, 총 520쌍을 비교. 구·군/동네 명칭을 정규화한 5글자 shingle Jaccard로 전체를 선별하고 상위 10쌍은 SequenceMatcher로 추가 확인. 수치는 편집 보조 지표이며 검색엔진의 품질/중복 판정 점수가 아님.
- 공통 구조·소개 문형·학년/과목 카드·수업 방식 설명의 반복 비중은 높음. 상위 본문 비교 예시는 수영–사상 Jaccard 0.5455, SequenceMatcher 0.7811. 반복이 전혀 없거나 완전히 지역 고유 콘텐츠라고 평가하지 않음.
- 각 상세의 핵심 학습 정보는 서로 다른 주제 16개, 각 3개 문단(335–397자)으로 구성. 오답·복습·독해 등 인접 주제는 있으나 방법·질문·학습 순서가 구분됨. 각 지역의 생활권 및 실제 상담 범위도 별도로 표시.
- FAQ 5개 중 3개는 수업 형태·학년/과목·상담 준비에 관한 공통 답변(지역명 정규화 기준). 나머지는 지역 범위와 개별 학습 주제. 정확해야 하는 공통 서비스 안내를 중복 제거 목적으로 억지로 바꾸지 않음.
- 심각한 페이지 전체 치환 복제나 허위 성과를 확인하지 못해 본문 재작성 없음. 지역 이름만으로 학생 수준·학교 난이도를 단정하거나 학교 실적을 만들지 않음.
- 지역 맞춤의 깊이는 현재 동네 안내+학습 주제 수준으로 제한적. 실제 지역 상담 질문이나 검증 가능한 자료가 확보되면 기존 분량을 늘리기보다 그 자료로 점진적으로 보완 권장. 외부 근거 없이 지역 교육 특성을 추가하지 않음.

| 구·군 | 현재 핵심 학습 주제 |
|---|---|
| 중구 | 하루 복습 시간을 작게 나누는 방법 |
| 서구 | 영어·국어 독해에서 답의 근거를 찾는 연습 |
| 동구 | 실행할 수 있는 주간 학습 계획 세우기 |
| 영도구 | 설명을 들은 문제를 스스로 다시 푸는 방법 |
| 부산진구 | 외운 영어를 읽기와 쓰기에 사용하는 점검법 |
| 동래구 | 개념을 아는데 수학 문제를 시작하지 못할 때 |
| 남구 | 영어·수학 서술형에서 과정과 조건을 확인하기 |
| 북구 | 기초 공백이 있을 때 복습 범위를 정하는 방법 |
| 해운대구 | 학교 시험과 모의고사 오답을 나란히 보는 방법 |
| 사하구 | 계산 실수와 개념 부족을 구분하는 수학 점검 |
| 금정구 | 학부모가 자기주도학습을 점검할 때 할 질문 |
| 강서구 | 방문·화상수업을 고를 때 복습까지 함께 계획하기 |
| 연제구 | 학교 평가 일정을 한 계획에 정리하는 방법 |
| 수영구 | 수학 풀이 기록을 복습 자료로 사용하는 방법 |
| 사상구 | 오답 기록을 쌓기보다 다시 사용하는 방법 |
| 기장군 | 예비중·예비고가 진학 전에 확인할 영어·수학 |

## 5. 지역 정보 정확성

- 데이터와 본문에서 서울 등 이전 지역의 복사 잔재, 다른 부산 구·군의 동네 혼입 후보, 특정 학교명·수치 성과 주장을 점검. 오류로 확정할 후보는 발견하지 못함.
- 부산 중구·동구·서구·북구·남구·강서구는 title·도입부·구조화 데이터에서 부산 지역임을 명시. 강서구의 서울 언급은 “서울 강서구가 아닌 부산광역시 강서구”라는 구분 문구로 복사 오류가 아님.
- 기장군은 자치구가 아닌 군으로 명시. 기장읍·정관읍·일광읍·장안읍·철마면은 읍·면 명칭으로 안내. 나머지 일부 동 이름은 가 단위를 합친 통상 일대 명칭이며 세부 행정동 경계로 단정하지 않음.
- 부산시 공식 사이트에 대한 실제 요청도 프록시에서 차단. 최신 구청/군청 공식 행정구역 자료를 통한 전 동네 관할 재검증은 **미확인**. 외부 검증을 완료한 사실로 확정하지 않았고 근거 없이 지역명은 수정하지 않음.
- 수업 형태와 부산 16개 구·군 상담 범위는 운영자가 이전 대화에서 확인한 기준. 이는 특정 교사 상주나 모든 일정의 즉시 배정, 해당 동네 학교 담당 이력을 의미하지 않음.

## 6. 사이트맵·내부 링크·robots

- 기존 단일 `sitemap.xml` XML 파싱 정상. 전체 고유 URL 56개, 부산 대표+상세 **17개** 각 1회, 서울 상세 **25개** 모두 유지. 별도 부산 사이트맵 생성 없음.
- 각 부산 canonical과 사이트맵 URL이 정확히 일치하고 `/stepon-website/` 프로젝트 경로 유지.
- 대표 → 상세 16개, 상세 → 부산·전국·홈·학년·과목·방문/화상·상담의 상대 경로와 앵커를 검사. 로컬 404·깨진 링크 없음.
- 별도 `hyoj4377/hyoj4377.github.io` 루트 저장소의 최신 main 소스를 읽기 전용으로 확인: `39a5906f290eb68379126225cb6094ac5285095d`. `User-agent: *`, `Allow: /`, `Sitemap: https://hyoj4377.github.io/stepon-website/sitemap.xml`. 다른 저장소 수정 없음.
- 실제 `https://hyoj4377.github.io/robots.txt`와 사이트맵 HTTP 응답은 미확인. 프로젝트 경로의 robots 파일로 해결된 것처럼 보고하지 않음.

## 7. 모바일·기능 회귀 테스트

- 부산 상세: 16×1440/768/390/320px = 64개 조합. 헤더·메뉴·이미지 로딩·FAQ·전화·상하단 CTA·카카오·무료체험·모바일 펼침 메뉴·가로 넘침 검사 통과.
- 부산 대표: 같은 4개 폭, 로컬 HTTP 200, 카드 16개·이미지·FAQ·상담 메뉴·Tab/Enter 탐색과 기장군 왕복 링크 확인.
- 서울 25개: 같은 4개 폭 총 100개 조합에서 링크·메타·이미지·CTA·전화·반응형 회귀 검사 통과.
- 메인: PC/모바일에서 원본 후기 8개와 슬라이더 이동, 전국 안내 링크, 상담 새 탭의 연결 주소 확인. 외부 대상은 테스트용 응답으로 차단하여 실제 폼 로딩·접수 성공을 주장하지 않음.
- 대표 텍스트/버튼 7종의 대비는 최소 약 5.90:1, 관측 로컬 CLS 최대 0. 이는 전 요소 접근성 인증·운영 서버 Core Web Vitals 보장이 아님.
- 전화 표시 `010-4377-6964`, `tel:01043776964`; 카카오 `http://pf.kakao.com/_eMxbPX`; 상담/무료체험 `https://sscoaching.co.kr/ssc/marketing/sangsangLanding2?code=3260631_I` 유지. 실제 통화·카카오 대화·폼 접수는 미확인.
- 전체 SEO 빌드와 `--check`: 통과(공개 서브 55개, 사이트맵 56개 URL). 전체 자동 테스트 **41개 통과(326.653초)**.

## 8. 발견한 오류와 실제 수정

- 확정된 페이지·메타·구조화 데이터·사이트맵·링크·반응형 오류: **0건**. 수정한 홈페이지 오류: **0건**.
- 외부 프록시 차단은 환경 제약이며 실제 사이트 오류에 포함하지 않음.
- 정상 페이지를 불필요하게 재작성하지 않았으며 원본 데이터·템플릿·생성 HTML·사이트맵·상담 주소·메인·서울 콘텐츠 모두 변경 없음.
- 변경 파일은 이 감사 보고서 `docs/부산-16개-구군-SEO-최종감사.md` 하나.

## 9. 수정하지 못한 항목과 이유

| 항목 | 상태·이유 | 추가 확인 |
|---|---|---|
| 공개 17개 페이지의 HTTP 200·리디렉션·배포 완료 | 미확인: CONNECT 프록시 403 | 일반 브라우저/외부 네트워크에서 재확인 |
| 공개 robots·사이트맵·X-Robots-Tag | 미확인: 동일한 접근 제한 | 루트 URL·HTTP 헤더 확인 |
| 최신 공식 행정동·법정동 관할 | 미확인: 공식 사이트 접근 차단 | 부산시·각 구청/기장군청 공식 자료와 대조 |
| 네이버 수집·색인 | 미확인: 서치어드바이저 접근 없음 | 사이트맵 처리·수집 현황·URL 재수집 확인 |
| 구글 색인·선택 canonical | 미확인: 서치콘솔 접근 없음 | URL 검사·페이지 색인·사이트맵 보고서 확인 |
| 실제 상담 완료 | 미확인: 로컬 검증은 링크/동작까지만 | 스마트폰 전화·카카오·무료체험 폼 접수 점검 |

검색엔진 등록 전에는 위 공개 접근·robots·사이트맵을 운영 환경에서 확인하고 네이버 서치어드바이저/구글 서치콘솔에 기존 단일 사이트맵을 제출·확인하세요. 이미 등록됐다면 불필요한 새 사이트/부산 전용 사이트맵을 만들지 않고 기존 등록에서 상태를 확인합니다.

## 10. GitHub 커밋 및 푸시 결과

- 감사 기준 커밋: `ddb4737847aa4d1c9b9bd92377acaded1b8619e0`. origin/main과 일치 확인.
- 예상하지 못한 원격 변경이 발견되면 덮어쓰지 않고 보고하는 원칙 적용.
- 감사 보고서 최초 커밋: `1f6fbe62b245664adb1917d1edeafd0ecfe3e5dd`. `git push origin HEAD:main` 성공 후 `git ls-remote origin refs/heads/main`에서 같은 SHA를 확인함. 이 푸시 결과 기록은 후속 문서 커밋으로 저장.
- Git 푸시 완료와 GitHub Pages 배포 완료, 네이버/구글 색인 완료는 서로 다른 상태이며 공개 배포·색인은 미확인.
