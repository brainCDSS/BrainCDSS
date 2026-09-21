import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class ImagingStudySummary {
  const ImagingStudySummary({
    required this.id,
    required this.accessionNumber,
    required this.patientName,
    required this.patientNo,
    required this.modalities,
    required this.scanType,
    required this.status,
    required this.seriesCount,
    required this.instanceCount,
    required this.analysisStatus,
    required this.reportStatus,
    required this.studyDateTime,
    required this.criticalFinding,
  });

  factory ImagingStudySummary.fromJson(Map<String, dynamic> json) {
    final patient = json['patient'] as Map?;
    final analysis = json['latest_analysis'] as Map?;
    final report = json['current_report'] as Map?;
    return ImagingStudySummary(
      id: json['study_id']?.toString() ?? '',
      accessionNumber: json['accession_number']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      modalities: (json['modalities'] as List? ?? const [])
          .map((value) => value.toString())
          .toList(growable: false),
      scanType: json['scan_type']?.toString(),
      status: json['status']?.toString() ?? '',
      seriesCount: (json['series_count'] as num?)?.toInt(),
      instanceCount: (json['instance_count'] as num?)?.toInt(),
      analysisStatus: analysis?['status']?.toString(),
      reportStatus: report?['status']?.toString(),
      studyDateTime: json['study_datetime']?.toString(),
      criticalFinding: json['critical_finding'] == true,
    );
  }

  final String id;
  final String accessionNumber;
  final String patientName;
  final String patientNo;
  final List<String> modalities;
  final String? scanType;
  final String status;
  final int? seriesCount;
  final int? instanceCount;
  final String? analysisStatus;
  final String? reportStatus;
  final String? studyDateTime;
  final bool criticalFinding;
}

class ImagingStudiesPage extends StatefulWidget {
  const ImagingStudiesPage({super.key, required this.apiClient});

  final ClinicianApiClient apiClient;

  @override
  State<ImagingStudiesPage> createState() => _ImagingStudiesPageState();
}

class _ImagingStudiesPageState extends State<ImagingStudiesPage> {
  List<ImagingStudySummary> _studies = const [];
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
          .map((item) => ImagingStudySummary.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(growable: false);
      if (mounted) setState(() => _studies = studies);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '영상 Worklist를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
            const RadiologySectionTitle(title: '영상 Worklist'),
            const SizedBox(height: 8),
            const Text(
              '저장된 Study 메타데이터와 AI·판독 상태를 표시합니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 13),
            ),
            const SizedBox(height: 16),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              RadiologyInfoCard(
                child: Column(children: [
                  Text(_error!, textAlign: TextAlign.center),
                  TextButton(onPressed: _load, child: const Text('다시 시도')),
                ]),
              )
            else if (_studies.isEmpty)
              const RadiologyEmptyState(
                icon: Icons.image_search_rounded,
                message: '접근 가능한 영상 Study가 없습니다.',
              )
            else
              ..._studies.map(
                (study) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _StudyCard(study: study),
                ),
              ),
          ],
        ),
      );
}

class _StudyCard extends StatelessWidget {
  const _StudyCard({required this.study});

  final ImagingStudySummary study;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Expanded(
                child: Text(
                  study.patientName.isEmpty ? '환자 정보 없음' : study.patientName,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              RadiologyStatusChip(
                label: study.status.isEmpty ? '상태 없음' : study.status,
                color: study.status == 'AVAILABLE'
                    ? const Color(0xFF208563)
                    : const Color(0xFFB46912),
              ),
            ]),
            const SizedBox(height: 8),
            Text(
              [
                if (study.patientNo.isNotEmpty) study.patientNo,
                if (study.accessionNumber.isNotEmpty) study.accessionNumber,
                if (study.scanType != null) study.scanType!,
                ...study.modalities,
              ].join(' · '),
              style: const TextStyle(color: radiologyMuted, fontSize: 12),
            ),
            const SizedBox(height: 8),
            Text(
              '시리즈 ${study.seriesCount ?? '-'} · 인스턴스 ${study.instanceCount ?? '-'} '
              '· AI ${study.analysisStatus ?? '없음'} · 판독 ${study.reportStatus ?? '없음'}',
              style: TextStyle(
                color: study.criticalFinding
                    ? const Color(0xFFB34B58)
                    : radiologyNavy,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
}
