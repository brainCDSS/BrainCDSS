# Patient app

목적: 환자용 Flutter 앱을 독립 build/release한다. 환자 인증, 예약, 복약, 검사결과, 알림, 응급 안내, assistant UI를 features에 둔다. 의료진 전용 workflow, 실제 환자정보, Firebase 설정 파일은 넣지 않는다. 진입점은 lib/main.dart. flutter pub get, flutter run으로 실행하고 flutter analyze, flutter test로 검증한다. Backend URL과 FCM 값은 향후 승인된 runtime config로 주입한다. 다음 작업은 Django health/API client와 환자 인증 contract 연결이다.

