import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class _ConsultationDetail {
  const _ConsultationDetail({
    required this.patientName,
    required this.patientNo,
    required this.requesterName,
    required this.requesterDepartment,
    required this.assigneeName,
    required this.assigneeDepartment,
    required this.reason,
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
      requesterName: requester?['name']?.toString() ?? '',
      requesterDepartment: requester?['department']?.toString() ?? '',
      assigneeName: assignee?['name']?.toString() ?? '',
      assigneeDepartment: assignee?['department']?.toString() ?? '',
      reason: json['reason']?.toString(),
      priority: json['priority']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      requestedAt: json['requested_at']?.toString(),
      finalOpinion: json['final_opinion']?.toString(),
      treatmentPlan: json['treatment_plan']?.toString(),
      allowedActions: (json['allowed_actions'] as List? ?? const [])
          .map((value) => value.toString())
          .toList(growable: false),
    );
  }

  final String patientName;
  final String patientNo;
  final String requesterName;
  final String requesterDepartment;
  final String assigneeName;
  final String assigneeDepartment;
  final String? reason;
  final String priority;
  final String status;
  final String? requestedAt;
  final String? finalOpinion;
  final String? treatmentPlan;
  final List<String> allowedActions;
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

  Future<void> _executeAction(String action) async {
    Map<String, dynamic>? body;
    if (action == 'RESPOND') {
      final values = await _responseDialog();
      if (values == null) return;
      body = values;
    } else if (action == 'REJECT' || action == 'CANCEL') {
      final reason = await _reasonDialog(action);
      if (reason == null) return;
      body = {'reason': reason};
    }

    final endpoint = switch (action) {
      'VIEW_RESPONSE' => 'view-response',
      _ => action.toLowerCase(),
    };
    try {
      await widget.apiClient.post(
        '/api/v1/consultations/${widget.consultationId}/$endpoint',
        body: body,
      );
      await _load();
    } on ClinicianApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  Future<String?> _reasonDialog(String action) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(action == 'REJECT' ? '협진 거절' : '협진 취소'),
        content: TextField(
          controller: controller,
          maxLength: 500,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: '사유',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('닫기'),
          ),
          FilledButton(
            onPressed: () {
              final value = controller.text.trim();
              if (value.isNotEmpty) Navigator.pop(dialogContext, value);
            },
            child: const Text('확인'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<Map<String, dynamic>?> _responseDialog() async {
    final opinion = TextEditingController();
    final plan = TextEditingController();
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('협진 회신'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: opinion,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: '최종 의견',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: plan,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: '치료 계획 (선택)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('닫기'),
          ),
          FilledButton(
            onPressed: () {
              final value = opinion.text.trim();
              if (value.isNotEmpty) {
                Navigator.pop(dialogContext, {
                  'final_opinion': value,
                  if (plan.text.trim().isNotEmpty)
                    'treatment_plan': plan.text.trim(),
                });
              }
            },
            child: const Text('회신'),
          ),
        ],
      ),
    );
    opinion.dispose();
    plan.dispose();
    return result;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('협진 상세')),
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
                : _ConsultationDetailBody(
                    consultation: _consultation!,
                    onAction: _executeAction,
                  ),
      );
}

class _ConsultationDetailBody extends StatelessWidget {
  const _ConsultationDetailBody({
    required this.consultation,
    required this.onAction,
  });

  final _ConsultationDetail consultation;
  final ValueChanged<String> onAction;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
          RadiologyInfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  consultation.patientName.isEmpty
                      ? '환자 정보 없음'
                      : consultation.patientName,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (consultation.patientNo.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    consultation.patientNo,
                    style: const TextStyle(color: radiologyMuted),
                  ),
                ],
                const SizedBox(height: 12),
                RadiologyStatusChip(
                  label: _statusLabel(consultation.status),
                  color: _statusColor(consultation.status),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '협진 정보'),
          const SizedBox(height: 10),
          RadiologyInfoCard(
            child: Column(
              children: [
                _DetailRow(label: '요청자', value: consultation.requesterName),
                _DetailRow(
                  label: '요청 진료과',
                  value: consultation.requesterDepartment,
                ),
                _DetailRow(label: '배정 의료진', value: consultation.assigneeName),
                _DetailRow(
                  label: '배정 진료과',
                  value: consultation.assigneeDepartment,
                ),
                _DetailRow(label: '우선순위', value: consultation.priority),
                _DetailRow(
                  label: '요청 시각',
                  value: _formatDateTime(consultation.requestedAt),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '협진 사유'),
          const SizedBox(height: 10),
          RadiologyInfoCard(
            child: Text(
              _textOrFallback(consultation.reason),
              style: const TextStyle(color: radiologyNavy, height: 1.5),
            ),
          ),
          if (_hasText(consultation.finalOpinion)) ...[
            const SizedBox(height: 14),
            const RadiologySectionTitle(title: '협진 의견'),
            const SizedBox(height: 10),
            RadiologyInfoCard(
              child: Text(
                consultation.finalOpinion!,
                style: const TextStyle(color: radiologyNavy, height: 1.5),
              ),
            ),
          ],
          if (_hasText(consultation.treatmentPlan)) ...[
            const SizedBox(height: 14),
            const RadiologySectionTitle(title: '치료 계획'),
            const SizedBox(height: 10),
            RadiologyInfoCard(
              child: Text(
                consultation.treatmentPlan!,
                style: const TextStyle(color: radiologyNavy, height: 1.5),
              ),
            ),
          ],
          if (consultation.allowedActions.isNotEmpty) ...[
            const SizedBox(height: 14),
            const RadiologySectionTitle(title: '가능한 작업'),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: consultation.allowedActions
                  .map(
                    (action) => FilledButton.tonal(
                      onPressed: () => onAction(action),
                      child: Text(_actionLabel(action)),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      );
}

String _actionLabel(String action) => switch (action) {
      'ACCEPT' => '수락',
      'REJECT' => '거절',
      'START' => '검토 시작',
      'RESPOND' => '회신',
      'CANCEL' => '취소',
      'VIEW_RESPONSE' => '회신 확인',
      _ => action,
    };

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            SizedBox(
              width: 92,
              child: Text(
                label,
                style: const TextStyle(color: radiologyMuted, fontSize: 13),
              ),
            ),
            Expanded(
              child: Text(
                _textOrFallback(value),
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

bool _hasText(String? value) => value != null && value.trim().isNotEmpty;

String _textOrFallback(String? value) =>
    _hasText(value) ? value!.trim() : '정보 없음';

String _statusLabel(String status) => switch (status) {
      'REQUESTED' => '요청',
      'ACCEPTED' => '수락',
      'IN_PROGRESS' => '진행중',
      'RESPONDED' || 'CLOSED' => '완료',
      'REJECTED' => '거절',
      'CANCELLED' => '취소',
      _ => status.isEmpty ? '정보 없음' : status,
    };

Color _statusColor(String status) => switch (status) {
      'REQUESTED' => const Color(0xFF2563B8),
      'ACCEPTED' || 'IN_PROGRESS' => const Color(0xFFB46912),
      'REJECTED' || 'CANCELLED' => const Color(0xFFCC4D5B),
      _ => const Color(0xFF208563),
    };

String _formatDateTime(String? value) {
  if (!_hasText(value)) {
    return '정보 없음';
  }
  final dateTime = DateTime.tryParse(value!)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.'
      '${dateTime.day.toString().padLeft(2, '0')} '
      '${dateTime.hour.toString().padLeft(2, '0')}:'
      '${dateTime.minute.toString().padLeft(2, '0')}';
}
