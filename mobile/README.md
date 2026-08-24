# Mobile

목적: 환자용 `patient-app`과 의료진용 `clinician-app`을 독립적으로 build·release한다. 공통 비임상 interface만 `packages/brainon_mobile_core`에 둔다. 역할별 화면·routing·권한·FCM 처리는 각 앱에 두며 실제 환자정보와 Firebase 설정 파일은 저장하지 않는다.

주요 진입점은 각 앱의 `lib/main.dart`다. 앱별로 `flutter pub get && flutter run`을 실행하며, 검증은 각 앱과 shared package에서 `flutter analyze && flutter test`를 수행한다. Android/iOS runner는 팀의 application ID와 signing 정책 확정 후 각 앱에서 `flutter create --platforms=android,ios .`로 생성한다. 다음 작업은 Django Health/API client, 앱별 인증 contract, FCM adapter다.
