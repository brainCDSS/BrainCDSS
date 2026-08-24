// Smoke test for the clinician-specific application shell.
import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_clinician_app/main.dart';
void main() {
  testWidgets('renders clinician shell', (tester) async {
    await tester.pumpWidget(const ClinicianApp());
    expect(find.text('Clinician app shell is ready.'), findsOneWidget);
  });
}
