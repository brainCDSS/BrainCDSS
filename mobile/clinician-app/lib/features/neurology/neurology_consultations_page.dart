import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyConsultation {
  const NeurologyConsultation({
    required this.id,
    required this.patientName,
    required this.patientNo,
    required this.patientSex,
    required this.type,
    required this.assigneeName,
    required this.assigneeDepartment,
    required this.priority,
    required this.status,
    required this.requestedAt,
  });

  factory NeurologyConsultation.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    final assignee = json['assigned_to'] as Map?;
    return NeurologyConsultation(
      id: json['consultation_id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      patientSex: patient?['sex']?.toString(),
      type: json['type']?.toString() ??
          json['consultation_type']?.toString() ??
          '',
      assigneeName: assignee?['name']?.toString() ?? '',
      assigneeDepartment: assignee?['department']?.toString() ?? '',
      priority: json['priority']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      requestedAt: json['requested_at']?.toString(),
    );
  }

  final String id;
  final String patientName;
  final String patientNo;
  final String? patientSex;
  final String type;
  final String assigneeName;
  final String assigneeDepartment;
  final String priority;
  final String status;
  final String? requestedAt;
}

class NeurologyConsultationsPage extends StatefulWidget {
  const NeurologyConsultationsPage({
    super.key,
    required this.apiClient,
    required this.onOpenDetail,
  });

  final ClinicianApiClient apiClient;
  final ValueChanged<String> onOpenDetail;

  @override
  State<NeurologyConsultationsPage> createState() =>
      _NeurologyConsultationsPageState();
}

class _NeurologyConsultationsPageState
    extends State<NeurologyConsultationsPage> {
  static const _filters = <String?>[
    null,
    'REQUESTED',
    'IN_PROGRESS',
    'COMPLETED',
  ];
  static const _filterLabels = ['전체', '요청', '진행중', '완료'];

  List<NeurologyConsultation> _consultations = const [];
  var _filterIndex = 0;
  var _isLoading = true;
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
      final filter = _filters[_filterIndex];
      final response = await widget.apiClient.get(
        '/api/v1/consultations',
        query: {
          'viewer_relation': 'REQUESTED_BY',
          if (filter != null && filter != 'COMPLETED') 'status': filter,
        },
      );
      var items = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (item) => NeurologyConsultation.fromJson(
              Map<String, dynamic>.from(item),
            ),
          )
          .toList(growable: false);
      if (filter == 'COMPLETED') {
        items = items
            .where(
              (item) => item.status == 'RESPONDED' || item.status == 'CLOSED',
            )
            .toList(growable: false);
      }
      if (mounted) {
        setState(() => _consultations = items);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '협진 목록을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _selectFilter(int index) {
    if (_filterIndex == index) {
      return;
    }
    setState(() => _filterIndex = index);
    _load();
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '협진'),
          const SizedBox(height: 8),
          const Text(
            '요청한 협진의 진행 상태를 확인합니다.',
            style: TextStyle(color: radiologyMuted, fontSize: 13),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            children: List.generate(
              _filterLabels.length,
              (index) => ChoiceChip(
                label: Text(_filterLabels[index]),
                selected: _filterIndex == index,
                onSelected: (_) => _selectFilter(index),
              ),
            ),
          ),
          const SizedBox(height: 14),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(28),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_errorMessage != null)
            _RetryCard(message: _errorMessage!, onRetry: _load)
          else if (_consultations.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.forum_outlined,
              message: '확인할 협진 요청이 없습니다.',
            )
          else
            ..._consultations.map(
              (consultation) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InkWell(
                  borderRadius: BorderRadius.circular(18),
                  onTap: consultation.id.isEmpty
                      ? null
                      : () => widget.onOpenDetail(consultation.id),
                  child: RadiologyInfoCard(
                    padding: const EdgeInsets.all(15),
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
                            Icons.forum_outlined,
                            color: radiologyBlue,
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
                                    child: Row(
                                      children: [
                                        Flexible(
                                          child: Text(
                                            consultation.patientName.isEmpty
                                                ? '환자 정보 없음'
                                                : consultation.patientName,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              color: radiologyNavy,
                                              fontSize: 16,
                                              fontWeight: FontWeight.w800,
                                            ),
                                          ),
                                        ),
                                        if (consultation.patientSex == 'M' ||
                                            consultation.patientSex == 'F') ...[
                                          const SizedBox(width: 8),
                                          _SexBadge(sex: consultation.patientSex!),
                                        ],
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  _StatusChip(status: consultation.status),
                                ],
                              ),
                              if (consultation.patientNo.isNotEmpty) ...[
                                const SizedBox(height: 3),
                                Text(
                                  consultation.patientNo,
                                  style: const TextStyle(
                                    color: radiologyMuted,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                              const SizedBox(height: 7),
                              Text(
                                _assigneeLabel(consultation),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: radiologyNavy,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${_priorityLabel(consultation.priority)} · '
                                '${_formatDateTime(consultation.requestedAt)}',
                                style: const TextStyle(
                                  color: radiologyMuted,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 4),
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

class NeurologyConsultationDetailPage extends StatefulWidget {
  const NeurologyConsultationDetailPage({
    super.key,
    required this.apiClient,
    required this.consultationId,
    required this.onOpenMessages,
  });

  final ClinicianApiClient apiClient;
  final String consultationId;
  final void Function({
    required String consultationId,
    required String patientName,
    required String patientNo,
    required String consultationStatus,
  }) onOpenMessages;

  @override
  State<NeurologyConsultationDetailPage> createState() =>
      _NeurologyConsultationDetailPageState();
}

class _NeurologyConsultationDetailPageState
    extends State<NeurologyConsultationDetailPage> {
  Map<String, dynamic>? _consultation;
  var _isLoading = true;
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
        '/api/v1/consultations/${widget.consultationId}',
      );
      if (mounted) {
        setState(() => _consultation = response);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '협진 정보를 불러오지 못했습니다.');
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
      return _RetryCard(message: _errorMessage!, onRetry: _load);
    }

    final consultation = _consultation!;
    final patient = consultation['patient_summary'] as Map?;
    final assignee = consultation['assigned_to'] as Map?;
    final allowedActions =
        (consultation['allowed_actions'] as List? ?? const [])
            .map((value) => value.toString())
            .toSet();
    final patientName = patient?['name']?.toString() ?? '';
    final patientNo = patient?['patient_no']?.toString() ?? '';
    final patientSex = patient?['sex']?.toString();
    final status = consultation['status']?.toString() ?? '';
    final reason = _ConsultationReasonDisplay.fromReason(
      consultation['reason']?.toString(),
    );

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                '협진 상세',
                style: TextStyle(
                  color: radiologyNavy,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            ConsultationMessagesAction(
              onTap: widget.consultationId.isEmpty
                  ? null
                  : () => widget.onOpenMessages(
                        consultationId: widget.consultationId,
                        patientName: patientName,
                        patientNo: patientNo,
                        consultationStatus: status,
                      ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        RadiologyInfoCard(
          child: Column(
            children: [
              _PatientDetailRow(name: patientName, sex: patientSex),
              _DetailRow(label: '환자번호', value: patientNo),
              _DetailRow(
                label: '협진 대상',
                value: _consultationTypeLabel(
                  consultation['type']?.toString() ??
                      consultation['consultation_type']?.toString() ??
                      '',
                ),
              ),
              _DetailRow(
                label: '배정 의료진',
                value: [
                  assignee?['department']?.toString() ?? '',
                  assignee?['name']?.toString() ?? '',
                ].where((value) => value.isNotEmpty).join(' '),
              ),
              _DetailRow(
                label: '우선순위',
                value:
                    _priorityLabel(consultation['priority']?.toString() ?? ''),
              ),
              _DetailRow(label: '상태', value: _statusLabel(status)),
              _DetailRow(
                label: '요청 시각',
                value:
                    _formatDateTime(consultation['requested_at']?.toString()),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        const RadiologySectionTitle(title: '협진 사유'),
        const SizedBox(height: 8),
        RadiologyInfoCard(
          child: _ConsultationReasonCard(reason: reason),
        ),
        if ((consultation['final_opinion']?.toString().trim().isNotEmpty ??
                false) ||
            (consultation['treatment_plan']?.toString().trim().isNotEmpty ??
                false)) ...[
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '협진 회신'),
          const SizedBox(height: 8),
          RadiologyInfoCard(
            child: Column(
              children: [
                _DetailRow(
                  label: '의견',
                  value: consultation['final_opinion']?.toString() ?? '',
                ),
                _DetailRow(
                  label: '치료 계획',
                  value: consultation['treatment_plan']?.toString() ?? '',
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _ConsultationReasonCard extends StatelessWidget {
  const _ConsultationReasonCard({required this.reason});

  final _ConsultationReasonDisplay reason;

  @override
  Widget build(BuildContext context) {
    if (reason.isEmpty) {
      return const Text('정보 없음', style: TextStyle(color: radiologyNavy));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (reason.requestReason != null) ...[
          const Text(
            '협진 요청 사유',
            style: TextStyle(
              color: radiologyMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            reason.requestReason!,
            style: const TextStyle(color: radiologyNavy, height: 1.45),
          ),
        ],
        if (reason.analysisType != null) ...[
          if (reason.requestReason != null) const SizedBox(height: 14),
          const Text(
            '분석 유형',
            style: TextStyle(color: radiologyMuted, fontSize: 11),
          ),
          const SizedBox(height: 3),
          Text(
            _analysisTypeLabel(reason.analysisType!),
            style: const TextStyle(
              color: radiologyNavy,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
        if (reason.aiJudgment != null) ...[
          if (reason.requestReason != null || reason.analysisType != null)
            const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFEAF2FF),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'AI 판정',
                  style: TextStyle(
                    color: radiologyBlue,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  reason.aiJudgment!,
                  softWrap: true,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ],
        if (reason.lesionCount != null || reason.totalVolume != null) ...[
          if (reason.requestReason != null ||
              reason.analysisType != null ||
              reason.aiJudgment != null)
            const SizedBox(height: 14),
          Row(
            children: [
              if (reason.lesionCount != null)
                Expanded(
                  child: _ReasonMetricCard(
                    label: '병변 개수',
                    value: reason.lesionCount!,
                  ),
                ),
              if (reason.lesionCount != null && reason.totalVolume != null)
                const SizedBox(width: 10),
              if (reason.totalVolume != null)
                Expanded(
                  child: _ReasonMetricCard(
                    label: '병변 총 부피',
                    value: reason.totalVolume!,
                  ),
                ),
            ],
          ),
        ],
      ],
    );
  }
}

class _ReasonMetricCard extends StatelessWidget {
  const _ReasonMetricCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFFF5F8FF),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: const TextStyle(color: radiologyMuted, fontSize: 11),
            ),
            const SizedBox(height: 3),
            Text(
              value,
              softWrap: true,
              style: const TextStyle(
                color: radiologyNavy,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      );
}

class _ConsultationReasonDisplay {
  const _ConsultationReasonDisplay({
    required this.requestReason,
    required this.analysisType,
    required this.aiJudgment,
    required this.lesionCount,
    required this.totalVolume,
  });

  factory _ConsultationReasonDisplay.fromReason(String? reason) {
    final lines = _withoutAnalysisId(reason)
        .split(RegExp(r'\r?\n'))
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
    const requestReasonLabels = ['협진 요청 사유', '협진 사유', 'reason'];
    const analysisTypeLabels = ['분석 유형', 'analysis type', 'analysis_type'];
    const judgmentLabels = ['AI 판정', 'ai judgment', 'is_positive'];
    const lesionCountLabels = ['병변 개수', 'lesion count', 'lesion_count'];
    const totalVolumeLabels = [
      '병변 총 부피',
      '총 병변 부피',
      'total volume',
      'total_volume_ml',
    ];

    final explicitRequestReason = _reasonValue(lines, requestReasonLabels);
    final analysisType = _reasonValue(lines, analysisTypeLabels);
    final aiJudgment = _reasonValue(lines, judgmentLabels);
    final lesionCount = _reasonValue(lines, lesionCountLabels);
    final totalVolume = _reasonValue(lines, totalVolumeLabels);
    final requestLines = lines.where((line) {
      return !_isReasonValueLine(line, requestReasonLabels) &&
          !_isReasonValueLine(line, analysisTypeLabels) &&
          !_isReasonValueLine(line, judgmentLabels) &&
          !_isReasonValueLine(line, lesionCountLabels) &&
          !_isReasonValueLine(line, totalVolumeLabels);
    }).toList(growable: false);

    return _ConsultationReasonDisplay(
      requestReason: explicitRequestReason ??
          (requestLines.isEmpty ? null : requestLines.join('\n')),
      analysisType: analysisType,
      aiJudgment: aiJudgment,
      lesionCount: lesionCount,
      totalVolume: totalVolume,
    );
  }

  final String? requestReason;
  final String? analysisType;
  final String? aiJudgment;
  final String? lesionCount;
  final String? totalVolume;

  bool get isEmpty =>
      requestReason == null &&
      analysisType == null &&
      aiJudgment == null &&
      lesionCount == null &&
      totalVolume == null;
}

bool _isReasonValueLine(String line, List<String> labels) =>
    _reasonValue([line], labels) != null;

String? _reasonValue(List<String> lines, List<String> labels) {
  for (final line in lines) {
    for (final label in labels) {
      final match = RegExp(
        '^${RegExp.escape(label)}\\s*[:=：]\\s*(.+)\$',
        caseSensitive: false,
      ).firstMatch(line);
      final value = match?.group(1)?.trim();
      if (value != null && value.isNotEmpty) return value;
    }
  }
  return null;
}

String _analysisTypeLabel(String value) => switch (value) {
      'CEREBRAL_ANEURYSM_MRA' => 'MRA 뇌동맥류 분석',
      _ => value,
    };

class _PatientDetailRow extends StatelessWidget {
  const _PatientDetailRow({required this.name, required this.sex});

  final String name;
  final String? sex;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(
            width: 86,
            child: Text('환자',
                style: TextStyle(color: radiologyMuted, fontSize: 13)),
          ),
          Expanded(
              child: Row(children: [
            Flexible(
                child: Text(name.isEmpty ? '정보 없음' : name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: radiologyNavy, fontWeight: FontWeight.w700))),
            if (sex == 'M' || sex == 'F') ...[
              const SizedBox(width: 8),
              _SexBadge(sex: sex!),
            ],
          ])),
        ]),
      );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 86,
              child: Text(
                label,
                style: const TextStyle(color: radiologyMuted, fontSize: 13),
              ),
            ),
            Expanded(
              child: Text(
                value.isEmpty ? '정보 없음' : value,
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

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFFEAF2FF),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          _statusLabel(status),
          style: const TextStyle(
            color: radiologyBlue,
            fontSize: 11,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _SexBadge extends StatelessWidget {
  const _SexBadge({required this.sex});

  final String sex;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: const Color(0xFFEAF2FF),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          sex,
          style: const TextStyle(
            color: radiologyMuted,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
}

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 10),
              TextButton(onPressed: onRetry, child: const Text('다시 시도')),
            ],
          ),
        ),
      );
}

String _assigneeLabel(NeurologyConsultation consultation) {
  final values = [
    if (consultation.type.isNotEmpty) _consultationTypeLabel(consultation.type),
    if (consultation.assigneeName.isNotEmpty)
      consultation.assigneeName
    else if (consultation.assigneeDepartment.isNotEmpty)
      _consultationTypeLabel(consultation.assigneeDepartment),
  ].where((value) => value.isNotEmpty).toList(growable: false);
  return values.isEmpty ? '배정 의료진 정보 없음' : values.join(' · ');
}

String _consultationTypeLabel(String value) => switch (value) {
      'RADIOLOGY' => '영상의학과',
      'NEUROSURGERY' => '신경외과',
      'NEUROSURGEON' => '신경외과',
      _ => value.isEmpty ? '협진 대상 정보 없음' : value,
    };

String _priorityLabel(String value) => switch (value) {
      'STAT' => '긴급',
      'URGENT' => '응급',
      'ROUTINE' => '일반',
      _ => value.isEmpty ? '우선순위 정보 없음' : value,
    };

String _statusLabel(String value) => switch (value) {
      'REQUESTED' => '요청',
      'ACCEPTED' => '수락',
      'IN_PROGRESS' => '진행중',
      'RESPONDED' => '회신 완료',
      'CLOSED' => '완료',
      'REJECTED' => '거절',
      'CANCELLED' => '취소',
      _ => value.isEmpty ? '정보 없음' : value,
    };

String _withoutAnalysisId(String? reason) {
  if (reason == null || reason.isEmpty) return '';

  return reason.replaceAll(
    RegExp(
      r'^\s*(?:(?:AI\s*)?분석\s*ID|analysis[_\s-]*id|검사\s*번호|study[_\s-]*(?:no|number)|accession[_\s-]*(?:no|number))\s*[:=：].*(?:\r?\n|$)',
      caseSensitive: false,
      multiLine: true,
    ),
    '',
  );
}

String _formatDateTime(String? value) {
  final parsed = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (parsed == null) {
    return '시간 정보 없음';
  }
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${parsed.year}.${twoDigits(parsed.month)}.${twoDigits(parsed.day)} '
      '${twoDigits(parsed.hour)}:${twoDigits(parsed.minute)}';
}
