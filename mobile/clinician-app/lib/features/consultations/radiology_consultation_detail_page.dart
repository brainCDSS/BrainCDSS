import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';
import '../radiology/widgets/radiology_ui.dart';

class _ConsultationDetail {
  const _ConsultationDetail({
    required this.patientName,
    required this.patientNo,
    required this.birthDate,
    required this.estimatedAge,
    required this.sex,
    required this.requesterName,
    required this.requesterDepartment,
    required this.assigneeName,
    required this.assigneeDepartment,
    required this.reason,
    required this.type,
    required this.priority,
    required this.status,
    required this.requestedAt,
    required this.finalOpinion,
    required this.treatmentPlan,
    required this.allowedActions,
  });

  factory _ConsultationDetail.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    final requester = json['requested_by'] as Map?;
    final assignee = json['assigned_to'] as Map?;
    return _ConsultationDetail(
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      birthDate: patient?['birth_date']?.toString(),
      estimatedAge: patient?['estimated_age']?.toString(),
      sex: patient?['sex']?.toString(),
      requesterName: requester?['name']?.toString() ?? '',
      requesterDepartment: requester?['department']?.toString() ?? '',
      assigneeName: assignee?['name']?.toString() ?? '',
      assigneeDepartment: assignee?['department']?.toString() ?? '',
      reason: json['reason']?.toString(),
      type: json['type']?.toString() ?? json['consultation_type']?.toString() ?? '',
      priority: json['priority']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      requestedAt: json['requested_at']?.toString(),
      finalOpinion: json['final_opinion']?.toString(),
      treatmentPlan: json['treatment_plan']?.toString(),
      allowedActions: (json['allowed_actions'] as List? ?? const [])
          .map((value) => value.toString())
          .toSet(),
    );
  }

  final String patientName;
  final String patientNo;
  final String? birthDate;
  final String? estimatedAge;
  final String? sex;
  final String requesterName;
  final String requesterDepartment;
  final String assigneeName;
  final String assigneeDepartment;
  final String? reason;
  final String type;
  final String priority;
  final String status;
  final String? requestedAt;
  final String? finalOpinion;
  final String? treatmentPlan;
  final Set<String> allowedActions;
}

class RadiologyConsultationDetailPage extends StatefulWidget {
  const RadiologyConsultationDetailPage({
    super.key,
    required this.apiClient,
    required this.consultationId,
  });

  final ClinicianApiClient apiClient;
  final String consultationId;

  @override
  State<RadiologyConsultationDetailPage> createState() =>
      _RadiologyConsultationDetailPageState();
}

class _RadiologyConsultationDetailPageState
    extends State<RadiologyConsultationDetailPage> {
  _ConsultationDetail? _consultation;
  bool _isLoading = true;
  bool _isSubmitting = false;
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
        setState(() => _consultation = _ConsultationDetail.fromJson(response));
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

  Future<void> _submitAction(
    String action, {
    Map<String, dynamic>? body,
  }) async {
    if (_isSubmitting) {
      return;
    }
    setState(() => _isSubmitting = true);
    try {
      await widget.apiClient.post(
        '/api/v1/consultations/${widget.consultationId}/$action',
        body: body,
      );
      await _load();
    } on ClinicianApiException catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('협진 상태를 변경하지 못했습니다.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('협진 상태를 변경하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _confirmAction({
    required String action,
    required String title,
    required String content,
  }) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: Text(content),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('확인'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await _submitAction(action);
    }
  }

  Future<void> _showReasonDialog({
    required String action,
    required String title,
    required String field,
    required String hintText,
  }) async {
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          maxLength: 2000,
          maxLines: 3,
          decoration: InputDecoration(hintText: hintText),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(
              dialogContext,
              controller.text.trim(),
            ),
            child: const Text('확인'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (reason == null || reason.isEmpty || !mounted) {
      return;
    }
    await _submitAction(action, body: {field: reason});
  }

  Future<void> _showRespondDialog() async {
    final opinionController = TextEditingController();
    final planController = TextEditingController();
    final values = await showDialog<Map<String, String>>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('협진 회신'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: opinionController,
                autofocus: true,
                maxLength: 2000,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: '협진 의견',
                  hintText: '협진 의견을 입력해 주세요.',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: planController,
                maxLength: 2000,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: '치료 계획 (선택)',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, {
              'final_opinion': opinionController.text.trim(),
              'treatment_plan': planController.text.trim(),
            }),
            child: const Text('회신 확정'),
          ),
        ],
      ),
    );
    opinionController.dispose();
    planController.dispose();
    if (values == null || values['final_opinion']!.isEmpty || !mounted) {
      return;
    }
    await _submitAction(
      'respond',
      body: {
        'final_opinion': values['final_opinion'],
        if (values['treatment_plan']!.isNotEmpty)
          'treatment_plan': values['treatment_plan'],
      },
    );
  }

  @override
  Widget build(BuildContext context) => _isLoading
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
                TextButton(onPressed: _load, child: const Text('다시 시도')),
              ],
            ),
          ),
        )
      : _ConsultationDetailBody(
          consultation: _consultation!,
          consultationId: widget.consultationId,
          isSubmitting: _isSubmitting,
          onAccept: () => _confirmAction(
            action: 'accept',
            title: '협진을 수락할까요?',
            content: '협진 검토를 시작할 수 있습니다.',
          ),
          onReject: () => _showReasonDialog(
            action: 'reject',
            title: '협진을 거절할까요?',
            field: 'reason',
            hintText: '거절 사유를 입력해 주세요.',
          ),
          onStart: () => _confirmAction(
            action: 'start',
            title: '협진 검토를 시작할까요?',
            content: '협진 상태가 진행 중으로 변경됩니다.',
          ),
          onRespond: _showRespondDialog,
          onCancel: () => _showReasonDialog(
            action: 'cancel',
            title: '협진을 취소할까요?',
            field: 'cancel_reason',
            hintText: '취소 사유를 입력해 주세요.',
          ),
          onViewResponse: () => _confirmAction(
            action: 'view-response',
            title: '회신을 확인할까요?',
            content: '회신 확인 후 협진이 종결됩니다.',
          ),
        );
}

class _ConsultationDetailBody extends StatelessWidget {
  const _ConsultationDetailBody({
    required this.consultation,
    required this.consultationId,
    required this.isSubmitting,
    required this.onAccept,
    required this.onReject,
    required this.onStart,
    required this.onRespond,
    required this.onCancel,
    required this.onViewResponse,
  });

  final _ConsultationDetail consultation;
  final String consultationId;
  final bool isSubmitting;
  final VoidCallback onAccept;
  final VoidCallback onReject;
  final VoidCallback onStart;
  final VoidCallback onRespond;
  final VoidCallback onCancel;
  final VoidCallback onViewResponse;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          const Text(
            '협진 상세',
            style: TextStyle(
              color: radiologyNavy,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            '요청된 협진의 상세 정보를 확인합니다.',
            style: TextStyle(color: radiologyMuted, fontSize: 13),
          ),
          const SizedBox(height: 18),
          _PatientSummaryCard(consultation: consultation),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '협진 정보'),
          const SizedBox(height: 8),
          RadiologyInfoCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Column(
              children: [
                _DetailRow(label: '요청자', value: consultation.requesterName),
                _DetailRow(label: '요청 진료과', value: consultation.requesterDepartment),
                _DetailRow(label: '배정 의료진', value: consultation.assigneeName),
                _DetailRow(label: '배정 진료과', value: consultation.assigneeDepartment),
                if (_hasText(consultation.type))
                  _DetailRow(label: '협진 유형', value: consultation.type),
                _DetailRow(label: '요청 시각', value: _formatDateTime(consultation.requestedAt)),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '협진 사유'),
          const SizedBox(height: 8),
          RadiologyInfoCard(
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
            child: Text(
              _textOrFallback(consultation.reason),
              style: const TextStyle(
                color: radiologyMuted,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          ),
          const SizedBox(height: 14),
          InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: consultationId.isEmpty
                ? null
                : () => RadiologyNavigation.openConsultationMessages(
                      consultationId: consultationId,
                      patientName: consultation.patientName,
                      patientNo: consultation.patientNo,
                      consultationStatus: consultation.status,
                    ),
            child: RadiologyInfoCard(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: const Row(
                children: [
                  _MessageEntryIcon(),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '협진 메시지',
                          style: TextStyle(
                            color: radiologyNavy,
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        SizedBox(height: 3),
                        Text(
                          '의료진과 협진 내용을 주고받을 수 있습니다.',
                          style: TextStyle(color: radiologyMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded, color: radiologyMuted),
                ],
              ),
            ),
          ),
          if (_hasText(consultation.finalOpinion)) ...[
            const SizedBox(height: 14),
            const RadiologySectionTitle(title: '협진 소견'),
            const SizedBox(height: 8),
            RadiologyInfoCard(
              padding: const EdgeInsets.all(16),
              child: Text(
                consultation.finalOpinion!,
                style: const TextStyle(color: radiologyNavy, height: 1.55),
              ),
            ),
          ],
          if (_hasText(consultation.treatmentPlan)) ...[
            const SizedBox(height: 14),
            const RadiologySectionTitle(title: '치료 계획'),
            const SizedBox(height: 8),
            RadiologyInfoCard(
              padding: const EdgeInsets.all(16),
              child: Text(
                consultation.treatmentPlan!,
                style: const TextStyle(color: radiologyNavy, height: 1.55),
              ),
            ),
          ],
          if (consultation.allowedActions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                if (consultation.allowedActions.contains('ACCEPT'))
                  FilledButton(
                    onPressed: isSubmitting ? null : onAccept,
                    child: const Text('수락'),
                  ),
                if (consultation.allowedActions.contains('REJECT'))
                  OutlinedButton(
                    onPressed: isSubmitting ? null : onReject,
                    child: const Text('거절'),
                  ),
                if (consultation.allowedActions.contains('START'))
                  FilledButton(
                    onPressed: isSubmitting ? null : onStart,
                    child: const Text('협진 시작'),
                  ),
                if (consultation.allowedActions.contains('RESPOND'))
                  FilledButton(
                    onPressed: isSubmitting ? null : onRespond,
                    child: const Text('의견 회신'),
                  ),
                if (consultation.allowedActions.contains('CANCEL'))
                  OutlinedButton(
                    onPressed: isSubmitting ? null : onCancel,
                    child: const Text('취소'),
                  ),
                if (consultation.allowedActions.contains('VIEW_RESPONSE'))
                  OutlinedButton(
                    onPressed: isSubmitting ? null : onViewResponse,
                    child: const Text('회신 확인'),
                  ),
              ],
            ),
          ],
        ],
      );
}

class _MessageEntryIcon extends StatelessWidget {
  const _MessageEntryIcon();

  @override
  Widget build(BuildContext context) => Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: const Color(0xFFEAF2FF),
          borderRadius: BorderRadius.circular(13),
        ),
        child: const Icon(
          Icons.forum_outlined,
          color: radiologyBlue,
          size: 21,
        ),
      );
}

class _PatientSummaryCard extends StatelessWidget {
  const _PatientSummaryCard({required this.consultation});

  final _ConsultationDetail consultation;

  @override
  Widget build(BuildContext context) {
    final demographics = <String>[
      if (_hasText(consultation.sex)) consultation.sex!,
      if (_hasText(consultation.estimatedAge)) '${consultation.estimatedAge}세',
      if (_hasText(consultation.birthDate)) consultation.birthDate!,
    ];

    return RadiologyInfoCard(
      padding: const EdgeInsets.all(16),
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
            child: const Icon(Icons.person_outline_rounded, color: radiologyBlue),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  consultation.patientName.isEmpty ? '환자 정보 없음' : consultation.patientName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: radiologyNavy, fontSize: 17, fontWeight: FontWeight.w800),
                ),
                if (consultation.patientNo.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(consultation.patientNo, style: const TextStyle(color: radiologyMuted, fontSize: 12)),
                ],
                if (demographics.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(demographics.join(' · '), style: const TextStyle(color: radiologyMuted, fontSize: 12)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (consultation.priority.isNotEmpty)
                _CompactBadge(label: _priorityLabel(consultation.priority), color: _priorityColor(consultation.priority)),
              if (consultation.priority.isNotEmpty) const SizedBox(height: 6),
              _CompactBadge(label: _statusLabel(consultation.status), color: _statusColor(consultation.status)),
            ],
          ),
        ],
      ),
    );
  }
}

class _CompactBadge extends StatelessWidget {
  const _CompactBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800)),
      );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 92,
              child: Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 13)),
            ),
            Expanded(
              child: Text(
                _textOrFallback(value),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
      );
}

bool _hasText(String? value) => value != null && value.trim().isNotEmpty;

String _textOrFallback(String? value) => _hasText(value) ? value!.trim() : '정보 없음';

String _statusLabel(String status) => switch (status) {
      'REQUESTED' => '요청',
      'ACCEPTED' => '수락',
      'IN_PROGRESS' => '협진 진행 중',
      'RESPONDED' || 'CLOSED' => '완료',
      'REJECTED' => '거절',
      'CANCELLED' => '취소',
      _ => status.isEmpty ? '상태 미확인' : status,
    };

Color _statusColor(String status) => switch (status) {
      'REQUESTED' => radiologyBlue,
      'ACCEPTED' || 'IN_PROGRESS' => radiologyWarning,
      'REJECTED' || 'CANCELLED' => radiologyDanger,
      _ => radiologySuccess,
    };

String _priorityLabel(String priority) => switch (priority) {
      'CRITICAL' => '긴급',
      'HIGH' => '높음',
      'NORMAL' => '일반',
      _ => priority,
    };

Color _priorityColor(String priority) => switch (priority) {
      'CRITICAL' => radiologyDanger,
      'HIGH' => radiologyWarning,
      _ => radiologyMuted,
    };

String _formatDateTime(String? value) {
  if (!_hasText(value)) {
    return '정보 없음';
  }
  final dateTime = DateTime.tryParse(value!)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  String two(int number) => number.toString().padLeft(2, '0');
  return '${dateTime.year}.${two(dateTime.month)}.${two(dateTime.day)} '
      '${two(dateTime.hour)}:${two(dateTime.minute)}';
}
