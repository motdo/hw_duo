# hw_duo

Flask와 SQLite를 사용하는 로컬 주소록 웹 서비스입니다. 현재 백엔드는 로그인, 회원가입, 로그아웃, 연락처 검색, 연락처 추가/수정/삭제 라우트와 DB 연결을 제공합니다.

## 실행 방법

```powershell
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app seed-db
python -m flask --app app run --debug
```

`seed-db`를 실행하면 테스트 계정 `demo / demo1234`와 샘플 연락처가 생성됩니다.

## 템플릿 연결 규칙

프론트엔드 템플릿은 아래 경로로 두면 `app.py`에서 바로 렌더링합니다.

- `templates/auth/login.html`
- `templates/auth/register.html`
- `templates/search/index.html`

사용할 수 있는 주요 엔드포인트는 아래와 같습니다.

- `url_for("auth.login")`: 로그인, `POST` 필드 `username`, `password`
- `url_for("auth.register")`: 회원가입, `POST` 필드 `username`, `password`, 선택 필드 `password_confirm`
- `url_for("auth.logout")`: 로그아웃
- `url_for("search.index")`: 검색 페이지, 검색어 파라미터 `q` 또는 `query`
- `url_for("search.api")`: 검색 결과 JSON API, 검색어 파라미터 `q` 또는 `query`
- `url_for("search.create_contact")`: 연락처 추가, `POST` 필드 `name`, `phone`, `email`, `address`, `memo`
- `url_for("search.update_contact", contact_id=contact.id)`: 연락처 수정
- `url_for("search.delete_contact", contact_id=contact.id)`: 연락처 삭제

`templates/search/index.html`에는 `query`, `contacts`, `total` 변수가 전달됩니다. 로그인된 사용자는 모든 템플릿에서 Flask 전역 객체 `g.user`로 확인할 수 있습니다.
