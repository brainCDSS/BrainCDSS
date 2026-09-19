import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'radiology_analysis_detail_page.dart';

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
      if (mounted) {
        setState(() => _requests = requests);
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
            const Center(child: Padding(
              padding: EdgeInsets.all(32),
              child: CircularProgressIndicator(),
            ))
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
                padding: const EdgeInsets.only(bottom: 10),
                child: _AnalysisRequestCard(
                  request: request,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => RadiologyAnalysisDetailPage(request: request),
                    ),
                  ),
                ),
              ),
            ),
        ],
      );
}

class _AnalysisRequestCard extends StatelessWidget {
  const _AnalysisRequestCard({required this.request, required this.onTap});

  final RadiologyAnalysisRequest request;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: RadiologyInfoCard(
          child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: const Color(0xFFEAF2FF),
                borderRadius: BorderRadius.circular(13),
              ),
              child: const Icon(Icons.analytics_outlined, color: radiologyBlue),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          request.analysisType.isEmpty
                              ? '분석 종류 정보 없음'
                              : request.analysisType,
                          style: const TextStyle(
                            color: radiologyNavy,
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      RadiologyStatusChip(
                        label: _statusLabel(request.status),
                        color: _statusColor(request.status),
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    request.stage.isEmpty ? '단계 정보 없음' : request.stage,
                    style: const TextStyle(
                      color: radiologyBlue,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _metadata(request),
                    style: const TextStyle(color: radiologyMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
          ),
        ),
      );

  String _metadata(RadiologyAnalysisRequest request) {
    final values = <String>[
      if (request.priority.isNotEmpty) request.priority,
      if (request.requestedAt != null) _formatDateTime(request.requestedAt!),
      if (request.modelCode.isNotEmpty) request.modelCode,
    ];
    return values.isEmpty ? '추가 정보 없음' : values.join(' · ');
  }
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
      'QUEUED' => '대기',
      'PROCESSING' => '처리중',
      'RETRYING' => '재시도',
      'COMPLETED' => '완료',
      'FAILED' => '실패',
      'CANCELLED' => '취소',
      _ => status.isEmpty ? '정보 없음' : status,
    };

Color _statusColor(String status) => switch (status) {
      'QUEUED' || 'RETRYING' => const Color(0xFFB46912),
      'PROCESSING' => const Color(0xFF2563B8),
      'FAILED' || 'CANCELLED' => const Color(0xFFCC4D5B),
      _ => const Color(0xFF208563),
    };

String _formatDateTime(String value) {
  final dateTime = DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.'
      '${dateTime.day.toString().padLeft(2, '0')} '
      '${dateTime.hour.toString().padLeft(2, '0')}:'
      '${dateTime.minute.toString().padLeft(2, '0')}';
}
