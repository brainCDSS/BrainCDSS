import '../../core/api/api_client.dart';

class ClinicalHistoryApi {
  ClinicalHistoryApi(this._client);
  final ApiClient _client;

  Future<List<ClinicalHistoryItem>> list() async {
    final response = await _client.get('/api/v1/me/clinical-history');
    return (response['results'] as List? ?? const [])
        .whereType<Map>()
        .map(ClinicalHistoryItem.fromJson)
        .where((item) => item.encounterId.isNotEmpty)
        .toList();
  }

  Future<ClinicalHistoryDetail> detail(String encounterId) async =>
      ClinicalHistoryDetail.fromJson(
        await _client.get('/api/v1/me/clinical-history/$encounterId'),
      );
}

class ClinicalHistoryItem {
  const ClinicalHistoryItem(
      {required this.encounterId,
      required this.visitedAt,
      required this.departmentName,
      required this.clinicianName,
      required this.diagnosisName,
      required this.clinicalOpinion,
      required this.examNames,
      required this.hasPrescription});
  final String encounterId;
  final DateTime? visitedAt;
  final String? departmentName;
  final String? clinicianName;
  final String? diagnosisName;
  final String? clinicalOpinion;
  final List<String> examNames;
  final bool hasPrescription;
  factory ClinicalHistoryItem.fromJson(Map<dynamic, dynamic> json) =>
      ClinicalHistoryItem(
        encounterId: json['encounter_id']?.toString() ?? '',
        visitedAt: DateTime.tryParse(json['visited_at']?.toString() ?? ''),
        departmentName: _text(json['department_name']),
        clinicianName: _text(json['clinician_name']),
        diagnosisName: _text(json['diagnosis_name']),
        clinicalOpinion: _text(json['clinical_opinion']),
        examNames: (json['exam_names'] as List? ?? const [])
            .map((value) => value.toString())
            .where((value) => value.isNotEmpty)
            .toList(),
        hasPrescription: json['has_prescription'] == true,
      );
}

class ClinicalHistoryDetail {
  const ClinicalHistoryDetail(
      {required this.visitedAt,
      required this.departmentName,
      required this.clinicianName,
      required this.diagnosisName,
      required this.encounterType,
      required this.exams,
      required this.clinicalOpinion,
      required this.hasPrescription});
  final DateTime? visitedAt;
  final String? departmentName;
  final String? clinicianName;
  final String? diagnosisName;
  final String? encounterType;
  final List<ClinicalHistoryExam> exams;
  final String? clinicalOpinion;
  final bool hasPrescription;
  factory ClinicalHistoryDetail.fromJson(Map<dynamic, dynamic> json) =>
      ClinicalHistoryDetail(
        visitedAt: DateTime.tryParse(json['visited_at']?.toString() ?? ''),
        departmentName: _text(json['department_name']),
        clinicianName: _text(json['clinician_name']),
        diagnosisName: _text(json['diagnosis_name']),
        encounterType: _text(json['encounter_type']),
        exams: (json['exams'] as List? ?? const [])
            .whereType<Map>()
            .map(ClinicalHistoryExam.fromJson)
            .toList(),
        clinicalOpinion: _text(json['clinical_opinion']),
        hasPrescription: json['has_prescription'] == true,
      );
}

class ClinicalHistoryExam {
  const ClinicalHistoryExam({required this.name, required this.examDate});
  final String name;
  final DateTime? examDate;
  factory ClinicalHistoryExam.fromJson(Map<dynamic, dynamic> json) =>
      ClinicalHistoryExam(
          name: json['name']?.toString() ?? '',
          examDate: DateTime.tryParse(json['exam_date']?.toString() ?? ''));
}

String? _text(dynamic value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}
