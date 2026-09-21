import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyImagingStudiesPage extends StatefulWidget {
  const NeurologyImagingStudiesPage({super.key, required this.apiClient});

  final ClinicianApiClient apiClient;

  @override
  State<NeurologyImagingStudiesPage> createState() =>
      _NeurologyImagingStudiesPageState();
}

class _NeurologyImagingStudiesPageState extends State<NeurologyImagingStudiesPage> {
  List<_ImagingStudy> _studies = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await widget.apiClient.get('/api/v1/imaging-studies');
      final studies = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _ImagingStudy.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) setState(() => _studies = studies);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '영상검사 목록을 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('영상검사 결과')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
            const Text('접근 권한이 있는 영상검사와 판독 결과를 확인합니다.',
                style: TextStyle(color: radiologyMuted, fontSize: 13)),
            const SizedBox(height: 16),
            if (_loading)
              const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()))
            else if (_error != null)
              _RetryCard(message: _error!, onRetry: _load)
            else if (_studies.isEmpty)
              const RadiologyEmptyState(icon: Icons.image_search_outlined, message: '조회 가능한 영상검사가 없습니다.')
            else
              ..._studies.map((study) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(18),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => NeurologyImagingStudyDetailPage(
                          apiClient: widget.apiClient,
                          studyId: study.id,
                        ),
                      )),
                      child: RadiologyInfoCard(
                        child: Row(children: [
                          const Icon(Icons.image_outlined, color: radiologyBlue),
                          const SizedBox(width: 12),
                          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(study.patientName.isEmpty ? '환자 정보 없음' : study.patientName,
                                style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800)),
                            const SizedBox(height: 4),
                            Text(_join([study.modalities, _formatDateTime(study.studyDateTime)]),
                                style: const TextStyle(color: radiologyMuted, fontSize: 13)),
                            const SizedBox(height: 4),
                            Text(study.accessionNumber.isEmpty ? study.status : study.accessionNumber,
                                style: const TextStyle(color: radiologyMuted, fontSize: 12)),
                          ])),
                          const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
                        ]),
                      ),
                    ),
                  )),
          ],
        ),
      );
}

class NeurologyImagingStudyDetailPage extends StatefulWidget {
  const NeurologyImagingStudyDetailPage({
    super.key,
    required this.apiClient,
    required this.studyId,
  });

  final ClinicianApiClient apiClient;
  final String studyId;

  @override
  State<NeurologyImagingStudyDetailPage> createState() =>
      _NeurologyImagingStudyDetailPageState();
}

class _NeurologyImagingStudyDetailPageState extends State<NeurologyImagingStudyDetailPage> {
  _ImagingStudy? _study;
  List<_Report> _reports = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final responses = await Future.wait([
        widget.apiClient.get('/api/v1/imaging-studies/${widget.studyId}'),
        widget.apiClient.get('/api/v1/imaging-studies/${widget.studyId}/reports', query: {'current_only': 'true'}),
      ]);
      final reports = (responses[1]['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _Report.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) {
        setState(() {
          _study = _ImagingStudy.fromJson(responses[0]);
          _reports = reports;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '영상검사 정보를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('영상검사 상세')),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Padding(padding: const EdgeInsets.all(24), child: _RetryCard(message: _error!, onRetry: _load)))
                : ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      RadiologyInfoCard(child: _StudySummary(study: _study!)),
                      const SizedBox(height: 16),
                      const RadiologySectionTitle(title: '최종 판독 결과'),
                      const SizedBox(height: 10),
                      if (_reports.isEmpty)
                        const RadiologyEmptyState(icon: Icons.description_outlined, message: '등록된 최종 판독 결과가 없습니다.')
                      else
                        ..._reports.map((report) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: RadiologyInfoCard(child: _ReportBody(report: report)),
                            )),
                    ],
                  ),
      );
}

class _ImagingStudy {
  const _ImagingStudy({
    required this.id,
    required this.accessionNumber,
    required this.studyDateTime,
    required this.modalities,
    required this.status,
    required this.patientName,
    required this.patientNo,
    required this.latestAnalysis,
    required this.currentReport,
    required this.criticalFinding,
  });

  factory _ImagingStudy.fromJson(Map<String, dynamic> json) {
    final patient = json['patient'] as Map?;
    final latestAnalysis = json['latest_analysis'] as Map?;
    final currentReport = json['current_report'] as Map?;
    return _ImagingStudy(
      id: json['study_id']?.toString() ?? '',
      accessionNumber: json['accession_number']?.toString() ?? '',
      studyDateTime: json['study_datetime']?.toString(),
      modalities: (json['modalities'] as List? ?? const []).map((item) => item.toString()).join(', '),
      status: json['status']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      latestAnalysis: latestAnalysis?['status']?.toString(),
      currentReport: currentReport?['status']?.toString(),
      criticalFinding: json['critical_finding'] == true,
    );
  }

  final String id;
  final String accessionNumber;
  final String? studyDateTime;
  final String modalities;
  final String status;
  final String patientName;
  final String patientNo;
  final String? latestAnalysis;
  final String? currentReport;
  final bool criticalFinding;
}

class _Report {
  const _Report({
    required this.status,
    required this.findings,
    required this.impression,
    required this.recommendation,
    required this.author,
    required this.finalizedAt,
    required this.criticalFinding,
  });

  factory _Report.fromJson(Map<String, dynamic> json) {
    final author = json['author'] as Map?;
    return _Report(
      status: json['status']?.toString() ?? '',
      findings: json['findings']?.toString(),
      impression: json['impression']?.toString(),
      recommendation: json['recommendation']?.toString(),
      author: author?['name']?.toString(),
      finalizedAt: json['finalized_at']?.toString(),
      criticalFinding: json['critical_finding'] == true,
    );
  }

  final String status;
  final String? findings;
  final String? impression;
  final String? recommendation;
  final String? author;
  final String? finalizedAt;
  final bool criticalFinding;
}

class _StudySummary extends StatelessWidget {
  const _StudySummary({required this.study});
  final _ImagingStudy study;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(study.patientName.isEmpty ? '환자 정보 없음' : study.patientName, style: const TextStyle(color: radiologyNavy, fontSize: 19, fontWeight: FontWeight.w800)),
        if (study.patientNo.isNotEmpty) ...[const SizedBox(height: 4), Text(study.patientNo, style: const TextStyle(color: radiologyMuted))],
        const SizedBox(height: 14),
        _Line(label: '검사 일시', value: _formatDateTime(study.studyDateTime)),
        _Line(label: '검사 종류', value: study.modalities),
        _Line(label: '상태', value: study.status),
        if (study.latestAnalysis != null && study.latestAnalysis!.isNotEmpty)
          _Line(label: 'AI 분석', value: study.latestAnalysis!),
        if (study.currentReport != null && study.currentReport!.isNotEmpty)
          _Line(label: '현재 판독', value: study.currentReport!),
        if (study.criticalFinding)
          const _Line(label: '중요 소견', value: '있음'),
      ]);
}

class _ReportBody extends StatelessWidget {
  const _ReportBody({required this.report});
  final _Report report;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [RadiologyStatusChip(label: report.status.isEmpty ? '판독' : report.status, color: report.criticalFinding ? const Color(0xFFB34B58) : radiologyBlue), const Spacer(), Text(_formatDateTime(report.finalizedAt), style: const TextStyle(color: radiologyMuted, fontSize: 12))]),
        if (_hasText(report.author)) _ReportText(label: '판독자', value: report.author),
        _ReportText(label: '소견', value: report.findings),
        _ReportText(label: '결론', value: report.impression),
        if (_hasText(report.recommendation)) _ReportText(label: '권고', value: report.recommendation),
      ]);
}

class _ReportText extends StatelessWidget {
  const _ReportText({required this.label, required this.value});
  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 12)), const SizedBox(height: 4), Text(_hasText(value) ? value!.trim() : '정보 없음', style: const TextStyle(color: radiologyNavy, height: 1.45))]));
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 8), child: Row(children: [SizedBox(width: 78, child: Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 13))), Expanded(child: Text(value.isEmpty ? '정보 없음' : value, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w700)))]));
}

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(child: Column(children: [Text(message, textAlign: TextAlign.center), const SizedBox(height: 10), TextButton(onPressed: onRetry, child: const Text('다시 시도'))]));
}

bool _hasText(String? value) => value != null && value.trim().isNotEmpty;

String _join(List<String> values) => values.where((value) => value.isNotEmpty).join(' · ');

String _formatDateTime(String? value) {
  final dateTime = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) return value ?? '정보 없음';
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
