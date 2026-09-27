import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'neurology_clinical_records_page.dart';
import 'neurology_consultation_create_page.dart';
import 'neurology_imaging_pages.dart';
import 'widgets/neurology_common_app_bar.dart';
import 'widgets/neurology_navigation_drawer.dart';

class NeurologyPatientsPage extends StatefulWidget {
  const NeurologyPatientsPage({
    super.key,
    required this.apiClient,
    required this.currentUserId,
    required this.onOpenConsultationDetail,
  });

  final ClinicianApiClient apiClient;
  final String currentUserId;
  final ValueChanged<String> onOpenConsultationDetail;

  @override
  State<NeurologyPatientsPage> createState() => _NeurologyPatientsPageState();
}

class _NeurologyPatientsPageState extends State<NeurologyPatientsPage> {
  Timer? _searchDebounce;
  List<_NeurologyPatient> _patients = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPatients();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    super.dispose();
  }

  Future<void> _loadPatients([String? search]) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await widget.apiClient.get(
        '/api/v1/patients',
        query: {
          if (search != null && search.isNotEmpty) 'search': search,
        },
      );
      final patients = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _NeurologyPatient.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(growable: false);
      if (mounted) {
        setState(() => _patients = patients);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = '환자 목록을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  void _onSearchChanged(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(
      const Duration(milliseconds: 350),
      () => _loadPatients(value.trim()),
    );
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '환자'),
          const SizedBox(height: 14),
          TextField(
            onChanged: _onSearchChanged,
            decoration: InputDecoration(
              hintText: '환자명 또는 환자번호 검색',
              prefixIcon: const Icon(Icons.search_rounded),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: radiologyBorder),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: radiologyBorder),
              ),
            ),
          ),
          const SizedBox(height: 18),
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_error != null)
            _RetryCard(message: _error!, onRetry: _loadPatients)
          else if (_patients.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.person_search_outlined,
              message: '표시할 환자가 없습니다.',
            )
          else
            ..._patients.map(
              (patient) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InkWell(
                  borderRadius: BorderRadius.circular(18),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => NeurologyPatientDetailPage(
                        apiClient: widget.apiClient,
                        patientId: patient.id,
                        currentUserId: widget.currentUserId,
                        onOpenConsultationDetail:
                            widget.onOpenConsultationDetail,
                      ),
                    ),
                  ),
                  child: RadiologyInfoCard(
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 23,
                          backgroundColor: const Color(0xFFEAF2FF),
                          child: Text(
                            patient.name.isEmpty
                                ? '?'
                                : patient.name.substring(0, 1),
                            style: const TextStyle(
                              color: radiologyBlue,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        const SizedBox(width: 13),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                patient.name.isEmpty
                                    ? '이름 정보 없음'
                                    : patient.name,
                                style: const TextStyle(
                                  color: radiologyNavy,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                patient.demographics,
                                style: const TextStyle(
                                  color: radiologyMuted,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(height: 7),
                              Text(
                                patient.status.isEmpty
                                    ? '상태 정보 없음'
                                    : patient.status,
                                style: const TextStyle(
                                  color: radiologyBlue,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Icon(
                          Icons.chevron_right_rounded,
                          color: radiologyMuted,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      );
}

class NeurologyPatientDetailPage extends StatefulWidget {
  const NeurologyPatientDetailPage({
    super.key,
    required this.apiClient,
    required this.patientId,
    required this.currentUserId,
    required this.onOpenConsultationDetail,
  });

  final ClinicianApiClient apiClient;
  final String patientId;
  final String currentUserId;
  final ValueChanged<String> onOpenConsultationDetail;

  @override
  State<NeurologyPatientDetailPage> createState() =>
      _NeurologyPatientDetailPageState();
}

class _NeurologyPatientDetailPageState
    extends State<NeurologyPatientDetailPage> {
  _NeurologyPatient? _patient;
  List<_PatientImagingStudy> _studies = const [];
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
        widget.apiClient.get('/api/v1/patients/${widget.patientId}'),
        widget.apiClient.get(
          '/api/v1/imaging-studies',
          query: {'patient_id': widget.patientId},
        ),
      ]);
      final studies = (responses[1]['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _PatientImagingStudy.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(growable: false);
      if (mounted) {
        setState(() {
          _patient = _NeurologyPatient.fromJson(responses[0]);
          _studies = studies;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = '환자 정보를 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _openConsultationCreate(_NeurologyPatient patient) async {
    final consultationId = await Navigator.of(context).push<String>(
      MaterialPageRoute<String>(
        builder: (_) => NeurologyConsultationCreatePage(
          apiClient: widget.apiClient,
          patientId: patient.id,
          patientName: patient.name,
          patientNo: patient.patientNo,
          demographics: patient.demographics,
        ),
      ),
    );
    if (!mounted || consultationId == null || consultationId.isEmpty) return;
    Navigator.of(context).pop();
    widget.onOpenConsultationDetail(consultationId);
  }

  @override
  Widget build(BuildContext context) {
    final patient = _patient;
    return Scaffold(
      appBar: NeurologyCommonAppBar(
        screenTitle: '환자 상세',
        onBack: () => Navigator.of(context).pop(),
        onNotifications: () => NeurologyNavigation.openNotifications(context),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: _RetryCard(message: _error!, onRetry: _load),
                  ),
                )
              : patient == null
                  ? const Center(
                      child: Text('환자 정보를 불러오지 못했습니다.'),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        _PatientSummary(patient: patient),
                        const SizedBox(height: 14),
                        const RadiologySectionTitle(title: '기본 정보'),
                        const SizedBox(height: 10),
                        RadiologyInfoCard(
                          child: Column(
                            children: [
                              _InfoRow(label: '생년월일', value: patient.birthDate),
                              _InfoRow(
                                label: '나이',
                                value: patient.estimatedAge == null
                                    ? null
                                    : '${patient.estimatedAge}세',
                              ),
                              _InfoRow(label: '성별', value: patient.sex),
                              _InfoRow(label: '연락처', value: patient.phone),
                              _InfoRow(label: '환자 상태', value: patient.status),
                            ],
                          ),
                        ),
                        const SizedBox(height: 14),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: () => _openConsultationCreate(patient),
                            icon: const Icon(Icons.send_outlined),
                            label: const Text('협진 요청'),
                          ),
                        ),
                        const SizedBox(height: 18),
                        NeurologyPatientClinicalRecordsSection(
                          apiClient: widget.apiClient,
                          patientId: widget.patientId,
                          currentUserId: widget.currentUserId,
                          showStatusBadge: false,
                        ),
                        const SizedBox(height: 18),
                        const RadiologySectionTitle(title: '최근 영상검사'),
                        const SizedBox(height: 10),
                        if (_studies.isEmpty)
                          const RadiologyEmptyState(
                            icon: Icons.image_search_outlined,
                            message: '조회 가능한 영상검사가 없습니다.',
                          )
                        else
                          ..._studies.map(
                            (study) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(18),
                                onTap: () => Navigator.of(context).push(
                                  MaterialPageRoute<void>(
                                    builder: (_) =>
                                        NeurologyImagingStudyDetailPage(
                                      apiClient: widget.apiClient,
                                      studyId: study.id,
                                    ),
                                  ),
                                ),
                                child: RadiologyInfoCard(
                                  child: Row(
                                    children: [
                                      Icon(
                                        study.criticalFinding
                                            ? Icons.warning_amber_rounded
                                            : Icons.image_outlined,
                                        color: study.criticalFinding
                                            ? const Color(0xFFB34B58)
                                            : radiologyBlue,
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              '검사 종류  ${study.modalities.isEmpty ? '정보 없음' : study.modalities}',
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: const TextStyle(
                                                color: radiologyNavy,
                                                fontWeight: FontWeight.w800,
                                              ),
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              '검사 일시  ${_formatDateTime(study.studyDateTime)}',
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: const TextStyle(
                                                color: radiologyMuted,
                                                fontSize: 13,
                                              ),
                                            ),
                                            if (study.accessionNumber
                                                .isNotEmpty) ...[
                                              const SizedBox(height: 3),
                                              Text(
                                                '검사번호  ${study.accessionNumber}',
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                  color: radiologyMuted,
                                                  fontSize: 12,
                                                ),
                                              ),
                                            ],
                                            const SizedBox(height: 8),
                                            Wrap(
                                              spacing: 6,
                                              runSpacing: 6,
                                              children: [
                                                _ImagingStudyStatusBadge(
                                                  value: _imagingStatusLabel(
                                                      study.status),
                                                ),
                                                if (study.latestAnalysis
                                                        ?.isNotEmpty ==
                                                    true)
                                                  _ImagingStudyStatusBadge(
                                                    value:
                                                        _aiAnalysisStatusLabel(
                                                      study.latestAnalysis!,
                                                    ),
                                                  ),
                                                if (study.currentReport
                                                        ?.isNotEmpty ==
                                                    true)
                                                  _ImagingStudyStatusBadge(
                                                    value: _reportStatusLabel(
                                                      study.currentReport!,
                                                    ),
                                                  ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                      const Icon(
                                        Icons.chevron_right_rounded,
                                        color: radiologyMuted,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
    );
  }
}

class _NeurologyPatient {
  const _NeurologyPatient({
    required this.id,
    required this.patientNo,
    required this.name,
    required this.birthDate,
    required this.estimatedAge,
    required this.sex,
    required this.phone,
    required this.status,
  });

  factory _NeurologyPatient.fromJson(Map<String, dynamic> json) =>
      _NeurologyPatient(
        id: json['id']?.toString() ?? '',
        patientNo: json['patient_no']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
        birthDate: json['birth_date']?.toString(),
        estimatedAge: json['estimated_age'] as int?,
        sex: json['sex']?.toString(),
        phone: json['phone']?.toString(),
        status: json['status']?.toString() ?? '',
      );

  final String id;
  final String patientNo;
  final String name;
  final String? birthDate;
  final int? estimatedAge;
  final String? sex;
  final String? phone;
  final String status;

  String get demographics {
    final values = <String>[
      if (sex != null && sex!.isNotEmpty) sex!,
      if (estimatedAge != null) '${estimatedAge}세',
      if (patientNo.isNotEmpty) patientNo,
    ];
    return values.isEmpty ? '기본 정보 없음' : values.join(' · ');
  }
}

class _PatientImagingStudy {
  const _PatientImagingStudy({
    required this.id,
    required this.accessionNumber,
    required this.studyDateTime,
    required this.modalities,
    required this.status,
    required this.latestAnalysis,
    required this.currentReport,
    required this.criticalFinding,
  });

  factory _PatientImagingStudy.fromJson(Map<String, dynamic> json) {
    final latestAnalysis = json['latest_analysis'] as Map?;
    final currentReport = json['current_report'] as Map?;
    return _PatientImagingStudy(
      id: json['study_id']?.toString() ?? '',
      accessionNumber: json['accession_number']?.toString() ?? '',
      studyDateTime: json['study_datetime']?.toString(),
      modalities: (json['modalities'] as List? ?? const [])
          .map((item) => item.toString())
          .join(', '),
      status: json['status']?.toString() ?? '',
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
  final String? latestAnalysis;
  final String? currentReport;
  final bool criticalFinding;

}

String _imagingStatusLabel(String status) => switch (status) {
      'AVAILABLE' => '조회 가능',
      _ => status,
    };

String _aiAnalysisStatusLabel(String status) => switch (status) {
      'COMPLETED' => 'AI 분석 완료',
      'PROCESSING' => 'AI 분석 중',
      'QUEUED' => 'AI 분석 대기',
      'FAILED' => 'AI 분석 실패',
      _ => status,
    };

String _reportStatusLabel(String status) => switch (status) {
      'FINAL' => '판독 확정',
      _ => status,
    };

class _ImagingStudyStatusBadge extends StatelessWidget {
  const _ImagingStudyStatusBadge({
    required this.value,
  });

  final String value;

  @override
  Widget build(BuildContext context) => RadiologyStatusChip(
        label: value,
        color: value == 'AI 분석 실패'
            ? const Color(0xFFB34B58)
            : radiologyBlue,
      );
}

class _PatientSummary extends StatelessWidget {
  const _PatientSummary({required this.patient});

  final _NeurologyPatient patient;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: const Color(0xFFEAF2FF),
              child: Text(
                patient.name.isEmpty ? '?' : patient.name.substring(0, 1),
                style: const TextStyle(
                  color: radiologyBlue,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    patient.name.isEmpty ? '이름 정보 없음' : patient.name,
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    patient.patientNo.isEmpty
                        ? '환자번호 정보 없음'
                        : patient.patientNo,
                    style: const TextStyle(color: radiologyMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(
          children: [
            SizedBox(
              width: 88,
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

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});

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

String _formatDateTime(String? value) {
  final dateTime = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) return '정보 없음';
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
