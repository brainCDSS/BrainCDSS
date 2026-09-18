import '../../core/api/api_client.dart';

class PatientProfileApi {
  PatientProfileApi(this._client);

  final ApiClient _client;

  Future<PatientProfile> getProfile() async {
    final response = await _client.get('/api/v1/me/profile');
    return PatientProfile.fromJson(response);
  }
}

class PatientProfile {
  const PatientProfile({
    required this.name,
    required this.birthDate,
    required this.sex,
    required this.phone,
    required this.emergencyContact,
    required this.allergyInfo,
  });

  final String? name;
  final DateTime? birthDate;
  final String? sex;
  final String? phone;
  final String? emergencyContact;
  final String? allergyInfo;

  factory PatientProfile.fromJson(Map<String, dynamic> json) =>
      PatientProfile(
        name: json['name']?.toString(),
        birthDate: DateTime.tryParse(json['birth_date']?.toString() ?? ''),
        sex: json['sex']?.toString(),
        phone: json['phone']?.toString(),
        emergencyContact: json['emergency_contact']?.toString(),
        allergyInfo: json['allergy_info']?.toString(),
      );
}
