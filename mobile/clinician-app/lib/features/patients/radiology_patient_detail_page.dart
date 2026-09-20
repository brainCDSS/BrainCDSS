import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';

class _PatientDetail {
  const _PatientDetail({
    required this.name,
    required this.patientNo,
    required this.birthDate,
    required this.estimatedAge,
    required this.sex,
    required this.phone,
    required this.emergencyContact,
    required this.pregnancyStatus,
    required this.status,
  });

  factory _PatientDetail.fromJson(Map<String, dynamic> json) {
    final birthDate = json['birth_date']?.toString();

    return _PatientDetail(
      name: json['name']?.toString() ?? '',
      patientNo: json['patient_no']?.toString() ?? '',
      birthDate: birthDate,
      estimatedAge: _toInt(json['estimated_age']) ??
          _calculateAgeFromBirthDate(birthDate),
      sex: json['sex']?.toString(),
      phone: json['phone']?.toString(),
      emergencyContact: json['emergency_contact']?.toString(),
      pregnancyStatus: json['pregnancy_status']?.toString(),
      status: json['status']?.toString() ?? '',
    );
  }

  final String name;
  final String patientNo;
  final String? birthDate;
  final int? estimatedAge;
  final String? sex;
  final String? phone;
  final String? emergencyContact;
  final String? pregnancyStatus;
  final String status;
}

class _ImagingStudyItem {
  const _ImagingStudyItem({
    required this.studyId,
    required this.accessionNumber,
    required this.studyDatetime,
    required this.modalities,
    required this.status,
    required this.scanType,
    required this.latestAnalysisId,
    required this.latestAnalysisStatus,
    required this.reportStatus,
    required this.criticalFinding,
  });

  factory _ImagingStudyItem.fromJson(Map<String, dynamic> json) {
    final latestAnalysis = _asMap(json['latest_analysis']);
    final currentReport = _asMap(json['current_report']);

    return _ImagingStudyItem(
      studyId: json['study_id']?.toString() ?? '',
      accessionNumber: json['accession_number']?.toString(),
      studyDatetime: json['study_datetime']?.toString(),
      modalities: (json['modalities'] as List? ?? const [])
          .map((value) => value.toString())
          .toList(),
      status: json['status']?.toString() ?? '',
      scanType: json['scan_type']?.toString(),
      latestAnalysisId: latestAnalysis?['analysis_id']?.toString(),
      latestAnalysisStatus: latestAnalysis?['status']?.toString(),
      reportStatus: currentReport?['status']?.toString(),
      criticalFinding: json['critical_finding'] == true,
    );
  }

  final String studyId;
  final String? accessionNumber;
  final String? studyDatetime;
  final List<String> modalities;
  final String status;
  final String? scanType;
  final String? latestAnalysisId;
  final String? latestAnalysisStatus;
  final String? reportStatus;
  final bool criticalFinding;
}

class _AiAnalysisSummary {
  const _AiAnalysisSummary({
    required this.analysisId,
    required this.analysisType,
    required this.status,
    required this.stage,
    required this.requestedAt,
    required this.isPositive,
    required this.totalVolumeMl,
  });

  factory _AiAnalysisSummary.fromJson(Map<String, dynamic> json) {
    final resultSummary = _asMap(json['result_summary']);

    return _AiAnalysisSummary(
      analysisId: json['analysis_id']?.toString() ?? '',
      analysisType: json['analysis_type']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      stage: json['stage']?.toString(),
      requestedAt: json['requested_at']?.toString(),
      isPositive: resultSummary?['is_positive'] as bool?,
      totalVolumeMl: _toDouble(resultSummary?['total_volume_ml']),
    );
  }

  final String analysisId;
  final String analysisType;
  final String status;
  final String? stage;
  final String? requestedAt;
  final bool? isPositive;
  final double? totalVolumeMl;
}

class _ConsultationSummary {
  const _ConsultationSummary({
    required this.consultationId,
    required this.type,
    required this.priority,
    required this.status,
    required this.requestedAt,
    required this.requestedByName,
    required this.requestedByDepartment,
    required this.reason,
  });

  factory _ConsultationSummary.fromJson(Map<String, dynamic> json) {
    final requestedBy = _asMap(json['requested_by']);

    return _ConsultationSummary(
      consultationId:
          json['consultation_id']?.toString() ?? json['id']?.toString() ?? '',
      type: json['type']?.toString() ??
          json['consultation_type']?.toString() ??
          '',
      priority: json['priority']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      requestedAt: json['requested_at']?.toString(),
      requestedByName: requestedBy?['name']?.toString(),
      requestedByDepartment: requestedBy?['department']?.toString(),
      reason: json['reason']?.toString(),
    );
  }

  final String consultationId;
  final String type;
  final String priority;
  final String status;
  final String? requestedAt;
  final String? requestedByName;
  final String? requestedByDepartment;
  final String? reason;
}

class RadiologyPatientDetailPage extends StatefulWidget {
  const RadiologyPatientDetailPage({
    super.key,
    required this.apiClient,
    required this.patientId,
  });

  final ClinicianApiClient apiClient;
  final String patientId;

  @override
  State<RadiologyPatientDetailPage> createState() =>
      _RadiologyPatientDetailPageState();
}

class _RadiologyPatientDetailPageState
    extends State<RadiologyPatientDetailPage> {
  _PatientDetail? _patient;

  List<_ImagingStudyItem> _studies = [];
  _AiAnalysisSummary? _latestAnalysis;
  List<_ConsultationSummary> _consultations = [];

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
      // 1. 환자 기본정보
      final patientResponse = await widget.apiClient.get(
        '/api/v1/patients/${widget.patientId}',
      );

      final patient = _PatientDetail.fromJson(patientResponse);

      // 2. 최근 영상검사
      List<_ImagingStudyItem> studies = [];

      try {
        final studiesResponse = await widget.apiClient.get(
          '/api/v1/imaging-studies?patient_id=${widget.patientId}',
        );

        studies = (studiesResponse['results'] as List? ?? const [])
            .whereType<Map>()
            .map(
              (item) => _ImagingStudyItem.fromJson(
                Map<String, dynamic>.from(item),
              ),
            )
            .toList();

        studies.sort((a, b) {
          final aDate = DateTime.tryParse(a.studyDatetime ?? '');
          final bDate = DateTime.tryParse(b.studyDatetime ?? '');

          if (aDate == null && bDate == null) {
            return 0;
          }

          if (aDate == null) {
            return 1;
          }

          if (bDate == null) {
            return -1;
          }

          return bDate.compareTo(aDate);
        });
      } catch (_) {
        // 검사 조회가 실패해도 환자 기본정보는 표시
      }

      // 3. 최근 검사 기준 AI 분석
      _AiAnalysisSummary? latestAnalysis;

      for (final study in studies) {
        if (study.studyId.isEmpty) {
          continue;
        }

        try {
          final aiResponse = await widget.apiClient.get(
            '/api/v1/imaging-studies/${study.studyId}/ai-analyses',
          );

          final analyses = (aiResponse['results'] as List? ?? const [])
              .whereType<Map>()
              .map(
                (item) => _AiAnalysisSummary.fromJson(
                  Map<String, dynamic>.from(item),
                ),
              )
              .toList();

          if (analyses.isNotEmpty) {
            analyses.sort((a, b) {
              final aDate = DateTime.tryParse(a.requestedAt ?? '');
              final bDate = DateTime.tryParse(b.requestedAt ?? '');

              if (aDate == null && bDate == null) {
                return 0;
              }

              if (aDate == null) {
                return 1;
              }

              if (bDate == null) {
                return -1;
              }

              return bDate.compareTo(aDate);
            });

            latestAnalysis = analyses.first;
            break;
          }
        } catch (_) {
          // 해당 검사에 AI 분석이 없으면 다음 검사 확인
        }
      }

      // 4. 현재 환자의 협진
      List<_ConsultationSummary> consultations = [];

      try {
        final consultationResponse = await widget.apiClient.get(
          '/api/v1/consultations',
        );

        consultations = (consultationResponse['results'] as List? ?? const [])
            .whereType<Map>()
            .map(
              (item) => Map<String, dynamic>.from(item),
            )
            .where((item) {
              final patientSummary = _asMap(
                item['patient_summary'],
              );

              return patientSummary?['id']?.toString() == widget.patientId;
            })
            .map(_ConsultationSummary.fromJson)
            .toList();

        consultations.sort((a, b) {
          final aDate = DateTime.tryParse(a.requestedAt ?? '');
          final bDate = DateTime.tryParse(b.requestedAt ?? '');

          if (aDate == null && bDate == null) {
            return 0;
          }

          if (aDate == null) {
            return 1;
          }

          if (bDate == null) {
            return -1;
          }

          return bDate.compareTo(aDate);
        });
      } catch (_) {
        // 협진 조회 실패 시에도 환자 상세는 유지
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _patient = patient;
        _studies = studies;
        _latestAnalysis = latestAnalysis;
        _consultations = consultations;
      });
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() {
          _errorMessage = error.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _errorMessage = '환자 정보를 불러오지 못했습니다.';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => _isLoading
            ? const Center(
                child: CircularProgressIndicator(),
              )
            : _errorMessage != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _errorMessage!,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 12),
                          TextButton(
                            onPressed: _load,
                            child: const Text('다시 시도'),
                          ),
                        ],
                      ),
                    ),
                  )
                : _PatientDetailBody(
                    apiClient: widget.apiClient,
                    patient: _patient!,
                    studies: _studies,
                    latestAnalysis: _latestAnalysis,
                    consultations: _consultations,
                  );
}

class _PatientDetailBody extends StatelessWidget {
  const _PatientDetailBody({
    required this.apiClient,
    required this.patient,
    required this.studies,
    required this.latestAnalysis,
    required this.consultations,
  });

  final ClinicianApiClient apiClient;
  final _PatientDetail patient;
  final List<_ImagingStudyItem> studies;
  final _AiAnalysisSummary? latestAnalysis;
  final List<_ConsultationSummary> consultations;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // 환자 요약
          RadiologyInfoCard(
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
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              patient.name.isEmpty ? '이름 정보 없음' : patient.name,
                              style: const TextStyle(
                                color: radiologyNavy,
                                fontSize: 20,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          if (patient.status.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            _StatusChip(
                              label: patient.status,
                              color: radiologyBlue,
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        patient.patientNo.isEmpty
                            ? '환자번호 정보 없음'
                            : patient.patientNo,
                        style: const TextStyle(
                          color: radiologyMuted,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        [
                          if (patient.estimatedAge != null)
                            '${patient.estimatedAge}세',
                          if (_hasValue(patient.sex)) patient.sex!,
                          if (_hasValue(patient.birthDate)) patient.birthDate!,
                        ].join(' · '),
                        style: const TextStyle(
                          color: radiologyMuted,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 18),

          // 기본 정보
          const RadiologySectionTitle(
            title: '기본 정보',
          ),
          const SizedBox(height: 10),

          RadiologyInfoCard(
            child: Column(
              children: [
              _InfoRow(
                label: '연락처',
                  value: patient.phone,
                ),
                if (_hasValue(patient.emergencyContact))
                  _InfoRow(
                    label: '응급연락처',
                    value: patient.emergencyContact,
                  ),
                if (_hasValue(patient.pregnancyStatus))
                  _InfoRow(
                    label: '임신 여부',
                    value: _pregnancyLabel(
                      patient.pregnancyStatus,
                    ),
                  ),
                _InfoRow(
                  label: '환자 상태',
                  value: patient.status,
                ),
              ],
            ),
          ),

          const SizedBox(height: 18),

          // 최근 검사
          const RadiologySectionTitle(
            title: '최근 검사',
          ),
          const SizedBox(height: 10),

          RadiologyInfoCard(
            padding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 6,
            ),
            child: studies.isEmpty
                ? const _EmptySection(
                    message: '확인 가능한 검사 정보가 없습니다.',
                  )
                : Column(
                    children: studies
                        .take(3)
                        .map(
                          (study) => _StudyRow(
                            study: study,
                            onTap: study.studyId.isEmpty
                                ? null
                                : () => RadiologyNavigation.openStudy(
                                      study.studyId,
                                    ),
                          ),
                        )
                        .toList(),
                  ),
          ),

          const SizedBox(height: 18),

          // AI 분석 결과
          const RadiologySectionTitle(
            title: 'AI 분석 결과',
          ),
          const SizedBox(height: 10),

          RadiologyInfoCard(
            child: latestAnalysis == null
                ? const _EmptySection(
                    message: '확인 가능한 AI 분석 결과가 없습니다.',
                  )
                : _AiAnalysisCard(
                    analysis: latestAnalysis!,
                  ),
          ),

          const SizedBox(height: 18),

          // 협진
          const RadiologySectionTitle(
            title: '협진',
          ),
          const SizedBox(height: 10),

          RadiologyInfoCard(
            child: consultations.isEmpty
                ? const _EmptySection(
                    message: '현재 환자와 관련된 협진이 없습니다.',
                  )
                : Column(
                    children: consultations
                        .take(3)
                        .map(
                          (consultation) => _ConsultationRow(
                            consultation: consultation,
                            onTap: consultation.consultationId.isEmpty
                                ? null
                                : () {
                                    RadiologyNavigation.openConsultation(
                                      consultation.consultationId,
                                    );
                                  },
                          ),
                        )
                        .toList(),
                  ),
          ),

          const SizedBox(height: 24),
        ],
      );
}

class _StudyRow extends StatelessWidget {
  const _StudyRow({
    required this.study,
    required this.onTap,
  });

  final _ImagingStudyItem study;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final modality = study.scanType ??
        (study.modalities.isNotEmpty ? study.modalities.join(', ') : '검사');

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          vertical: 12,
        ),
        child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: const Color(0xFFEAF2FF),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(
              Icons.description_outlined,
              color: radiologyBlue,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _studyTitle(study),
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  [
                    _formatDateTime(study.studyDatetime),
                    modality,
                  ].where((value) => value.isNotEmpty).join(' · '),
                  style: const TextStyle(
                    color: radiologyMuted,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          _StatusChip(
            label: _reportStatusLabel(
              study.reportStatus,
              study.status,
            ),
            color: _reportStatusColor(
              study.reportStatus,
            ),
          ),
          const SizedBox(width: 4),
          const Icon(
            Icons.chevron_right,
            color: radiologyMuted,
            size: 22,
          ),
        ],
        ),
      ),
    );
  }
}

class _AiAnalysisCard extends StatelessWidget {
  const _AiAnalysisCard({
    required this.analysis,
  });

  final _AiAnalysisSummary analysis;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: const Color(0xFFEAF2FF),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(
                  Icons.psychology_alt_outlined,
                  color: radiologyBlue,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _analysisTypeLabel(
                        analysis.analysisType,
                      ),
                      style: const TextStyle(
                        color: radiologyNavy,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatDateTime(
                        analysis.requestedAt,
                      ),
                      style: const TextStyle(
                        color: radiologyMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              _StatusChip(
                label: _analysisStatusLabel(
                  analysis.status,
                ),
                color: analysis.status == 'COMPLETED'
                    ? const Color(0xFF16A36A)
                    : radiologyBlue,
              ),
              const SizedBox(width: 4),
              const Icon(
                Icons.chevron_right,
                color: radiologyMuted,
                size: 22,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF2F7FF),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'AI 판정',
                  style: TextStyle(
                    color: radiologyBlue,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  _analysisFinding(
                    analysis.analysisType,
                    analysis.isPositive,
                  ),
                  style: const TextStyle(
                    color: radiologyNavy,
                  ),
                ),
              ],
            ),
          ),
          if (analysis.totalVolumeMl != null) ...[
            const SizedBox(height: 10),
            _InfoRow(
              label: '총 병변 부피',
              value: '${analysis.totalVolumeMl!.toStringAsFixed(4)} mL',
            ),
          ],
        ],
      );
}

class _ConsultationRow extends StatelessWidget {
  const _ConsultationRow({
    required this.consultation,
    required this.onTap,
  });

  final _ConsultationSummary consultation;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: 8,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: const Color(0xFFEAF2FF),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.groups_outlined,
                color: radiologyBlue,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _consultationTypeLabel(
                      consultation.type,
                    ),
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  if (_hasValue(
                    consultation.requestedByName,
                  ))
                    Text(
                      [
                        '요청자 ${consultation.requestedByName}',
                        if (_hasValue(
                          consultation.requestedByDepartment,
                        ))
                          consultation.requestedByDepartment!,
                      ].join(' · '),
                      style: const TextStyle(
                        color: radiologyMuted,
                        fontSize: 12,
                      ),
                    ),
                  if (_hasValue(
                    consultation.requestedAt,
                  )) ...[
                    const SizedBox(height: 3),
                    Text(
                      _formatDateTime(
                        consultation.requestedAt,
                      ),
                      style: const TextStyle(
                        color: radiologyMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                  if (_hasValue(
                    consultation.reason,
                  )) ...[
                    const SizedBox(height: 6),
                    Text(
                      consultation.reason!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: radiologyNavy,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            _StatusChip(
              label: _consultationStatusLabel(
                consultation.status,
              ),
              color: _consultationStatusColor(
                consultation.status,
              ),
            ),
            const SizedBox(width: 4),
            const Icon(
              Icons.chevron_right,
              color: radiologyMuted,
              size: 22,
            ),
            ],
          ),
        ),
      );
}

class _EmptySection extends StatelessWidget {
  const _EmptySection({
    required this.message,
  });

  final String message;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(
          vertical: 18,
        ),
        child: Center(
          child: Text(
            message,
            style: const TextStyle(
              color: radiologyMuted,
              fontSize: 13,
            ),
          ),
        ),
      );
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: 10,
          vertical: 5,
        ),
        decoration: BoxDecoration(
          color: color.withValues(
            alpha: 0.10,
          ),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(
          vertical: 7,
        ),
        child: Row(
          children: [
            SizedBox(
              width: 88,
              child: Text(
                label,
                style: const TextStyle(
                  color: radiologyMuted,
                  fontSize: 13,
                ),
              ),
            ),
            Expanded(
              child: Text(
                !_hasValue(value) ? '정보 없음' : value!,
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

Map<String, dynamic>? _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }

  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }

  return null;
}

int? _toInt(dynamic value) {
  if (value is int) {
    return value;
  }

  if (value is num) {
    return value.toInt();
  }

  return int.tryParse(
    value?.toString() ?? '',
  );
}

double? _toDouble(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse(
    value?.toString() ?? '',
  );
}

bool _hasValue(String? value) => value != null && value.trim().isNotEmpty;

int? _calculateAgeFromBirthDate(String? value) {
  if (!_hasValue(value)) {
    return null;
  }

  final birthDate = DateTime.tryParse(value!);

  if (birthDate == null) {
    return null;
  }

  final today = DateTime.now();

  var age = today.year - birthDate.year;

  final hasHadBirthdayThisYear = today.month > birthDate.month ||
      (today.month == birthDate.month && today.day >= birthDate.day);

  if (!hasHadBirthdayThisYear) {
    age--;
  }

  return age;
}

String _formatDateTime(String? value) {
  if (!_hasValue(value)) {
    return '';
  }

  final parsed = DateTime.tryParse(value!);

  if (parsed == null) {
    return value;
  }

  final local = parsed.toLocal();

  String two(int number) => number.toString().padLeft(2, '0');

  return '${local.year}.${two(local.month)}.${two(local.day)} '
      '${two(local.hour)}:${two(local.minute)}';
}

String _studyTitle(_ImagingStudyItem study) {
  final type = study.scanType ??
      (study.modalities.isNotEmpty ? study.modalities.first : null);

  if (_hasValue(type)) {
    return 'Brain $type';
  }

  if (_hasValue(study.accessionNumber)) {
    return study.accessionNumber!;
  }

  return '영상 검사';
}

String _reportStatusLabel(
  String? reportStatus,
  String studyStatus,
) {
  switch (reportStatus) {
    case 'FINAL':
    case 'AMENDED':
      return '판독 완료';

    case 'DRAFT':
      return '판독 중';
  }

  if (studyStatus == 'AVAILABLE') {
    return '검사 완료';
  }

  return studyStatus.isEmpty ? '상태 미확인' : studyStatus;
}

Color _reportStatusColor(String? status) {
  switch (status) {
    case 'FINAL':
    case 'AMENDED':
      return const Color(0xFF16A36A);

    case 'DRAFT':
      return const Color(0xFFE28A15);

    default:
      return radiologyBlue;
  }
}

String _analysisTypeLabel(String type) {
  switch (type) {
    case 'HEMORRHAGIC_STROKE_CT':
      return 'CT 뇌출혈 분석';

    case 'ISCHEMIC_STROKE_DWI_ADC':
      return 'MRI 허혈성 뇌졸중 분석';

    case 'CEREBRAL_ANEURYSM_MRA':
      return 'MRA 뇌동맥류 분석';

    default:
      return type.isEmpty ? 'AI 분석' : type;
  }
}

String _analysisStatusLabel(String status) {
  switch (status) {
    case 'QUEUED':
      return '분석 대기';

    case 'PROCESSING':
      return '분석 중';

    case 'COMPLETED':
      return '분석 완료';

    case 'FAILED':
      return '분석 실패';

    case 'CANCELLED':
      return '분석 취소';

    case 'RETRYING':
      return '재시도 중';

    default:
      return status.isEmpty ? '상태 미확인' : status;
  }
}

String _analysisFinding(
  String analysisType,
  bool? isPositive,
) {
  if (isPositive == null) {
    return 'AI 판정 결과가 아직 산출되지 않았습니다.';
  }

  final target = switch (analysisType) {
    'HEMORRHAGIC_STROKE_CT' => '출혈 의심 영역',
    'ISCHEMIC_STROKE_DWI_ADC' => '허혈성 병변 의심 영역',
    'CEREBRAL_ANEURYSM_MRA' => '뇌동맥류 의심 영역',
    _ => '병변 의심 영역',
  };

  return '$target ${isPositive ? '검출' : '미검출'}';
}

String _consultationTypeLabel(String type) {
  switch (type) {
    case 'RADIOLOGY':
      return '영상의학과 협진';

    case 'NEUROSURGERY':
      return '신경외과 협진';

    default:
      return type.isEmpty ? '협진' : type;
  }
}

String _consultationStatusLabel(String status) {
  switch (status) {
    case 'REQUESTED':
      return '요청됨';

    case 'ACCEPTED':
      return '수락됨';

    case 'IN_PROGRESS':
      return '진행 중';

    case 'RESPONDED':
      return '회신 완료';

    case 'CLOSED':
      return '종결';

    case 'REJECTED':
      return '거절';

    case 'CANCELLED':
      return '취소';

    default:
      return status.isEmpty ? '상태 미확인' : status;
  }
}

Color _consultationStatusColor(String status) {
  switch (status) {
    case 'RESPONDED':
    case 'CLOSED':
      return const Color(0xFF16A36A);

    case 'REQUESTED':
    case 'ACCEPTED':
    case 'IN_PROGRESS':
      return const Color(0xFFE28A15);

    case 'REJECTED':
    case 'CANCELLED':
      return const Color(0xFFD74B4B);

    default:
      return radiologyBlue;
  }
}

String _pregnancyLabel(String? value) {
  switch (value) {
    case 'PREGNANT':
      return '임신';

    case 'NOT_PREGNANT':
      return '비임신';

    case 'UNKNOWN':
      return '확인되지 않음';

    default:
      return value ?? '';
  }
}
