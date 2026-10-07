# 스텝온과외 · STEP ON

초등·중등·고등 방문수업 / 화상수업을 소개하는 반응형 홈페이지입니다. **index.html 하나에 디자인과 JavaScript를 모두 포함**했습니다. 외부 CSS·JS·폰트를 불러오지 않아 HTML만 열어도 디자인과 기능이 작동합니다. 설치나 빌드는 필요하지 않습니다.

## 미리 확인하기

파일을 내려받아 **index.html을 더블 클릭**하면 바로 열립니다. 클라우드에서는 다음 명령으로 3000번 포트 서버를 실행하고 사용 중인 웹 미리보기를 여세요.

```sh
cd /workspace/stepon-website
python3 server.py --port 3000
```

터미널 연결이 끝나도 서버를 유지하려면 아래 명령을 사용하세요. 이미 3000번 포트에서 실행 중이면 중복 실행하지 마세요.

```sh
nohup python3 -u server.py --port 3000 > /tmp/stepon-preview.log 2>&1 < /dev/null &
```

로컬 PC에서 서버를 실행했다면 브라우저에서 http://localhost:3000을 엽니다. 이 주소는 다른 사람에게 공유하는 공개 주소가 아닙니다.

## 문구·상담 링크·연락처 수정

**index.html**을 편집기로 열고 찾기(Ctrl+F / Cmd+F)로 **window.STEPON_CONFIG**를 검색하세요. 이곳이 모든 자주 바꾸는 내용을 모아 둔 설정 영역입니다. 따옴표 안의 글자만 바꾸고 저장한 다음 브라우저를 새로고침하세요. 따옴표·쉼표·대괄호는 유지하세요. 줄바꿈은 `\n`으로 입력합니다.

| 수정할 내용 | 설정 영역에서 찾을 이름 |
| --- | --- |
| 브랜드명 / 슬로건 | brand / slogan |
| 모든 무료 시강·상담 버튼 주소 | **consultationUrl** |
| 카카오채널 / 블로그 주소 | kakaoUrl / blogUrl |
| 전화번호 / 이메일 | phone / email |
| 대표명 / 사업자등록번호 / 주소 | business 안의 항목 |
| 첫 화면 제목 / 설명 | hero |
| 브랜드 소개 | introduction |
| 초등·중등·고등 안내 | levels |
| 학습 관리 특징 | management |
| 실제 수강 후기 | reviews |
| 무료 시강 설명 / 안내사항 | trial |

`consultationUrl: 'https://실제-상담주소',`로 바꾸면 상단·본문·모바일 하단의 모든 상담 버튼에 적용됩니다. 주소는 https:// 또는 http://로 시작해야 하며, 가능한 경우 https://를 사용하세요. 빈 상담 주소는 준비 중 안내로 이동합니다. 카카오채널과 블로그도 주소를 넣으면 새 창으로 열립니다. 빈 연락처는 표시하지 않습니다.

후기는 `reviews: []`를 아래 형식으로 바꾸세요. 실제 후기만 사용하고 게시 동의·개인정보를 확인하세요. 여러 개는 쉼표로 구분합니다.

```js
reviews: [
  { text: '사용 동의를 받은 실제 후기 원문', author: '게시 동의를 받은 작성자 표기', detail: '학년 · 과목' },
],
```

후기가 없으면 준비 중 카드만 표시됩니다. 가상의 성적·합격 사례는 포함하지 않았습니다. 설정 문구에 HTML 태그나 `</script>`를 넣지 마세요.

## 디자인·구조 수정

index.html 위쪽의 `<style id="stepon-styles">`가 디자인 영역입니다. 바로 아래 :root의 --navy / --gold / --paper로 색상을 조정합니다. 중간의 header·main·footer가 홈페이지 구성입니다. 방문수업·화상수업 설명, 상담 절차, 검색·공유용 제목도 이 파일에서 해당 문장을 찾아 수정하세요. 아래쪽의 stepon-app 영역은 기능 코드이므로 일반적인 문구 수정에서는 건드릴 필요가 없습니다.

- index.html: 디자인·콘텐츠·설정·기능을 모두 담은 단일 홈페이지
- server.py: 클라우드 미리보기용 서버. 캐시 방지와 미리보기 경로 접두사를 지원합니다.
- assets/favicon.svg: 선택적인 브라우저 탭 아이콘. 없어도 디자인·기능은 작동합니다.

이전 외부 파일(styles.css, app.js, site-config.js)은 혼동을 방지하기 위해 제거했습니다. 앞으로는 index.html에서 수정하세요. 글꼴은 기기에 설치된 한국어 기본 글꼴을 사용합니다. 홈페이지는 상담용 외부 신청 페이지에 연결하며 자체적으로 신청 내용을 저장하지 않습니다.

## 공개하기

정적 호스팅에 index.html과 assets 폴더를 올리면 됩니다. GitHub Pages에서는 파일이 main에 반영된 뒤 Settings → Pages → Deploy from a branch → main / / (root)를 선택하세요. 공개 전에 상담 주소·연락처·방문 지역·시강 조건을 실제 정보로 확인하세요.

## 공식 로고

공식 원본 로고는 assets/stepon-logo.png에 보관하며, 헤더와 푸터에는 동일한 원본을 데이터 URI로 HTML 안에 포함했습니다. 미리보기에서 별도 이미지 경로를 불러오지 않아도 표시됩니다. 원본 비율을 유지하며 PC는 너비 64px, 모바일은 50px로 표시합니다. 로고를 교체할 때는 원본 파일과 index.html 내부의 두 공식 로고 데이터 URI를 함께 갱신해야 합니다. GitHub에서는 assets 폴더 → Add file → Upload files로 원본 파일을 업로드할 수 있습니다.

## 교육 사진

assets/images/에 원본 PNG와 웹 표시용 WebP를 보관합니다. main-study는 소개, home-tutoring은 방문수업, online-tutoring은 화상수업, study-management는 학습관리, parent-consulting은 무료 시강 안내에 사용합니다. 미리보기 이미지 경로 오류를 피하기 위해 화면의 사진은 WebP 데이터를 index.html에 직접 포함했습니다. 사진을 교체할 때는 원본 파일과 해당 education-photo 이미지의 src 데이터를 함께 갱신하세요. 사진의 크기·위치는 style 영역 끝의 교육 사진 CSS에서 조정합니다.
