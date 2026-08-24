# Mobile rules

환자 앱과 의료진 앱은 독립 build·release 단위다. 역할별 화면과 workflow를 서로 참조하지 않고, 검증된 비임상 공통 코드만 `packages/brainon_mobile_core`로 공유한다. Firebase key/config와 실제 의료데이터를 commit하지 않는다. 승인된 API/RBAC 계약 이후 기능을 추가하고 변경한 앱과 shared package의 analyze/test를 실행한다.
