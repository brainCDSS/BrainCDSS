// Smoke test for the patient-specific application shell.
import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_patient_app/main.dart';
void main() {
  testWidgets('renders patient shell', (tester) async {
    await tester.pumpWidget(const PatientApp());
    expect(find.text('Patient app shell is ready.'), findsOneWidget);
  });
}
