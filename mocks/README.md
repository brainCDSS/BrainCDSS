# Mocks
고정 synthetic JSON으로 success/delay/failure mode adapter를 구현할 위치다. 실제 개인정보·AI 정확도·외부 전송은 금지한다.

`inference-server/`에는 독립 FastAPI mock 서버와 성공·실패 테스트가 있다.
실행 방법과 현재 범위는 [inference-server/README.md](inference-server/README.md)를 참고한다.
지연 mode와 나머지 외부 연동 서버 동작은 TODO다.
