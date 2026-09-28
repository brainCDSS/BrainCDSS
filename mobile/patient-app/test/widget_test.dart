// Smoke test for the patient-specific authentication entry point.
import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_patient_app/app/patient_app.dart';
import 'package:brainon_patient_app/features/auth/auth_storage.dart';

class _EmptyAuthStorage implements AuthStorage {
  @override
  Future<void> clear() async {}

  @override
  Future<StoredAuthSession?> read() async => null;

  @override
  Future<void> save(session) async {}

  @override
  Future<void> updateAccessToken(String accessToken) async {}
}

void main() {
  testWidgets('shows login page without stored authentication', (tester) async {
    await tester.pumpWidget(PatientApp(authStorage: _EmptyAuthStorage()));
    await tester.pump();

    expect(find.text('내 건강을 더 가깝게, HODOC'), findsOneWidget);
    expect(find.text('아이디'), findsOneWidget);
    expect(find.text('비밀번호'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget);
  });
}
