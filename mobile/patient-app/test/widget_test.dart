// Smoke test for the patient-specific application shell.
import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_patient_app/app/patient_app.dart';

void main() {
  testWidgets('renders patient shell', (tester) async {
    await tester.pumpWidget(const PatientApp());
    expect(find.text('건강 요약'), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
    expect(find.text('예약'), findsOneWidget);
    expect(find.text('검사 · 결과'), findsOneWidget);
    expect(find.text('복약'), findsOneWidget);
    expect(find.text('마이페이지'), findsOneWidget);

    await tester.tap(find.text('예약').last);
    await tester.pump();
    expect(find.text('예약하기'), findsOneWidget);
  });
}
