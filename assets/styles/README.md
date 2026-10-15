# 공통 가독성 스타일

`readability.css`에서 메인과 모든 공개 안내 페이지의 글자 대비, 제목 굵기, 버튼 및 카드 스타일을 관리합니다. 기존 레이아웃과 문구는 각 페이지 원본을 유지합니다.

수정 후 저장소 루트에서 다음 명령을 실행하세요.

```sh
python3 scripts/build_seo.py
python3 scripts/build_seo.py --check
```

빌드 시 메인 `index.html`의 `readability` 스타일 영역과 모든 안내 페이지에 CSS가 인라인으로 포함됩니다. 외부 CSS 요청이 실패해도 디자인이 적용됩니다. 생성된 안내 페이지의 CSS를 직접 수정하지 마세요.
