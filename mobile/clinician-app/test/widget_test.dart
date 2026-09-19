import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_clinician_app/app/clinician_app.dart';

void main() {
  testWidgets('renders radiology clinician shell', (tester) async {
    await tester.pumpWidget(const ClinicianApp());
    expect(find.text('Brain On'), findsOneWidget);
    expect(find.text('영상의학과'), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
  });
}
