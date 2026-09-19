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
        scheduledAt: DateTime.tryParse(json['scheduled_at']?.toString() ?? '')
            ?.toLocal(),
        timeSlot: json['time_slot']?.toString(),
        dose: json['dose']?.toString(),
        status: json['status']?.toString(),
        intakeId: json['intake_id']?.toString(),
        takenAt:
            DateTime.tryParse(json['taken_at']?.toString() ?? '')?.toLocal(),
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
