# 공통 플로팅 상담 메뉴

`floating-consult.html`에 메뉴 전용 HTML·CSS·JavaScript가 있습니다. 외부 라이브러리나 CSS 요청 없이 각 페이지에 인라인으로 포함됩니다.

연결 주소와 전화번호는 `data/seo/site.json`의 `phone_uri`, `phone`, `kakao_url`, `consultation_url`을 사용합니다. 수정한 뒤 `python3 scripts/build_seo.py`를 실행하면 메인 및 모든 안내 페이지에 동기화됩니다. 기존 메인 상담 버튼의 설정은 `index.html`의 `STEPON_CONFIG`에 별도로 유지되어 있습니다.

모바일에서는 기존 하단 상담 버튼 위에 접힌 메뉴를 표시합니다. 버튼으로 펼치거나 닫을 수 있으며 Escape로 닫으면 메뉴 버튼으로 초점이 돌아옵니다. JavaScript가 꺼져 있어도 세 상담 링크를 사용할 수 있습니다.

`python3 scripts/build_seo.py --check`로 생성 결과와 메인 컴포넌트가 최신인지 확인할 수 있습니다. 생성된 안내 HTML이나 메인 내 `floating-consult` 표시 영역을 직접 수정하지 마세요.
