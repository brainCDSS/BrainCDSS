# 기여 가이드

`main`은 릴리스 가능 상태, `develop`은 통합 기준, `feature/*`는 짧은 작업 브랜치로 사용한다. 작은 목적 단위 commit과 검토 가능한 PR을 만들고 commit/PR에 환자정보나 secret을 넣지 않는다.

Migration 충돌은 최신 `develop`을 반영한 뒤 두 migration의 dependency를 확인하고 필요한 경우 Django merge migration으로 해결한다. 기존 migration을 공유 후 임의 수정하지 않는다. API/event 변경은 먼저 `contracts/` schema와 version/호환성 문서를 갱신하고 producer/consumer contract test를 함께 수정한다.

PR 전 확인:
- 관련 test, lint, build를 실행하고 결과를 기록했다.
- DB migration 생성·적용 여부를 확인했다.
- REST API와 RabbitMQ event contract의 호환성을 확인했다.
- 실제 의료데이터·영상·secret·가중치가 없다.
- production dependency의 필요성과 대안을 기록했다.
- RBAC, audit, trace 경계를 우회하지 않는다.
