import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class _PatientDetail {
  const _PatientDetail({
    required this.name,
    required this.patientNo,
    required this.birthDate,
    required this.estimatedAge,
    required this.sex,
    required this.phone,
    required this.status,
    required this.latestAssessment,
  });

  factory _PatientDetail.fromJson(Map<String, dynamic> json) {
    final assessment = json['latest_assessment'];
    return _PatientDetail(
      name: json['name']?.toString() ?? '',
      patientNo: json['patient_no']?.toString() ?? '',
      birthDate: json['birth_date']?.toString(),
      estimatedAge: json['estimated_age'] as int?,
      sex: json['sex']?.toString(),
      phone: json['phone']?.toString(),
      status: json['status']?.toString() ?? '',
      latestAssessment: assessment is Map
          ? _AssessmentSummary.fromJson(Map<String, dynamic>.from(assessment))
          : null,
    );
  }

  final String name;
  final String patientNo;
  final String? birthDate;
  final int? estimatedAge;
  final String? sex;
  final String? phone;
  final String status;
  final _AssessmentSummary? latestAssessment;
}

class _AssessmentSummary {
  const _AssessmentSummary({
    required this.encounterId,
    required this.status,
    required this.totalScore,
    required this.triagePriority,
    required this.onsetAt,
    required this.lkwAt,
    required this.symptomNote,
    required this.items,
  });

  factory _AssessmentSummary.fromJson(Map<String, dynamic> json) =>
      _AssessmentSummary(
        encounterId: json['encounter_id']?.toString() ?? '',
        status: json['status']?.toString() ?? '',
        totalScore: (json['total_score'] as num?)?.toInt(),
        triagePriority: json['triage_priority']?.toString(),
        onsetAt: json['onset_at']?.toString(),
        lkwAt: json['lkw_at']?.toString(),
        symptomNote: json['symptom_note']?.toString(),
        items: (json['items'] as List? ?? const [])
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false),
      );

  final String encounterId;
  final String status;
  final int? totalScore;
  final String? triagePriority;
  final String? onsetAt;
  final String? lkwAt;
  final String? symptomNote;
  final List<Map<String, dynamic>> items;
}

class RadiologyPatientDetailPage extends StatefulWidget {
  const RadiologyPatientDetailPage({
    super.key,
    required this.apiClient,
    required this.patientId,
    required this.roleCode,
  });

  final ClinicianApiClient apiClient;
  final String patientId;
  final String roleCode;

  @override
  State<RadiologyPatientDetailPage> createState() =>
      _RadiologyPatientDetailPageState();
}

class _RadiologyPatientDetailPageState
    extends State<RadiologyPatientDetailPage> {
  _PatientDetail? _patient;
  List<Map<String, dynamic>> _currentMedications = const [];
  List<Map<String, dynamic>> _clinicalNotes = const [];
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
      final response = await widget.apiClient.get(
        '/api/v1/patients/${widget.patientId}',
      );
      final patient = _PatientDetail.fromJson(response);
      final medicationsResponse = await widget.apiClient.get(
        '/api/v1/patients/${widget.patientId}/current-medications',
      );
      var notes = const <Map<String, dynamic>>[];
      final encounterId = patient.latestAssessment?.encounterId;
      if (widget.roleCode == 'NEUROLOGIST' &&
          encounterId != null &&
          encounterId.isNotEmpty) {
        final notesResponse = await widget.apiClient.get(
          '/api/v1/clinical-notes',
          query: {'encounter_id': encounterId},
        );
        notes = (notesResponse['results'] as List? ?? const [])
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false);
      }
      if (mounted) {
        setState(() {
          _patient = patient;
          _currentMedications =
              (medicationsResponse['results'] as List? ?? const [])
                  .whereType<Map>()
                  .map((item) => Map<String, dynamic>.from(item))
                  .toList(growable: false);
          _clinicalNotes = notes;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '환자 정보를 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('환자 상세')),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(_errorMessage!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          TextButton(
                              onPressed: _load, child: const Text('다시 시도')),
                        ],
                      ),
                    ),
                  )
                : _PatientDetailBody(
                    patient: _patient!,
                    currentMedications: _currentMedications,
                    clinicalNotes: _clinicalNotes,
                    showClinicalNotes: widget.roleCode == 'NEUROLOGIST',
                  ),
      );
}

class _PatientDetailBody extends StatelessWidget {
  const _PatientDetailBody({
    required this.patient,
    required this.currentMedications,
    required this.clinicalNotes,
    required this.showClinicalNotes,
  });

  final _PatientDetail patient;
  final List<Map<String, dynamic>> currentMedications;
  final List<Map<String, dynamic>> clinicalNotes;
  final bool showClinicalNotes;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
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
          ),
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
          const SizedBox(height: 18),
          const RadiologySectionTitle(title: '최신 초기평가'),
          const SizedBox(height: 10),
          if (patient.latestAssessment == null)
            const RadiologyEmptyState(
              icon: Icons.fact_check_outlined,
              message: '초기평가 기록이 없습니다.',
            )
          else
            _AssessmentCard(assessment: patient.latestAssessment!),
          const SizedBox(height: 18),
          const RadiologySectionTitle(title: '현재 복용약'),
          const SizedBox(height: 10),
          if (currentMedications.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.medication_outlined,
              message: '현재 복용 중인 약물이 없습니다.',
            )
          else
            ...currentMedications.map(
              (medication) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: RadiologyInfoCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        medication['medication_name']?.toString() ?? '약품명 없음',
                        style: const TextStyle(
                          color: radiologyNavy,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${medication['dose'] ?? '-'} ${medication['dose_unit'] ?? ''} '
                        '· 1일 ${medication['frequency_per_day'] ?? '-'}회 '
                        '· ${medication['duration_days'] ?? '-'}일',
                        style: const TextStyle(
                            color: radiologyMuted, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          if (showClinicalNotes) ...[
            const SizedBox(height: 18),
            const RadiologySectionTitle(title: '진료기록'),
            const SizedBox(height: 10),
            if (clinicalNotes.isEmpty)
              const RadiologyEmptyState(
                icon: Icons.description_outlined,
                message: '현재 Encounter의 진료기록이 없습니다.',
              )
            else
              ...clinicalNotes.map(
                (note) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: RadiologyInfoCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Expanded(
                            child: Text(
                              note['assessment_summary']?.toString() ??
                                  '임상 평가 요약 없음',
                              style: const TextStyle(
                                color: radiologyNavy,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          RadiologyStatusChip(
                            label: note['status']?.toString() ?? '-',
                            color: radiologyBlue,
                          ),
                        ]),
                        const SizedBox(height: 6),
                        Text(
                          note['clinical_opinion_summary']?.toString() ??
                              '임상소견 요약 없음',
                          style: const TextStyle(color: radiologyMuted),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ],
      );
}

class _AssessmentCard extends StatelessWidget {
  const _AssessmentCard({required this.assessment});

  final _AssessmentSummary assessment;

  @override
  Widget build(BuildContext context) {
    final itemValues = <String>[];
    for (final item in assessment.items) {
      final code = item['item_code']?.toString();
      final value = item['value_text'] ?? item['value_numeric'];
      if (code != null && value != null) itemValues.add('$code $value');
    }
    return RadiologyInfoCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              RadiologyStatusChip(
                label: assessment.status,
                color: const Color(0xFF2563B8),
              ),
              if (assessment.triagePriority != null)
                RadiologyStatusChip(
                  label: assessment.triagePriority!,
                  color: assessment.triagePriority == 'EMERGENCY'
                      ? const Color(0xFFB34B58)
                      : const Color(0xFFB46912),
                ),
            ],
          ),
          const SizedBox(height: 10),
          _InfoRow(label: 'Encounter', value: assessment.encounterId),
          _InfoRow(
            label: '스크리닝',
            value: assessment.totalScore?.toString(),
          ),
          _InfoRow(label: '증상 발생', value: assessment.onsetAt),
          _InfoRow(label: 'LKW', value: assessment.lkwAt),
          _InfoRow(label: '증상 메모', value: assessment.symptomNote),
          if (itemValues.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              itemValues.join(' · '),
              style: const TextStyle(color: radiologyMuted, fontSize: 12),
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
