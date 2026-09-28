import '../../core/api/api_client.dart';

class PatientPrescriptionsApi {
  PatientPrescriptionsApi(this._client);

  final ApiClient _client;

  Future<List<PrescriptionItemSummary>> listItems() async {
    final response = await _client.get('/api/v1/me/prescriptions');
    final items = <PrescriptionItemSummary>[];
    for (final prescription
        in (response['results'] as List? ?? const []).whereType<Map>()) {
      for (final item
          in (prescription['items'] as List? ?? const []).whereType<Map>()) {
        final parsed = PrescriptionItemSummary.fromJson(item);
        if (parsed.itemId.isNotEmpty) items.add(parsed);
      }
    }
    return items;
  }
}

class MedicationSchedulesApi {
  MedicationSchedulesApi(this._client);

  final ApiClient _client;

  Future<List<MedicationScheduleSummary>> listForDate(DateTime date) async {
    final response = await _client.get('/api/v1/medication-schedules', query: {
      'date': _dateQuery(date),
    });
    return (response['items'] as List? ?? const [])
        .whereType<Map>()
        .map(MedicationScheduleSummary.fromJson)
        .toList();
  }

  Future<void> markTaken(String scheduleId) async {
    await _client.post(
      '/api/v1/medication-intakes',
      body: {
        'medication_schedule_id': scheduleId,
        'status': 'TAKEN',
      },
    );
  }

  Future<void> updateIntake(String intakeId, String status) async {
    await _client.patch(
      '/api/v1/medication-intakes/$intakeId',
      body: {'status': status},
    );
  }

  Future<void> deleteIntake(String intakeId) async {
    await _client.delete('/api/v1/medication-intakes/$intakeId');
  }
}

const _koreaOffset = Duration(hours: 9);

DateTime koreaNow() => _toKoreaWallTime(DateTime.now().toUtc());

DateTime? parseKoreaDateTime(Object? value) {
  if (value is DateTime) {
    return value.isUtc ? _toKoreaWallTime(value) : value;
  }

  final raw = value?.toString().trim() ?? '';
  if (raw.isEmpty) return null;
  final parsed = DateTime.tryParse(raw);
  if (parsed == null) return null;

  // Django's aware ISO-8601 values include Z or an explicit UTC offset.
  // Keep legacy offset-less values unchanged instead of assuming their zone.
  final hasTimeZone = RegExp(r'(Z|[+-]\d{2}:?\d{2})$', caseSensitive: false)
      .hasMatch(raw);
  return hasTimeZone ? _toKoreaWallTime(parsed.toUtc()) : parsed;
}

DateTime _toKoreaWallTime(DateTime utcValue) {
  final korea = utcValue.add(_koreaOffset);
  return DateTime(
    korea.year,
    korea.month,
    korea.day,
    korea.hour,
    korea.minute,
    korea.second,
    korea.millisecond,
    korea.microsecond,
  );
}

String _dateQuery(DateTime date) =>
    '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

class MedicationScheduleSummary {
  const MedicationScheduleSummary({
    required this.scheduleId,
    required this.prescriptionId,
    required this.medicationName,
    required this.scheduledAt,
    required this.timeSlot,
    required this.dose,
    required this.status,
    required this.intakeId,
    required this.takenAt,
  });

  final String scheduleId;
  final String prescriptionId;
  final String medicationName;
  final DateTime? scheduledAt;
  final String? timeSlot;
  final String? dose;
  final String? status;
  final String? intakeId;
  final DateTime? takenAt;

  factory MedicationScheduleSummary.fromJson(Map<dynamic, dynamic> json) =>
      MedicationScheduleSummary(
        scheduleId: json['schedule_id']?.toString() ?? '',
        prescriptionId: json['prescription_id']?.toString() ?? '',
        medicationName: json['medication_name']?.toString() ?? '',
        scheduledAt: parseKoreaDateTime(json['scheduled_at']),
        timeSlot: json['time_slot']?.toString(),
        dose: json['dose']?.toString(),
        status: json['status']?.toString(),
        intakeId: json['intake_id']?.toString(),
        takenAt: parseKoreaDateTime(json['taken_at']),
      );
}

class PrescriptionItemSummary {
  const PrescriptionItemSummary({
    required this.itemId,
    required this.prescriptionId,
    required this.medicationId,
    required this.medicationCode,
    required this.medicationName,
    required this.dose,
    required this.doseUnit,
    required this.route,
    required this.frequencyPerDay,
    required this.timing,
    required this.startDate,
    required this.durationDays,
    required this.instructions,
  });

  final String itemId;
  final String prescriptionId;
  final String medicationId;
  final String? medicationCode;
  final String medicationName;
  final String dose;
  final String doseUnit;
  final String? route;
  final int frequencyPerDay;
  final String? timing;
  final DateTime? startDate;
  final int durationDays;
  final String? instructions;

  factory PrescriptionItemSummary.fromJson(Map<dynamic, dynamic> json) =>
      PrescriptionItemSummary(
        itemId: json['item_id']?.toString() ?? '',
        prescriptionId: json['prescription_id']?.toString() ?? '',
        medicationId: json['medication_id']?.toString() ?? '',
        medicationCode: json['medication_code']?.toString(),
        medicationName: json['medication_name']?.toString() ?? '',
        dose: json['dose']?.toString() ?? '',
        doseUnit: json['dose_unit']?.toString() ?? '',
        route: json['route']?.toString(),
        frequencyPerDay: json['frequency_per_day'] is int
            ? json['frequency_per_day'] as int
            : int.tryParse(json['frequency_per_day']?.toString() ?? '') ?? 0,
        timing: json['timing']?.toString(),
        startDate: DateTime.tryParse(json['start_date']?.toString() ?? ''),
        durationDays: json['duration_days'] is int
            ? json['duration_days'] as int
            : int.tryParse(json['duration_days']?.toString() ?? '') ?? 0,
        instructions: json['instructions']?.toString(),
      );
}
