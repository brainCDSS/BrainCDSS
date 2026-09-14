import '../../core/api/api_client.dart';

class HomeApi {
  HomeApi(this.apiClient);

  final ApiClient apiClient;

  Future<List<HomeAppointment>> getMyAppointments() async {
    final response = await apiClient.get(
      '/api/v1/appointments',
      query: {
        'page': '1',
      },
    );

    final results = response['results'];

    if (results is! List) {
      return const [];
    }

    return results
        .whereType<Map>()
        .map(
          (item) => HomeAppointment.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }
}

class HomeAppointment {
  const HomeAppointment({
    required this.appointmentId,
    required this.status,
    required this.requestType,
    required this.hospitalName,
    required this.departmentName,
    required this.clinicianName,
    required this.clinicianId,
    required this.scheduledAt,
  });

  final String appointmentId;
  final String status;
  final String requestType;

  final String hospitalName;
  final String departmentName;
  final String clinicianName;
  final String clinicianId;

  final DateTime? scheduledAt;

  factory HomeAppointment.fromJson(
    Map<String, dynamic> json,
  ) {
    return HomeAppointment(
      appointmentId:
          json['appointment_id']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      requestType:
          json['request_type']?.toString() ?? '',
      hospitalName: _nestedName(
        json['hospital'],
      ),
      departmentName: _nestedName(
        json['department'],
      ),
      clinicianName: _nestedName(
        json['clinician'],
      ),
      clinicianId: _nestedId(json['clinician']),
      scheduledAt: _parseDateTime(
        json['scheduled_at'],
      ),
    );
  }

  static String _nestedName(dynamic value) {
    if (value is Map) {
      return value['name']?.toString() ?? '';
    }

    return '';
  }

  static String _nestedId(dynamic value) {
    if (value is Map) return value['id']?.toString() ?? '';
    return '';
  }

  static DateTime? _parseDateTime(dynamic value) {
    if (value == null) {
      return null;
    }

    return DateTime.tryParse(
      value.toString(),
    );
  }
}
