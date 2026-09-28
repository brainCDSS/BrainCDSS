import 'package:brainon_patient_app/features/medications/patient_prescriptions_api.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('parseKoreaDateTime', () {
    test('converts UTC schedule times to Asia/Seoul wall time', () {
      expect(
        parseKoreaDateTime('2026-09-28T01:00:00Z'),
        DateTime(2026, 9, 28, 10),
      );
      expect(
        parseKoreaDateTime('2026-09-28T03:00:00+00:00'),
        DateTime(2026, 9, 28, 12),
      );
      expect(
        parseKoreaDateTime('2026-09-28T09:00:00Z'),
        DateTime(2026, 9, 28, 18),
      );
    });

    test('moves a late UTC schedule into the next Seoul calendar day', () {
      expect(
        parseKoreaDateTime('2026-09-28T23:00:00Z'),
        DateTime(2026, 9, 29, 8),
      );
    });
  });
}
