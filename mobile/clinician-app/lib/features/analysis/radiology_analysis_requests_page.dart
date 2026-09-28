import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';
import '../radiology/widgets/radiology_ui.dart';

class RadiologyAnalysisRequest {
  const RadiologyAnalysisRequest({
    required this.analysisId,
    required this.studyId,
    required this.analysisType,
    required this.status,
    required this.stage,
    required this.priority,
    required this.requestedAt,
    required this.completedAt,
    required this.modelCode,
    required this.modelVersion,
  });

  factory RadiologyAnalysisRequest.fromJson(Map<String, dynamic> json) {
    final model = json['model'] as Map?;
    return RadiologyAnalysisRequest(
      analysisId: json['analysis_id']?.toString() ?? '',
      studyId: json['study_id']?.toString() ?? '',
      analysisType: json['analysis_type']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      stage: json['stage']?.toString() ?? '',
      priority: json['priority']?.toString() ?? '',
      requestedAt: json['requested_at']?.toString(),
      completedAt: json['completed_at']?.toString(),
      modelCode: model?['code']?.toString() ?? '',
      modelVersion: model?['version']?.toString() ?? '',
    );
  }

  final String analysisId;
  final String studyId;
  final String analysisType;
  final String status;
  final String stage;
  final String priority;
  final String? requestedAt;
  final String? completedAt;
  final String modelCode;
  final String modelVersion;
}

class RadiologyAnalysisApi {
  RadiologyAnalysisApi(this._client);

  final ClinicianApiClient _client;

  Future<List<RadiologyAnalysisRequest>> list({String? status}) async {
    final response = await _client.get(
      '/api/v1/ai-analyses',
      query: {if (status != null) 'status': status},
    );
    return (response['results'] as List? ?? const [])
        .whereType<Map>()
        .map(
          (item) => RadiologyAnalysisRequest.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList(growable: false);
  }
}

class RadiologyAnalysisRequestsPage extends StatefulWidget {
  const RadiologyAnalysisRequestsPage({super.key, required this.apiClient});

  final ClinicianApiClient apiClient;

  @override
  State<RadiologyAnalysisRequestsPage> createState() =>
      _RadiologyAnalysisRequestsPageState();
}

class _RadiologyAnalysisRequestsPageState
    extends State<RadiologyAnalysisRequestsPage> {
  List<RadiologyAnalysisRequest> _requests = const [];
  Map<String, Map<String, dynamic>> _studiesById = const {};
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  Future<void> _loadRequests() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final requests = await RadiologyAnalysisApi(widget.apiClient).list();
      final studies = await _loadMissingStudies(requests);
      if (mounted) {
        setState(() {
          _requests = requests;
          _studiesById = studies;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = 'AI 분석 요청을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<Map<String, Map<String, dynamic>>> _loadMissingStudies(
    List<RadiologyAnalysisRequest> requests,
  ) async {
    final next = Map<String, Map<String, dynamic>>.from(_studiesById);
    final missingStudyIds = requests
        .map((request) => request.studyId)
        .where((studyId) => studyId.isNotEmpty && !next.containsKey(studyId))
        .toSet();

    final entries = await Future.wait(
      missingStudyIds.map((studyId) async {
        try {
          final study = await widget.apiClient.get(
            '/api/v1/imaging-studies/$studyId',
          );
          return MapEntry(studyId, study);
        } on ClinicianApiException {
          return null;
        } catch (_) {
          return null;
        }
      }),
    );
    for (final entry in entries) {
      if (entry != null) {
        next[entry.key] = entry.value;
      }
    }
    return next;
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '분석요청'),
          const SizedBox(height: 6),
          const Text(
            '등록된 AI 분석 요청의 처리 상태를 확인합니다.',
            style: TextStyle(color: radiologyMuted, fontSize: 13),
          ),
          const SizedBox(height: 18),
          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_errorMessage != null)
            _AnalysisLoadError(message: _errorMessage!, onRetry: _loadRequests)
          else if (_requests.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.analytics_outlined,
              message: '표시할 AI 분석 요청이 없습니다.',
            )
          else
            ..._requests.map(
              (request) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _AnalysisRequestCard(
                  request: request,
                  study: _studiesById[request.studyId],
                  onTap: () => RadiologyNavigation.openAnalysis(request),
                ),
              ),
            ),
        ],
      );
}

class _AnalysisRequestCard extends StatelessWidget {
  const _AnalysisRequestCard({
    required this.request,
    required this.study,
    required this.onTap,
  });

  final RadiologyAnalysisRequest request;
  final Map<String, dynamic>? study;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: RadiologyInfoCard(
          padding: const EdgeInsets.all(15),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: const Color(0xFFEAF2FF),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.analytics_outlined,
                  color: radiologyBlue,
                  size: 21,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text.rich(
                            TextSpan(
                              children: [
                                TextSpan(text: _patientName(study)),
                                if (_patientNo(study).isNotEmpty)
                                  TextSpan(
                                    text: ' · ${_patientNo(study)}',
                                    style: const TextStyle(
                                      color: radiologyMuted,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                              ],
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: radiologyNavy,
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        RadiologyStatusChip(
                          label: _statusLabel(request.status),
                          color: _statusColor(request.status),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _analysisTypeLabel(request.analysisType),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: radiologyBlue,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      request.requestedAt == null
                          ? '요청일시 정보 없음'
                          : _formatDateTime(request.requestedAt!),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: radiologyMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 4),
              const Padding(
                padding: EdgeInsets.only(top: 1),
                child: Icon(
                  Icons.chevron_right_rounded,
                  color: radiologyMuted,
                  size: 20,
                ),
              ),
            ],
          ),
        ),
      );

}

String _patientName(Map<String, dynamic>? study) {
  final patient = study?['patient'] as Map?;
  final name = patient?['name']?.toString();
  return name == null || name.isEmpty ? '환자 정보 없음' : name;
}

String _patientNo(Map<String, dynamic>? study) {
  final patient = study?['patient'] as Map?;
  return patient?['patient_no']?.toString() ?? '';
}

class _AnalysisLoadError extends StatelessWidget {
  const _AnalysisLoadError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Column(
          children: [
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 10),
            TextButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ),
      );
}

String _statusLabel(String status) => switch (status) {
      'QUEUED' => '분석 대기',
      'PROCESSING' => '분석 중',
      'RETRYING' => '재시도 중',
      'COMPLETED' => '분석 완료',
      'FAILED' => '분석 실패',
      'CANCELLED' => '분석 취소',
      _ => status.isEmpty ? '상태 미확인' : status,
    };

Color _statusColor(String status) => switch (status) {
      'QUEUED' || 'RETRYING' => radiologyWarning,
      'PROCESSING' => radiologyBlue,
      'FAILED' || 'CANCELLED' => radiologyDanger,
      _ => radiologySuccess,
    };

String _analysisTypeLabel(String analysisType) => switch (analysisType) {
      'HEMORRHAGIC_STROKE_CT' => 'CT 뇌출혈 분석',
      'ISCHEMIC_STROKE_DWI_ADC' => 'MRI 허혈성 뇌졸중 분석',
      'CEREBRAL_ANEURYSM_MRA' => 'MRA 뇌동맥류 분석',
      _ => analysisType.isEmpty ? '분석 유형 정보 없음' : analysisType,
    };

String _formatDateTime(String value) {
  final dateTime = DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  String two(int number) => number.toString().padLeft(2, '0');
  return '${dateTime.year}.${two(dateTime.month)}.${two(dateTime.day)} '
      '${two(dateTime.hour)}:${two(dateTime.minute)}';
}
