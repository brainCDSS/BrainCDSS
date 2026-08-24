# BrainOn mobile core

목적: 두 앱이 공유해도 안전한 API endpoint 설정, 인증 interface, 공통 오류와 design token의 경계다. 환자/의료진 화면, 역할별 workflow, 임상 model은 넣지 않는다. 진입점은 lib/brainon_mobile_core.dart이며 flutter test로 검증한다. 다음 작업은 승인된 REST contract 기반 API client interface다.

