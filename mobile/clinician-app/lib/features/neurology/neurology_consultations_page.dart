import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyConsultation {
  const NeurologyConsultation({
    required this.id,
    required this.patientName,
    required this.patientNo,
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
    final status = consultation['status']?.toString() ?? '';

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
              _DetailRow(label: '환자', value: patientName),
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
          child: Text(
            consultation['reason']?.toString().trim().isNotEmpty == true
                ? consultation['reason'].toString()
                : '정보 없음',
            style: const TextStyle(color: radiologyNavy, height: 1.45),
          ),
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
        if (allowedActions.contains('CANCEL') ||
            allowedActions.contains('VIEW_RESPONSE')) ...[
          const SizedBox(height: 10),
          Text(
            '현재 가능한 처리: ${allowedActions.join(', ')}',
            style: const TextStyle(color: radiologyMuted, fontSize: 12),
          ),
        ],
      ],
    );
  }
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

String _formatDateTime(String? value) {
  final parsed = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (parsed == null) {
    return '시간 정보 없음';
  }
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${parsed.year}.${twoDigits(parsed.month)}.${twoDigits(parsed.day)} '
      '${twoDigits(parsed.hour)}:${twoDigits(parsed.minute)}';
}
