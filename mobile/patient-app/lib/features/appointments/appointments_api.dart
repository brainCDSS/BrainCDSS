import '../../core/api/api_client.dart';

class AppointmentsApi {
  AppointmentsApi(this.client);
  final ApiClient client;

  Future<Map<String, dynamic>> detail(String id) =>
      client.get('/api/v1/appointments/$id');

  Future<void> create(String slotId) async {
    await client.post('/api/v1/appointments', body: {'slot_id': slotId});
  }

  Future<void> reschedule(String id, String slotId) async {
    await client.patch('/api/v1/appointments/$id/reschedule', body: {'new_slot_id': slotId});
  }

  Future<void> cancel(String id, {String? reason}) async {
    await client.post('/api/v1/appointments/$id/cancel', body: {
      if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
    });
  }

  Future<List<ClinicianOption>> clinicians() async {
    final hospitals = await client.get('/api/v1/hospitals', query: {'page': '1'});
    final values = <String, ClinicianOption>{};
    for (final hospital in (hospitals['results'] as List? ?? const []).whereType<Map>()) {
      final detail = await client.get('/api/v1/hospitals/${hospital['id']}');
      for (final department in (detail['departments'] as List? ?? const []).whereType<Map>()) {
        final response = await client.get('/api/v1/departments/${department['id']}/clinicians');
        for (final clinician in (response['clinicians'] as List? ?? const []).whereType<Map>()) {
          if (clinician['is_active'] == true) {
            final item = ClinicianOption(
              id: clinician['id']?.toString() ?? '',
              name: clinician['name']?.toString() ?? '',
              department: department['name']?.toString() ?? '',
            );
            if (item.id.isNotEmpty) values[item.id] = item;
          }
        }
      }
    }
    return values.values.toList();
  }

  Future<List<AppointmentSlot>> slots(String clinicianId, DateTime date) async {
    final value = '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    final response = await client.get('/api/v1/clinicians/$clinicianId/slots', query: {'date': value});
    return (response['slots'] as List? ?? response['results'] as List? ?? const [])
        .whereType<Map>()
        .map(AppointmentSlot.fromJson)
        .where((slot) => slot.status == 'AVAILABLE' && slot.id.isNotEmpty)
        .toList();
  }
}

class ClinicianOption {
  const ClinicianOption({required this.id, required this.name, required this.department});
  final String id;
  final String name;
  final String department;
}

class AppointmentSlot {
  const AppointmentSlot({required this.id, required this.startAt, required this.endAt, required this.status});
  final String id;
  final DateTime? startAt;
  final DateTime? endAt;
  final String status;
  factory AppointmentSlot.fromJson(Map<dynamic, dynamic> json) => AppointmentSlot(
        id: json['id']?.toString() ?? '',
        startAt: DateTime.tryParse(json['start_at']?.toString() ?? ''),
        endAt: DateTime.tryParse(json['end_at']?.toString() ?? ''),
        status: json['status']?.toString() ?? '',
      );
}
