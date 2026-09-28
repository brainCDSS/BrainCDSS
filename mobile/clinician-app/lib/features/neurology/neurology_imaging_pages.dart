import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../analysis/radiology_analysis_detail_page.dart';
import '../analysis/radiology_analysis_requests_page.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'widgets/neurology_common_app_bar.dart';
import 'widgets/neurology_navigation_drawer.dart';

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
        appBar: NeurologyCommonAppBar(
          screenTitle: '영상검사 결과',
          onBack: () => Navigator.of(context).pop(),
          onNotifications: () => NeurologyNavigation.openNotifications(context),
        ),
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
  List<RadiologyAnalysisRequest> _analyses = const [];
  bool _loading = true;
  bool _openingAnalysis = false;
  String? _error;
  String? _analysisError;

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
      final study = _ImagingStudy.fromJson(responses[0]);
      final reports = (responses[1]['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _Report.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      List<RadiologyAnalysisRequest> analyses = const [];
      String? analysisError;
      try {
        final allAnalyses = await RadiologyAnalysisApi(widget.apiClient).list();
        analyses = allAnalyses
            .where((analysis) => analysis.studyId == study.id)
            .toList(growable: false);
      } on ClinicianApiException catch (error) {
        analysisError = error.message;
      } catch (_) {
        analysisError = 'AI 분석 결과를 불러오지 못했습니다.';
      }
      if (mounted) {
        setState(() {
          _study = study;
          _reports = reports;
          _analyses = analyses;
          _analysisError = analysisError;
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
        appBar: NeurologyCommonAppBar(
          screenTitle: '영상검사 상세',
          onBack: () => Navigator.of(context).pop(),
          onNotifications: () => NeurologyNavigation.openNotifications(context),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Padding(padding: const EdgeInsets.all(24), child: _RetryCard(message: _error!, onRetry: _load)))
                : ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      RadiologyInfoCard(
                        child: _StudySummary(
                          study: _study!,
                          analyses: _analyses,
                          analysisError: _analysisError,
                          openingAnalysis: _openingAnalysis,
                          onOpenAnalysis: _openAnalysisResult,
                        ),
                      ),
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

  Future<void> _openAnalysisResult(
    List<RadiologyAnalysisRequest> analyses,
  ) async {
    if (_openingAnalysis || analyses.isEmpty) return;
    final orderedAnalyses = [...analyses]
      ..sort(
        (first, second) => _analysisCompletedAt(second).compareTo(
          _analysisCompletedAt(first),
        ),
      );
    final latest = orderedAnalyses.first;
    final previous = orderedAnalyses.skip(1).toList(growable: false);
    final selected = await showModalBottomSheet<RadiologyAnalysisRequest>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.78,
          ),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
            children: [
              const Text(
                'AI 분석 결과 선택',
                style: TextStyle(
                  color: radiologyNavy,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 14),
              _LatestAnalysisCard(
                analysis: latest,
                onTap: () => Navigator.of(context).pop(latest),
              ),
              if (previous.isNotEmpty) ...[
                const SizedBox(height: 22),
                const Text(
                  '이전 분석 기록',
                  style: TextStyle(
                    color: radiologyNavy,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                ...previous.map(
                  (analysis) => _PreviousAnalysisTile(
                    analysis: analysis,
                    onTap: () => Navigator.of(context).pop(analysis),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
    if (!mounted || selected == null) return;

    setState(() => _openingAnalysis = true);
    try {
      final response = await widget.apiClient.get(
        '/api/v1/ai-analyses/${selected.analysisId}',
      );
      final request = RadiologyAnalysisRequest.fromJson(response);
      if (request.analysisId != selected.analysisId ||
          request.studyId != widget.studyId) {
        throw const _AnalysisNavigationException(
          '현재 검사와 연결된 AI 분석 결과를 확인할 수 없습니다.',
        );
      }
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => Scaffold(
            appBar: NeurologyCommonAppBar(
              screenTitle: 'AI 분석 결과',
              onBack: () => Navigator.of(context).pop(),
              onNotifications: () => NeurologyNavigation.openNotifications(context),
            ),
            body: RadiologyAnalysisDetailPage(
              apiClient: widget.apiClient,
              request: request,
            ),
          ),
        ),
      );
    } on _AnalysisNavigationException catch (error) {
      if (mounted) _showMessage(error.message);
    } on ClinicianApiException catch (error) {
      if (mounted) _showMessage(error.message);
    } catch (_) {
      if (mounted) _showMessage('AI 분석 결과를 열지 못했습니다.');
    } finally {
      if (mounted) setState(() => _openingAnalysis = false);
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}

class _AnalysisNavigationException implements Exception {
  const _AnalysisNavigationException(this.message);

  final String message;
}

class _LatestAnalysisCard extends StatelessWidget {
  const _LatestAnalysisCard({required this.analysis, required this.onTap});

  final RadiologyAnalysisRequest analysis;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFFF4F8FF),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFB9D4FA)),
            ),
            child: Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: const BoxDecoration(
                    color: Color(0xFFE1EEFF),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.insights_outlined,
                    color: radiologyBlue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const _AnalysisBadge(label: '최신 분석'),
                      const SizedBox(height: 7),
                      Text(
                        _analysisTypeDisplay(analysis.analysisType),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: radiologyNavy,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _formatDateTime(analysis.completedAt),
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
                const SizedBox(width: 8),
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    _AnalysisBadge(label: '분석 완료'),
                    SizedBox(height: 12),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '결과 보기',
                          style: TextStyle(
                            color: radiologyBlue,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Icon(
                          Icons.chevron_right_rounded,
                          color: radiologyBlue,
                          size: 18,
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );
}

class _PreviousAnalysisTile extends StatelessWidget {
  const _PreviousAnalysisTile({required this.analysis, required this.onTap});

  final RadiologyAnalysisRequest analysis;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              children: [
                const Icon(
                  Icons.history_rounded,
                  color: radiologyMuted,
                  size: 20,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _analysisTypeDisplay(analysis.analysisType),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: radiologyNavy,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _formatDateTime(analysis.completedAt),
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
                const SizedBox(width: 8),
                const _AnalysisBadge(label: '분석 완료'),
                const SizedBox(width: 4),
                const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
              ],
            ),
          ),
        ),
      );
}

class _AnalysisBadge extends StatelessWidget {
  const _AnalysisBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F1FF),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: radiologyBlue,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
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
    required this.latestAnalysisId,
    required this.currentReport,
    required this.criticalFinding,
  });

  factory _ImagingStudy.fromJson(Map<String, dynamic> json) {
    final patient = json['patient'] as Map?;
    final latestAnalysis = json['latest_analysis'] as Map?;
    final currentReport = json['current_report'] as Map?;
    final modalities = (json['modalities'] as List? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.isNotEmpty)
        .toSet();
    if (modalities.isEmpty) {
      for (final series in json['series'] as List? ?? const []) {
        if (series is Map) {
          final modality = series['modality']?.toString() ?? '';
          if (modality.isNotEmpty) modalities.add(modality);
        }
      }
    }
    return _ImagingStudy(
      id: json['study_id']?.toString() ?? '',
      accessionNumber: json['accession_number']?.toString() ?? '',
      studyDateTime: json['study_datetime']?.toString(),
      modalities: modalities.join(', '),
      status: json['status']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      latestAnalysis: latestAnalysis?['status']?.toString(),
      latestAnalysisId: latestAnalysis?['analysis_id']?.toString() ?? '',
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
  final String latestAnalysisId;
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
      author: author?['name']?.toString() ?? author?['user_id']?.toString(),
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
  const _StudySummary({
    required this.study,
    required this.analyses,
    required this.analysisError,
    required this.openingAnalysis,
    required this.onOpenAnalysis,
  });

  final _ImagingStudy study;
  final List<RadiologyAnalysisRequest> analyses;
  final String? analysisError;
  final bool openingAnalysis;
  final Future<void> Function(List<RadiologyAnalysisRequest>) onOpenAnalysis;

  @override
  Widget build(BuildContext context) {
    final completedAnalyses = analyses
        .where((analysis) => analysis.status == 'COMPLETED')
        .toList(growable: true);
    if (completedAnalyses.isEmpty &&
        study.latestAnalysisId.isNotEmpty &&
        study.latestAnalysis == 'COMPLETED') {
      completedAnalyses.add(
        RadiologyAnalysisRequest(
          analysisId: study.latestAnalysisId,
          studyId: study.id,
          analysisType: '',
          status: study.latestAnalysis!,
          stage: '',
          priority: '',
          requestedAt: null,
          completedAt: null,
          modelCode: '',
          modelVersion: '',
        ),
      );
    }
    final details = <_StudyInfoItem>[
      _StudyInfoItem('검사 일시', _formatDateTime(study.studyDateTime)),
      if (study.modalities.isNotEmpty)
        _StudyInfoItem('검사 종류', study.modalities),
      if (study.status.isNotEmpty)
        _StudyInfoItem('영상 상태', _studyStatusLabel(study.status)),
      if (study.latestAnalysis?.isNotEmpty == true)
        _StudyInfoItem(
          'AI 분석 상태',
          _analysisStatusLabel(study.latestAnalysis!),
        ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          study.patientName.isEmpty ? '환자 정보 없음' : study.patientName,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: radiologyNavy,
            fontSize: 19,
            fontWeight: FontWeight.w800,
          ),
        ),
        if (study.patientNo.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(
            study.patientNo,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: radiologyMuted),
          ),
        ],
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Divider(height: 1),
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            final isCompact = constraints.maxWidth < 360;
            final itemWidth = isCompact
                ? constraints.maxWidth
                : (constraints.maxWidth - 16) / 2;
            return Wrap(
              spacing: 16,
              runSpacing: 14,
              children: details
                  .map((item) => SizedBox(
                        width: itemWidth,
                        child: _StudyInfoCell(item: item),
                      ))
                  .toList(growable: false),
            );
          },
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: completedAnalyses.isEmpty || openingAnalysis
                ? null
                : () => onOpenAnalysis(completedAnalyses),
            icon: openingAnalysis
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.insights_outlined),
            label: Text(openingAnalysis ? 'AI 분석 결과 여는 중' : 'AI 분석 결과 보기'),
          ),
        ),
        if (completedAnalyses.isEmpty) ...[
          const SizedBox(height: 8),
          Text(
            analysisError ??
                (study.latestAnalysis?.isNotEmpty == true
                    ? 'AI 분석 결과가 아직 준비되지 않았습니다.'
                    : 'AI 분석 결과가 없습니다.'),
            style: const TextStyle(color: radiologyMuted, fontSize: 12),
          ),
        ],
      ],
    );
  }
}

class _ReportBody extends StatelessWidget {
  const _ReportBody({required this.report});
  final _Report report;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              RadiologyStatusChip(
                label: report.status == 'FINAL'
                    ? '확정'
                    : _reportStatusLabel(report.status),
                color: report.criticalFinding
                    ? const Color(0xFFB34B58)
                    : radiologyBlue,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _formatDateTime(report.finalizedAt),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.right,
                  style: const TextStyle(color: radiologyMuted, fontSize: 12),
                ),
              ),
            ],
          ),
          if (_hasText(report.author)) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                const Icon(Icons.person_outline_rounded,
                    size: 16, color: radiologyMuted),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    report.author?.trim() ?? '',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const Divider(height: 28),
          ],
          _ReportText(label: '소견', value: report.findings),
          const SizedBox(height: 16),
          _ReportText(label: '결론', value: report.impression),
          if (_hasText(report.recommendation)) ...[
            const SizedBox(height: 16),
            _ReportText(label: '권고', value: report.recommendation),
          ],
        ],
      );
}

class _ReportText extends StatelessWidget {
  const _ReportText({required this.label, required this.value});
  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 12)),
          const SizedBox(height: 4),
          Text(
            _hasText(value) ? value!.trim() : '정보 없음',
            softWrap: true,
            style: const TextStyle(color: radiologyNavy, height: 1.45),
          ),
        ],
      );
}

class _StudyInfoItem {
  const _StudyInfoItem(this.label, this.value);

  final String label;
  final String value;
}

class _StudyInfoCell extends StatelessWidget {
  const _StudyInfoCell({required this.item});

  final _StudyInfoItem item;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.label,
            style: const TextStyle(color: radiologyMuted, fontSize: 12),
          ),
          const SizedBox(height: 4),
          Text(
            item.value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: radiologyNavy,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
}

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(child: Column(children: [Text(message, textAlign: TextAlign.center), const SizedBox(height: 10), TextButton(onPressed: onRetry, child: const Text('다시 시도'))]));
}

String _studyStatusLabel(String status) => switch (status) {
      'AVAILABLE' => '조회 가능',
      _ => status,
    };

String _analysisStatusLabel(String status) => switch (status) {
      'COMPLETED' => '분석 완료',
      _ => status,
    };

String _analysisTypeDisplay(String type) => switch (type) {
      'ISCHEMIC_STROKE_DWI_ADC' => 'MRI 허혈성 뇌졸중 분석',
      'HEMORRHAGIC_STROKE_CT' => 'CT 뇌출혈 분석',
      'CEREBRAL_ANEURYSM_MRA' => 'MRA 뇌동맥류 분석',
      '' => 'AI 분석',
      _ => type,
    };

DateTime _analysisCompletedAt(RadiologyAnalysisRequest analysis) =>
    DateTime.tryParse(analysis.completedAt ?? '')?.toUtc() ??
    DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);

String _reportStatusLabel(String status) => switch (status) {
      'FINAL' => '판독 확정',
      _ => status,
    };

bool _hasText(String? value) => value != null && value.trim().isNotEmpty;

String _join(List<String> values) => values.where((value) => value.isNotEmpty).join(' · ');

String _formatDateTime(String? value) {
  final dateTime = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) return value ?? '정보 없음';
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
