import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_clinician_app/app/clinician_app.dart';

void main() {
  testWidgets('renders clinician login page', (tester) async {
    await tester.pumpWidget(const ClinicianApp());

    expect(find.text('Brain On'), findsOneWidget);
    expect(find.text('아이디'), findsOneWidget);
    expect(find.text('비밀번호'), findsOneWidget);
    expect(find.text('로그인'), findsNWidgets(2));
  });
}
