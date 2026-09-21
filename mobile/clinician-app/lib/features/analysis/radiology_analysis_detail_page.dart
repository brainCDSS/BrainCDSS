import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'radiology_analysis_requests_page.dart';

class RadiologyAnalysisDetailPage extends StatefulWidget {
  const RadiologyAnalysisDetailPage({
    super.key,
    required this.apiClient,
    required this.request,
  });

  final ClinicianApiClient apiClient;
  final RadiologyAnalysisRequest request;

  @override
  State<RadiologyAnalysisDetailPage> createState() =>
      _RadiologyAnalysisDetailPageState();
}

class _RadiologyAnalysisDetailPageState
    extends State<RadiologyAnalysisDetailPage> {
  Map<String, dynamic>? _analysis;
  Map<String, dynamic>? _study;
  Map<String, dynamic>? _result;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final analysis = await widget.apiClient.get(
        '/api/v1/ai-analyses/${widget.request.analysisId}',
      );
      Map<String, dynamic>? study;
      final studyId = analysis['study_id']?.toString() ?? widget.request.studyId;
      if (studyId.isNotEmpty) {
        study = await widget.apiClient.get(
          '/api/v1/imaging-studies/$studyId',
        );
      }
      Map<String, dynamic>? result;
      if (analysis['status']?.toString() == 'COMPLETED') {
        try {
          result = await widget.apiClient.get(
            '/api/v1/ai-analyses/${widget.request.analysisId}/result',
          );
        } on ClinicianApiException {
          // Result projection can be briefly unavailable after completion.
        } catch (_) {
          // Preserve the completed-analysis screen when result parsing fails.
        }
      }
      if (mounted) {
        setState(() {
          _analysis = analysis;
          _study = study;
          _result = result;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = 'AI 분석 정보를 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
                ? _LoadError(message: _errorMessage!, onRetry: _load)
                : _AnalysisBody(
                    analysis: _analysis!,
                    study: _study,
                    result: _result,
                  );
}

class _AnalysisBody extends StatelessWidget {
  const _AnalysisBody({
    required this.analysis,
    required this.study,
    required this.result,
  });

  final Map<String, dynamic> analysis;
  final Map<String, dynamic>? study;
  final Map<String, dynamic>? result;

  @override
  Widget build(BuildContext context) {
    final status = analysis['status']?.toString() ?? '';
    final patient = study?['patient'] as Map?;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const RadiologySectionTitle(title: '환자 및 검사 정보'),
        const SizedBox(height: 10),
        RadiologyInfoCard(
          child: Column(
            children: [
              _InfoRow(label: '환자명', value: patient?['name']?.toString()),
              _InfoRow(label: '환자번호', value: patient?['patient_no']?.toString()),
              _InfoRow(
                label: '검사 일시',
                value: _formatDateTime(study?['study_datetime']?.toString()),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const RadiologySectionTitle(title: '분석 결과'),
        const SizedBox(height: 10),
        RadiologyInfoCard(
          child: Column(
            children: [
              _InfoRow(
                label: '분석 유형',
                value: _analysisTypeLabel(
                  analysis['analysis_type']?.toString(),
                ),
              ),
              _InfoRow(label: '분석 상태', value: _statusLabel(status)),
              _InfoRow(
                label: 'AI 판정',
                value: _aiJudgment(
                  analysis['analysis_type']?.toString(),
                  result?['is_positive'],
                ),
              ),
              _InfoRow(
                label: '병변 개수',
                value: _lesionCountValue(result?['lesion_count']),
              ),
              _InfoRow(
                label: '총 병변 부피',
                value: _volumeValue(result?['total_volume_ml']),
              ),
              if (result?['confidence'] != null)
                _InfoRow(
                  label: '신뢰도',
                  value: _confidenceValue(result?['confidence']),
                ),
              _InfoRow(
                label: '분석 요청',
                value: _formatDateTime(analysis['requested_at']?.toString()),
              ),
              _InfoRow(
                label: '분석 완료',
                value: _formatDateTime(analysis['completed_at']?.toString()),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 94,
              child: Text(
                label,
                style: const TextStyle(color: radiologyMuted, fontSize: 13),
              ),
            ),
            Expanded(
              child: Text(
                value == null || value!.isEmpty ? '정보 없음' : value!,
                style: const TextStyle(
                  color: radiologyNavy,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: RadiologyInfoCard(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(message, textAlign: TextAlign.center),
                const SizedBox(height: 12),
                TextButton(onPressed: onRetry, child: const Text('다시 시도')),
              ],
            ),
          ),
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
      _ => status.isEmpty ? '정보 없음' : status,
    };

String? _analysisTypeLabel(String? analysisType) => switch (analysisType) {
      'HEMORRHAGIC_STROKE_CT' => 'CT 뇌출혈 분석',
      'ISCHEMIC_STROKE_DWI_ADC' => 'MRI 허혈성 뇌졸중 분석',
      'CEREBRAL_ANEURYSM_MRA' => 'MRA 뇌동맥류 분석',
      null || '' => null,
      _ => analysisType,
    };

String _aiJudgment(String? analysisType, Object? isPositive) {
  if (isPositive is! bool) {
    return '미산출';
  }
  return switch (analysisType) {
    'HEMORRHAGIC_STROKE_CT' => isPositive
        ? '출혈 의심 영역 검출'
        : '출혈 의심 영역 미검출',
    'ISCHEMIC_STROKE_DWI_ADC' => isPositive
        ? '허혈성 병변 의심 영역 검출'
        : '허혈성 병변 의심 영역 미검출',
    'CEREBRAL_ANEURYSM_MRA' => isPositive
        ? '뇌동맥류 의심 영역 검출'
        : '뇌동맥류 의심 영역 미검출',
    _ => '미산출',
  };
}

String? _ageValue(Object? value) => value == null ? null : '$value세';

String? _lesionCountValue(Object? value) =>
    value == null ? null : '${value.toString()}개';

String? _volumeValue(Object? value) =>
    value == null ? null : '${value.toString()} mL';

String? _confidenceValue(Object? value) {
  final parsed = switch (value) {
    num number => number.toDouble(),
    String text => double.tryParse(text),
    _ => null,
  };
  if (parsed == null) {
    return value?.toString();
  }
  if (parsed < 0 || parsed > 1) {
    return value.toString();
  }
  final percent = (parsed * 100).toStringAsFixed(2);
  return '${percent.replaceFirst(RegExp(r'\.?0+$'), '')}%';
}

String? _formatDateTime(String? value) {
  if (value == null || value.isEmpty) {
    return null;
  }
  final dateTime = DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.'
      '${dateTime.day.toString().padLeft(2, '0')} '
      '${dateTime.hour.toString().padLeft(2, '0')}:'
      '${dateTime.minute.toString().padLeft(2, '0')}';
}
