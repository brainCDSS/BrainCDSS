import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_clinician_app/app/clinician_app.dart';

void main() {
  testWidgets('renders session restoration state', (tester) async {
    await tester.pumpWidget(const ClinicianApp());
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
