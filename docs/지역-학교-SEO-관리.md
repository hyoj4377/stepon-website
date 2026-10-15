# 스텝온과외 지역·학교 SEO 관리

기존 메인 홈페이지(index.html)는 변경하지 않았습니다. 전국 안내와 수업 방식·학년·과목 안내는 별도의 정적 HTML입니다. JavaScript 없이 본문·사진·제목·상담 링크를 읽을 수 있습니다. 설치나 유료 API가 필요하지 않습니다.

## 오늘 공개 대상으로 만든 페이지

기본 주소: https://hyoj4377.github.io/stepon-website/

| 안내 | 상대 URL |
| --- | --- |
| 전국 17개 시·도 상담 안내 | regions/ |
| 서울 과외 상세 안내 | regions/seoul/ |
| 강남구 과외 상세 안내 | regions/seoul/gangnam/ |
| 강동구 과외 상세 안내 | regions/seoul/gangdong/ |
| 강북구 과외 상세 안내 | regions/seoul/gangbuk/ |
| 서울 강서구 과외 상세 안내 | regions/seoul/gangseo/ |
| 서울 관악구 과외 상세 안내 | regions/seoul/gwanak/ |
| 방문과외 | guides/visit/ |
| 화상과외 | guides/online/ |
| 초등학생 | guides/elementary/ |
| 중학생 | guides/middle/ |
| 고등학생 | guides/high/ |
| 영어 | guides/english/ |
| 수학 | guides/math/ |
| 국어 | guides/korean/ |
| 사회 | guides/social/ |
| 과학 | guides/science/ |
| 수행평가 관리 | guides/performance-assessment/ |

예: https://hyoj4377.github.io/stepon-website/guides/english/

사이트맵은 sitemap.xml에 있으며 현재 메인 포함 19개 URL을 담습니다. 실제 운영이 확인되지 않은 학교·동네별 URL이나 외부 상담 주소, 이미지 주소는 넣지 않습니다. 각 페이지의 탐색 메뉴와 관련 안내 카드가 서로 연결됩니다. 기존 메인 화면은 유지했으므로 새 안내의 진입 URL은 regions/이며 사이트맵에도 등록되어 있습니다.

## 17개 시·도 초안

서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주를 준비했습니다. 공식 행정 명칭은 데이터에 구분해 저장합니다.

각 지역의 title·description·기본 안내 초안·보완 주제를 `data/seo/regions.json`에 저장했습니다. 서울은 운영자가 서울 25개 자치구 서비스 범위를 확인해 공개했습니다. 나머지 **16개 시·도는 draft이며 개별 HTML을 공개하지 않습니다.** 지역 고유 내용과 검증 가능한 출처, 실제 상담·운영 조건이 아직 부족하기 때문입니다. 허브의 지역 카드에는 준비 중으로 표시하고 존재하지 않는 페이지로 링크하지 않습니다.

검토용 초안 HTML은 저장소 밖에 생성할 수 있습니다.

```sh
python3 scripts/build_seo.py --preview-drafts /tmp/stepon-region-review
```

현재 공개하지 않은 16개 지역의 기본 안내 초안을 생성합니다. noindex,nofollow가 적용되고 사이트맵에 들어가지 않습니다. 생성기는 저장소 내부에 초안 HTML을 출력하는 것을 거부합니다. 생성된 검토용 파일을 GitHub Pages 배포 폴더로 복사하지 마세요. 이 초안은 확인되지 않은 지역 정보를 채우기 위한 편집 자료입니다.

## 내용을 수정할 곳

| 파일 | 역할 |
| --- | --- |
| data/seo/site.json | 신규 안내 페이지의 브랜드·상담·카카오·블로그·전화·기본 URL |
| data/seo/guides.json | 방문·화상·학년·영어·수학·국어·사회·과학·수행평가 안내의 문구와 FAQ |
| data/seo/regions.json | 지역·학교 계층, 초안·게시 상태, 공식 출처, 검토 기록 |
| scripts/build_seo.py | HTML·내부 링크·메타데이터·사이트맵 생성 및 게시 조건 검사 |
| data/seo/generated.json | 생성된 파일의 소유권과 체크섬 목록. 직접 수정하지 않음 |
| tests/test_seo.py | 경로·게시 조건·중복·사이트맵·정적 콘텐츠 검증 |
| .github/workflows/seo-check.yml | push·PR에서 생성 결과와 테스트 검사 |

새 안내 페이지의 설정은 site.json을 사용합니다. 기존 메인 홈페이지의 설정은 이전과 동일하게 index.html 내부 window.STEPON_CONFIG입니다. 기존 메인 링크를 변경하지 않기 위해 두 영역을 독립적으로 관리합니다.

## 데이터 변경 후 갱신하기

저장소 폴더에서 다음 명령을 실행하세요.

```sh
python3 scripts/build_seo.py
python3 scripts/build_seo.py --check
python3 -m unittest discover -s tests -v
```

첫 명령이 모든 공개 안내 HTML과 sitemap.xml을 갱신합니다. 나머지는 갱신 누락과 잘못된 링크를 검사합니다. 데이터와 생성 결과를 함께 커밋·push하세요. GitHub Pages는 main 루트의 실제 HTML을 배포합니다. `.nojekyll`로 별도 Jekyll 처리를 생략합니다. Actions는 검사만 하며 콘텐츠를 임의로 게시하거나 수정하지 않습니다.

생성 결과를 직접 고치지 마세요. 데이터에서 바꿔야 다음 생성에도 유지됩니다. 생성기는 자신이 이전에 생성한 파일만 관리하고, 수동으로 바뀐 파일을 임의로 삭제하지 않습니다. index.html이나 기존 업로드 파일은 수정하지 않습니다.

## 지역 → 동네 → 학교 → 학년·과목 확장

지역 데이터의 kind와 parent_id로 연결합니다.

- province: 시·도. parent_id는 null
- district: 시·군·구. 부모는 province
- neighborhood: 읍·면·동. 부모는 district
- school: 학교. 부모는 neighborhood
- learning: 학교별 학년·과목 안내. 부모는 school

모든 레코드는 고유한 id·slug·name·official_name을 가집니다. slug는 소문자 영문·숫자·하이픈을 사용합니다. 실제 명칭은 name과 official_name에 넣고, URL에는 안정적인 slug를 사용하세요. 같은 부모 아래 중복 slug는 허용하지 않습니다.

예를 들어 향후 검증한 데이터를 입력하면 다음처럼 구성할 수 있습니다. 아래는 **경로 구조 예시이며 현재 생성·게시한 페이지가 아닙니다.**

```
regions/daegu/donggu/bangchon/{verified-school-slug}/middle-math/
```

학교를 추가하기 전에 공식 학교명, 공식 학교 코드, 소재지의 실제 상위 동네를 확인하세요. 학교알리미(https://www.schoolinfo.go.kr/) 또는 공식 교육기관·학교 자료를 참고하고 실제로 확인한 문서의 정확한 URL과 확인일을 기록하세요. API 키나 개인정보는 이 데이터에 넣지 않습니다.

school 객체에는 official_name, official_code, non_affiliation_notice: true를 기록합니다. sources에 type: official_school인 확인된 공식 학교 출처가 필요합니다. learning 객체에는 grade(elementary / middle / high)와 subject(english / math / korean / social / science)를 넣습니다. 여러 학년·과목 페이지를 자동 조합해 게시하지 말고 각각 학생에게 도움이 되는 고유 안내를 검토하세요.

## 지역·학교 게시 조건

status를 published로 바꾸는 것만으로 게시되지 않습니다. 다음 조건을 모두 확인해야 합니다.

1. title·description·intro가 완성되어 있어야 합니다.
2. sections에 3개 이상 고유 안내가 있어야 하고, 각 항목에 heading·paragraphs·local_relevance를 기록합니다. 본문 분량 검사는 최소 조건이며 글자 수만 채우는 것을 권장하지 않습니다.
3. sources의 공식 출처에 url(HTTPS), label, checked_on(YYYY-MM-DD), verified: true를 기록합니다. verified는 실제로 사람이 자료를 확인한 뒤에만 지정하세요. 생성기가 URL 내용의 진실성을 자동 보증하는 것은 아닙니다.
4. review.approved: true와 review.reviewed_on을 실제 검토 후 기록합니다.
5. 하위 지역은 상위 지역 페이지가 먼저 게시되어야 합니다.
6. 학교 페이지에는 확인된 공식 학교 정보와 비제휴 안내가 필요합니다. 특정 학교의 전담 강사·수업 실적·제휴를 임의로 쓰지 마세요.
7. 지역명만 바꾼 동일·매우 유사한 본문은 생성기가 거부합니다. 기계적 유사도 검사 외에 편집자가 실제 유용성을 확인해야 합니다.

학교별 학습 내용에 필요한 학교 일정·범위는 공식 자료나 학생이 제공한 자료로 확인하세요. 성적·합격·배정·방문 가능 지역을 확인 없이 보장하지 마세요. 지역별 페이지는 검색량이나 순위를 보장하는 도구가 아닙니다. 운영할 수 있는 지역과 충분한 정보를 가진 주제부터 단계적으로 게시하세요.

## 검증과 미리보기

```sh
python3 server.py --port 3000
```

현재 서버는 main과 신규 안내·sitemap.xml만 제공하고, 없는 페이지에는 실제 404를 반환합니다. `/stepon-website/` 접두사와 하위 폴더 URL도 검증했습니다. 예시 로컬 주소는 http://localhost:3000/regions/입니다. 로컬 주소는 공개 공유용 주소가 아닙니다.

현재 검증 결과: 생성기 재실행의 동일 결과, 사이트맵 19개 URL, 모든 내부 경로·앵커, 16개 초안 제외, 학교 게시 차단, 지역명만 바꾼 중복 차단, 계층 URL 확장, JavaScript 없는 실제 본문 표시를 확인했습니다. 브라우저에서는 신규 안내 페이지를 1440·768·390·320px에서 확인하고 공식 로고·사진·모바일 상담 버튼·링크·가로 넘침을 검사했습니다. 기존 메인 파일의 체크섬도 유지했습니다.

공개 배포 후 regions/ 및 sitemap.xml을 열어 확인하고 네이버 서치어드바이저·구글 서치 콘솔에 사이트맵을 제출하세요. sitemap.xml에 실제 URL이 있다고 해서 즉시 색인되거나 검색 순위가 보장되는 것은 아닙니다.

## 서울 상세 안내

서울 페이지는 regions/seoul/에 게시하며 서울 카드에서도 연결됩니다. 제목·본문·25개 자치구 목록·FAQ는 regions.json의 seoul 레코드에서 관리합니다. city-guide 템플릿은 학년·과목·수업 방식 카드, 자치구 그리드, 상하단 상담과 BreadcrumbList·FAQPage를 생성합니다. 화면 FAQ와 구조화 데이터는 동일한 데이터를 사용하며 리치 스니펫 노출을 보장하지 않습니다.

service_confirmation에는 현재 운영자가 직접 제공한 지역 서비스 범위와 확인일, region_id를 기록했습니다. 이 방식은 province·district의 운영 정보에만 적용되며 학교의 공식 정보 검증 조건을 대신할 수 없습니다. 서울시 공식 사이트는 이 환경에서 접속이 제한되어 검증한 외부 출처로 기록하지 않았습니다.

자치구 그리드는 현재 링크 없는 안내입니다. 향후 district 레코드를 기존 게시 조건에 따라 검토·공개한 후 해당 자치구의 page_id로 연결하면 실제로 게시된 자식 페이지만 링크됩니다. 존재하지 않는 구별 상세 URL은 만들지 않습니다.

## 강남구 상세 안내

지역 데이터의 seoul-gangnam은 kind: district, parent_id: seoul, slug: gangnam으로 관리합니다. 강남구 전 지역 서비스 범위는 운영자가 직접 제공한 정보를 service_confirmation에 기록했습니다. district-guide 템플릿이 학년·5개 과목·수업 방식별 카드, 동네 그리드, FAQ 6개와 상하단 상담을 생성합니다.

서울 페이지의 강남구 카드에서 gangnam/으로 이동하고, 강남구에서는 서울·전국 안내로 돌아갈 수 있습니다. 주요 12개 동네는 안내 그리드이며 존재하지 않는 동네 페이지로 연결하지 않습니다. 향후 공식 정보와 고유 콘텐츠가 확보된 neighborhood 레코드를 게시하고 해당 동네의 page_id로 연결하세요.

BreadcrumbList는 홈→전국→서울→강남구의 4단계입니다. Service는 실제 안내 범위·학년·과목·기존 전화번호만 포함하고, 지점 주소·수업료·후기·성과 수치는 넣지 않았습니다. FAQ 데이터와 화면 내용은 같은 원본을 사용하며 검색 노출이나 리치 결과를 보장하지 않습니다.

## 강동구와 기존 페이지 점검 (2026-10-14)

서울·강남구 HTML은 저장소 main에 존재합니다. 로컬 서버에서는 GitHub Pages 접두사 /stepon-website/를 포함한 URL로 HTTP 200과 내부 링크를 확인했습니다. canonical과 사이트맵, HTML에 noindex가 없는 것을 검사했으며 저장소에는 robots.txt가 없습니다. 공개 GitHub Pages 주소는 네트워크 프록시가 CONNECT 403으로 차단해 실제 배포 응답과 X-Robots-Tag, 도메인 루트 robots.txt는 확인하지 못했습니다. 이는 사이트가 403을 반환했다는 의미가 아닙니다. 네이버 서치어드바이저·구글 서치 콘솔의 색인 도구에도 접근할 수 없어 실제 색인은 운영자가 확인해야 합니다.

강동구 데이터는 seoul-gangdong 레코드입니다. 기존 district-guide 템플릿의 지역명·서비스·탐색 라벨을 데이터 기반으로 바꿨고, Gangnam HTML은 동일하게 유지했습니다. 강동구는 상담 준비와 수업 후 복습 흐름을 중심으로 독립 콘텐츠를 작성했으며 8개 동네 그리드에는 별도 상세 링크가 없습니다. 재빌드하면 서울 카드·강동구 페이지·사이트맵이 함께 유지됩니다.

배포 후 GitHub 저장소 Actions에서 Pages 작업 완료를 확인하고 서울·강남구·강동구 공개 URL을 열어 주세요. 네이버 서치어드바이저에서 수집·색인 현황과 사이트맵을 확인하고, 구글 서치 콘솔 URL 검사에서 색인·선택된 canonical을 확인하세요. 색인 완료까지 기다려야 다음 페이지를 제작할 수 있는 것은 아닙니다.

## 강북구 상세 안내

seoul-gangbuk 데이터로 강북구 전용 본문과 미아·수유·번·우이동 4개 안내를 관리합니다. neighborhood_columns: 2로 4개 동네를 균형 있는 2열로 표시합니다. 기존 강남·강동구는 기본 열 수를 유지합니다. 학습 단계와 기초 점검 중심의 고유 본문, FAQ 6개, 실제 Service와 BreadcrumbList를 생성하며 서울의 강북구 카드에서 연결합니다. 없는 동네 상세 페이지는 생성하지 않습니다.

루트 저장소 hyoj4377.github.io의 robots.txt는 User-agent: * / Allow: /이며 스텝온 사이트맵을 지정합니다. 프로젝트 저장소에 별도의 robots 파일을 추가하지 않았습니다. 공개 HTTP와 검색엔진 색인은 네트워크 제한 시 원격 push 확인과 구분하여 운영자가 직접 확인해야 합니다.

## 서울 강서구 상세 안내

seoul-gangseo 데이터로 기초 보완·학교 진도·오답·내신 준비를 연결하는 강서구 고유 본문을 작성했습니다. 기존 district-guide를 사용하며 생성기 템플릿을 별도로 복제하지 않았습니다. 지역 그리드에는 화곡·마곡·등촌·가양·염창·방화·공항·발산 안내를 포함하고 존재하지 않는 동네별 링크는 만들지 않습니다. 발산 지역 검색은 상담에서 실제 동네·주소를 확인하도록 안내합니다.

서울 강서구임을 title·description·Service의 areaServed에서 구분합니다. 첫 화면과 FAQ에 서비스 범위·대상·과목·선택 기준·상담 방법을 명확하게 표현했습니다. FAQ와 구조화 데이터는 같은 원본을 사용하며 GEO·AEO나 검색 결과 노출을 보장하지 않습니다. 기존 루트 robots 정책은 변경하지 않습니다.

## 관악구 상세 안내

seoul-gwanak 데이터로 수업 중 질문과 혼자 복습하는 과정을 연결하는 관악구 고유 본문을 관리합니다. 봉천·신림·남현동과 서울대입구역·낙성대역 생활권을 구분해 안내하며 역명을 지점이나 사무실 위치로 표현하지 않습니다. 역명은 상담 시 실제 거주 동네·주소를 설명하는 참고입니다. 기존 district-guide를 사용하므로 템플릿을 복제하지 않았습니다.

학년·5개 과목·방문/화상 안내의 실제 링크, FAQ 6개, 상하단 상담·전화와 동일한 내용의 구조화 데이터를 생성합니다. 서울 카드와 사이트맵에 연결하고, 존재하지 않는 동네 URL은 게시하지 않습니다. 기존 공개 robots 정책은 변경하지 않습니다.
