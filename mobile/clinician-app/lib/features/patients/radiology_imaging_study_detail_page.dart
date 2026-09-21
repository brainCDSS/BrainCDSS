import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class RadiologyImagingStudyDetailPage extends StatefulWidget {
  const RadiologyImagingStudyDetailPage({
    super.key,
    required this.apiClient,
    required this.studyId,
  });

  final ClinicianApiClient apiClient;
  final String studyId;

  @override
  State<RadiologyImagingStudyDetailPage> createState() =>
      _RadiologyImagingStudyDetailPageState();
}

class _RadiologyImagingStudyDetailPageState
    extends State<RadiologyImagingStudyDetailPage> {
  Map<String, dynamic>? _study;
  List<Map<String, dynamic>> _reports = const [];
  Map<String, dynamic>? _analysisResult;
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
      final study = await widget.apiClient.get(
        '/api/v1/imaging-studies/${widget.studyId}',
      );
      List<Map<String, dynamic>> reports = const [];
      try {
        final response = await widget.apiClient.get(
          '/api/v1/imaging-studies/${widget.studyId}/reports',
        );
        reports = (response['results'] as List? ?? const [])
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false);
      } on ClinicianApiException {
        // Keep the study detail visible when reports are unavailable.
      }

      Map<String, dynamic>? analysisResult;
      final latestAnalysis = study['latest_analysis'] as Map?;
      final analysisId = latestAnalysis?['analysis_id']?.toString() ?? '';
      if (analysisId.isNotEmpty &&
          latestAnalysis?['status']?.toString() == 'COMPLETED') {
        try {
          analysisResult = await widget.apiClient.get(
            '/api/v1/ai-analyses/$analysisId/result',
          );
        } on ClinicianApiException {
          // A completed analysis can briefly have no result projection.
        }
      }

      if (mounted) {
        setState(() {
          _study = study;
          _reports = reports;
          _analysisResult = analysisResult;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '검사 정보를 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              TextButton(onPressed: _load, child: const Text('다시 시도')),
            ],
          ),
        ),
      );
    }

    final study = _study!;
    final patient = study['patient'] as Map?;
    final series = (study['series'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
    final modalities = series
        .map((item) => item['modality']?.toString() ?? '')
        .where((value) => value.isNotEmpty)
        .toSet()
        .join(', ');
    final instanceCount = series.fold<int>(
      0,
      (total, item) => total + _asInt(item['instance_count']),
    );
    final latestAnalysis = study['latest_analysis'] as Map?;
    final currentReport = study['current_report'] as Map?;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      children: [
        const RadiologySectionTitle(title: '검사 상세'),
        const SizedBox(height: 10),
        RadiologyInfoCard(
          child: Column(
            children: [
              _InfoRow(
                label: '검사 식별정보',
                value: _textOrNull(study['accession_number']) ??
                    _textOrNull(study['study_id']),
              ),
              _InfoRow(
                label: '검사 일시',
                value: _formatDateTime(study['study_datetime']?.toString()),
              ),
              _InfoRow(label: '검사 상태', value: _textOrNull(study['status'])),
              if (modalities.isNotEmpty)
                _InfoRow(label: 'Modality', value: modalities),
              _InfoRow(label: 'Series', value: '${series.length}개'),
              _InfoRow(label: 'Instance', value: '$instanceCount개'),
              _InfoRow(
                label: '최근 AI 분석',
                value: _textOrNull(latestAnalysis?['status']),
              ),
              _InfoRow(
                label: '현재 판독',
                value: _textOrNull(currentReport?['status']),
              ),
            ],
          ),
        ),
        if (patient != null) ...[
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '환자 요약'),
          const SizedBox(height: 8),
          RadiologyInfoCard(
            child: Column(
              children: [
                _InfoRow(label: '환자명', value: _textOrNull(patient['name'])),
                _InfoRow(
                  label: '환자번호',
                  value: _textOrNull(patient['patient_no']),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 14),
        const RadiologySectionTitle(title: '판독 결과'),
        const SizedBox(height: 8),
        if (_reports.isEmpty)
          const RadiologyEmptyState(
            icon: Icons.description_outlined,
            message: '등록된 판독 결과가 없습니다.',
          )
        else
          ..._reports.map(
            (report) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _ReportCard(report: report),
            ),
          ),
        const SizedBox(height: 14),
        const RadiologySectionTitle(title: 'AI 분석 결과'),
        const SizedBox(height: 8),
        if (_analysisResult == null)
          const RadiologyEmptyState(
            icon: Icons.analytics_outlined,
            message: '표시할 AI 분석 결과가 없습니다.',
          )
        else
          RadiologyInfoCard(
            child: Column(
              children: [
                _InfoRow(
                  label: 'AI 판정',
                  value: _analysisResult!['is_positive'] == null
                      ? null
                      : _analysisResult!['is_positive'] == true
                          ? '양성'
                          : '음성',
                ),
                _InfoRow(
                  label: '병변 개수',
                  value: _analysisResult!['lesion_count'] == null
                      ? null
                      : '${_analysisResult!['lesion_count']}개',
                ),
                _InfoRow(
                  label: '총 병변 부피',
                  value: _analysisResult!['total_volume_ml'] == null
                      ? null
                      : '${_analysisResult!['total_volume_ml']} mL',
                ),
                if (_analysisResult!['confidence'] != null)
                  _InfoRow(
                    label: '신뢰도',
                    value: _confidenceValue(_analysisResult!['confidence']),
                  ),
                _InfoRow(
                  label: '중증도',
                  value: _textOrNull(_analysisResult!['severity']),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({required this.report});

  final Map<String, dynamic> report;

  @override
  Widget build(BuildContext context) {
    final author = report['author'] as Map?;
    return RadiologyInfoCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _InfoRow(label: '판독 상태', value: _textOrNull(report['status'])),
          _InfoRow(label: '판독의', value: _textOrNull(author?['name'])),
          _InfoRow(
            label: '확정 시각',
            value: _formatDateTime(report['finalized_at']?.toString()) ??
                _formatDateTime(report['preliminary_at']?.toString()),
          ),
          if (_textOrNull(report['findings']) != null) ...[
            const SizedBox(height: 6),
            const Text(
              '판독 소견',
              style: TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              report['findings'].toString(),
              style: const TextStyle(color: radiologyMuted, height: 1.45),
            ),
          ],
          if (_textOrNull(report['impression']) != null) ...[
            const SizedBox(height: 10),
            const Text(
              '판독 결론',
              style: TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              report['impression'].toString(),
              style: const TextStyle(color: radiologyMuted, height: 1.45),
            ),
          ],
          if (_textOrNull(report['recommendation']) != null) ...[
            const SizedBox(height: 10),
            const Text(
              '권고 사항',
              style: TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              report['recommendation'].toString(),
              style: const TextStyle(color: radiologyMuted, height: 1.45),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) {
    if (value == null || value!.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
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
              value!,
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
}

int _asInt(Object? value) => value is num ? value.toInt() : 0;

String? _textOrNull(Object? value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}

String? _formatDateTime(String? value) {
  final parsed = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (parsed == null) {
    return _textOrNull(value);
  }
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${parsed.year}.${twoDigits(parsed.month)}.${twoDigits(parsed.day)} '
      '${twoDigits(parsed.hour)}:${twoDigits(parsed.minute)}';
}

String _confidenceValue(Object value) {
  final number = value is num ? value.toDouble() : double.tryParse('$value');
  if (number == null || number < 0 || number > 1) {
    return '$value';
  }
  return '${(number * 100).toStringAsFixed(2).replaceFirst(RegExp(r'\.?0+$'), '')}%';
}
