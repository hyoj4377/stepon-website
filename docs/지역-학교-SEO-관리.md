# 스텝온과외 지역·학교 SEO 관리

기존 메인 홈페이지(index.html)는 변경하지 않았습니다. 전국 안내와 수업 방식·학년·과목 안내는 별도의 정적 HTML입니다. JavaScript 없이 본문·사진·제목·상담 링크를 읽을 수 있습니다. 설치나 유료 API가 필요하지 않습니다.

## 오늘 공개 대상으로 만든 페이지

기본 주소: https://hyoj4377.github.io/stepon-website/

| 안내 | 상대 URL |
| --- | --- |
| 전국 17개 시·도 상담 안내 | regions/ |
| 방문과외 | guides/visit/ |
| 화상과외 | guides/online/ |
| 초등학생 | guides/elementary/ |
| 중학생 | guides/middle/ |
| 고등학생 | guides/high/ |
| 영어 | guides/english/ |
| 수학 | guides/math/ |

예: https://hyoj4377.github.io/stepon-website/guides/english/

사이트맵은 sitemap.xml에 있으며 현재 메인 포함 9개 URL을 담습니다. 실제 운영이 확인되지 않은 학교·동네별 URL이나 외부 상담 주소, 이미지 주소는 넣지 않습니다. 각 페이지의 탐색 메뉴와 관련 안내 카드가 서로 연결됩니다. 기존 메인 화면은 유지했으므로 새 안내의 진입 URL은 regions/이며 사이트맵에도 등록되어 있습니다.

## 17개 시·도 초안

서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주를 준비했습니다. 공식 행정 명칭은 데이터에 구분해 저장합니다.

각 지역의 title·description·기본 안내 초안·보완 주제를 `data/seo/regions.json`에 저장했습니다. 현재는 **모두 draft이며 지역별 HTML은 공개하지 않습니다.** 지역 고유 내용과 검증 가능한 출처, 실제 상담·운영 조건이 아직 부족하기 때문입니다. 허브의 지역 카드에는 준비 중으로 표시하고 존재하지 않는 페이지로 링크하지 않습니다.

검토용 초안 HTML은 저장소 밖에 생성할 수 있습니다.

```sh
python3 scripts/build_seo.py --preview-drafts /tmp/stepon-region-review
```

17개의 기본 안내 초안을 생성합니다. noindex,nofollow가 적용되고 사이트맵에 들어가지 않습니다. 생성기는 저장소 내부에 초안 HTML을 출력하는 것을 거부합니다. 생성된 검토용 파일을 GitHub Pages 배포 폴더로 복사하지 마세요. 이 초안은 확인되지 않은 지역 정보를 채우기 위한 편집 자료입니다.

## 내용을 수정할 곳

| 파일 | 역할 |
| --- | --- |
| data/seo/site.json | 신규 안내 페이지의 브랜드·상담·카카오·블로그·전화·기본 URL |
| data/seo/guides.json | 방문·화상·초등·중등·고등·영어·수학 안내의 문구와 FAQ |
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

school 객체에는 official_name, official_code, non_affiliation_notice: true를 기록합니다. sources에 type: official_school인 확인된 공식 학교 출처가 필요합니다. learning 객체에는 grade(elementary / middle / high)와 subject(english / math)를 넣습니다. 여러 학년·과목 페이지를 자동 조합해 게시하지 말고 각각 학생에게 도움이 되는 고유 안내를 검토하세요.

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

현재 검증 결과: 생성기 재실행의 동일 결과, 사이트맵 9개 URL, 모든 내부 경로·앵커, 17개 초안 제외, 학교 게시 차단, 지역명만 바꾼 중복 차단, 계층 URL 확장, JavaScript 없는 실제 본문 표시를 확인했습니다. 브라우저에서는 신규 8개 페이지를 1440·768·390·320px에서 확인하고 공식 로고·사진·모바일 상담 버튼·링크·가로 넘침을 검사했습니다. 기존 메인 파일의 체크섬도 유지했습니다.

공개 배포 후 regions/ 및 sitemap.xml을 열어 확인하고 네이버 서치어드바이저·구글 서치 콘솔에 사이트맵을 제출하세요. sitemap.xml에 실제 URL이 있다고 해서 즉시 색인되거나 검색 순위가 보장되는 것은 아닙니다.
