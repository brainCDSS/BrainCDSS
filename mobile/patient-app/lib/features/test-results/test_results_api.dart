import '../../core/api/api_client.dart';

class TestResultsApi {
  TestResultsApi(this._client);

  final ApiClient _client;

  Future<List<TestResultSummary>> list() async {
    final response = await _client.get('/api/v1/me/test-results');
    return (response['results'] as List? ?? const [])
        .whereType<Map>()
        .map(TestResultSummary.fromJson)
        .where((result) => result.studyId.isNotEmpty)
        .toList();
  }
}

class TestResultSummary {
  const TestResultSummary({
    required this.studyId,
    required this.studyDatetime,
    required this.modalities,
    required this.studyDescription,
  });

  final String studyId;
  final DateTime? studyDatetime;
  final List<String> modalities;
  final String studyDescription;

  factory TestResultSummary.fromJson(Map<dynamic, dynamic> json) =>
      TestResultSummary(
        studyId: json['study_id']?.toString() ?? '',
        studyDatetime:
            DateTime.tryParse(json['study_datetime']?.toString() ?? ''),
        modalities: (json['modalities'] as List? ?? const [])
            .map((value) => value.toString())
            .where((value) => value.isNotEmpty)
            .toList(),
        studyDescription: json['study_description']?.toString() ?? '',
      );
}
