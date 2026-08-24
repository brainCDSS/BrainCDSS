# Clinician app

목적: 의료진용 Flutter 앱을 독립 build/release한다. 의료진 인증, 환자 조회, 예약, 알림, 응급 workflow, assistant UI를 features에 둔다. 환자 self-service 화면, 실제 의료데이터, Firebase 설정 파일은 넣지 않는다. 진입점은 lib/main.dart. flutter pub get, flutter run으로 실행하고 flutter analyze, flutter test로 검증한다. 다음 작업은 Django health/API client와 의료진 RBAC contract 연결이다.

