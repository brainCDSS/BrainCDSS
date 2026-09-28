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
      type: json['type']?.toString() ??
          json['consultation_type']?.toString() ??
          '',
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

class _RespondDraft {
  const _RespondDraft({
    required this.finalOpinion,
    required this.treatmentPlan,
  });

  final String finalOpinion;
  final String treatmentPlan;
}

class _RespondConsultationDialog extends StatefulWidget {
  const _RespondConsultationDialog();

  @override
  State<_RespondConsultationDialog> createState() =>
      _RespondConsultationDialogState();
}

class _RespondConsultationDialogState
    extends State<_RespondConsultationDialog> {
  late final TextEditingController _opinionController;
  late final TextEditingController _planController;

  @override
  void initState() {
    super.initState();
    _opinionController = TextEditingController();
    _planController = TextEditingController();
  }

  @override
  void dispose() {
    _opinionController.dispose();
    _planController.dispose();
    super.dispose();
  }

  void _submit() {
    Navigator.of(context).pop(
      _RespondDraft(
        finalOpinion: _opinionController.text.trim(),
        treatmentPlan: _planController.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Dialog(
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Expanded(
                      child: Text(
                        '협진 회신',
                        style: TextStyle(
                          color: radiologyNavy,
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: '닫기',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                const Text(
                  '협진 의견',
                  style: TextStyle(
                    color: radiologyNavy,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _opinionController,
                  autofocus: true,
                  maxLength: 2000,
                  minLines: 3,
                  maxLines: 4,
                  decoration: _replyInputDecoration(
                    hintText: '협진에 대한 의견을 입력해주세요.',
                  ),
                ),
                const SizedBox(height: 12),
                const Row(
                  children: [
                    Text(
                      '치료 계획',
                      style: TextStyle(
                        color: radiologyNavy,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    SizedBox(width: 5),
                    Text(
                      '(선택)',
                      style: TextStyle(
                        color: radiologyBlue,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _planController,
                  maxLength: 1000,
                  minLines: 2,
                  maxLines: 3,
                  decoration: _replyInputDecoration(
                    hintText: '치료 계획이 있다면 입력해주세요.',
                  ),
                ),
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEAF2FF),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.info_outline_rounded,
                          color: radiologyBlue, size: 18),
                      SizedBox(width: 7),
                      Expanded(
                        child: Text(
                          '입력하신 내용은 요청한 의료진에게 전달됩니다.',
                          style: TextStyle(
                              color: radiologyMuted,
                              fontSize: 12,
                              height: 1.35),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(46),
                          side: const BorderSide(color: radiologyBorder),
                        ),
                        child: const Text('취소'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: _submit,
                        style: FilledButton.styleFrom(
                          minimumSize: const Size.fromHeight(46),
                          backgroundColor: radiologyBlue,
                        ),
                        child: const Text('회신 확정'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );
}

InputDecoration _replyInputDecoration({required String hintText}) =>
    InputDecoration(
      hintText: hintText,
      hintStyle: const TextStyle(color: radiologyMuted, fontSize: 13),
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: radiologyBorder),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: radiologyBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: radiologyBlue, width: 1.5),
      ),
      counterStyle: const TextStyle(color: radiologyMuted, fontSize: 11),
    );

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

  Future<void> _load({bool showLoading = true}) async {
    if (!mounted) {
      return;
    }
    if (showLoading) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }
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
    if (!mounted || _isSubmitting) {
      return;
    }
    setState(() => _isSubmitting = true);
    try {
      await widget.apiClient.post(
        '/api/v1/consultations/${widget.consultationId}/$action',
        body: body,
      );
      await _load(showLoading: false);
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

  Future<void> _showRejectReasonDialog() async {
    const otherReason = '기타';
    const reasons = [
      '담당 진료 범위 외',
      '추가 검사 필요',
      '환자 상태 및 정보 부족',
      '진료 일정상 수용 어려움',
      otherReason,
    ];
    final otherController = TextEditingController();
    String? selectedReason;
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) {
          final isOther = selectedReason == otherReason;
          final isValid = selectedReason != null &&
              (!isOther || otherController.text.trim().isNotEmpty);
          return AlertDialog(
            title: const Text('협진을 거절할까요?'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    value: selectedReason,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      hintText: '거절 사유를 선택해 주세요.',
                    ),
                    items: reasons
                        .map(
                          (reason) => DropdownMenuItem(
                            value: reason,
                            child: Text(
                              reason,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(growable: false),
                    onChanged: (value) {
                      setDialogState(() => selectedReason = value);
                    },
                  ),
                  if (isOther) ...[
                    const SizedBox(height: 14),
                    TextField(
                      controller: otherController,
                      autofocus: true,
                      maxLength: 2000,
                      minLines: 2,
                      maxLines: 4,
                      onChanged: (_) => setDialogState(() {}),
                      decoration: const InputDecoration(
                        hintText: '거절 사유를 입력해 주세요.',
                      ),
                    ),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('취소'),
              ),
              FilledButton(
                onPressed: isValid
                    ? () => Navigator.pop(
                          dialogContext,
                          isOther
                              ? otherController.text.trim()
                              : selectedReason,
                        )
                    : null,
                child: const Text('확인'),
              ),
            ],
          );
        },
      ),
    );
    otherController.dispose();
    if (reason == null || reason.isEmpty || !mounted) {
      return;
    }
    await _submitAction('reject', body: {'reason': reason});
  }

  Future<void> _showRespondDialogSafely() async {
    if (!mounted || _isSubmitting) {
      return;
    }
    final draft = await showDialog<_RespondDraft>(
      context: context,
      builder: (_) => const _RespondConsultationDialog(),
    );
    if (!mounted || draft == null || draft.finalOpinion.isEmpty) {
      return;
    }

    // Keep the parent detail state update outside the dialog route teardown.
    await WidgetsBinding.instance.endOfFrame;
    await Future<void>.delayed(Duration.zero);
    if (!mounted) {
      return;
    }
    await _submitAction(
      'respond',
      body: {
        'final_opinion': draft.finalOpinion,
        if (draft.treatmentPlan.isNotEmpty)
          'treatment_plan': draft.treatmentPlan,
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
              onReject: _showRejectReasonDialog,
              onStart: () => _confirmAction(
                action: 'start',
                title: '협진 검토를 시작할까요?',
                content: '협진 상태가 진행 중으로 변경됩니다.',
              ),
              onRespond: _showRespondDialogSafely,
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
          Row(
            children: [
              const Expanded(
                child: Text(
                  '협진 상세',
                  style: TextStyle(
                    color: radiologyNavy,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              ConsultationMessagesAction(
                onTap: consultationId.isEmpty
                    ? null
                    : () => RadiologyNavigation.openConsultationMessages(
                          consultationId: consultationId,
                          patientName: consultation.patientName,
                          patientNo: consultation.patientNo,
                          consultationStatus: consultation.status,
                        ),
              ),
            ],
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
                _DetailRow(
                    label: '요청 진료과', value: consultation.requesterDepartment),
                _DetailRow(label: '배정 의료진', value: consultation.assigneeName),
                _DetailRow(
                    label: '배정 진료과', value: consultation.assigneeDepartment),
                _DetailRow(
                    label: '요청 시각',
                    value: _formatDateTime(consultation.requestedAt)),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '협진 사유'),
          const SizedBox(height: 8),
          RadiologyInfoCard(
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
            child: _ConsultationReasonCard(reason: consultation.reason),
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

class _ConsultationReasonCard extends StatelessWidget {
  const _ConsultationReasonCard({required this.reason});

  final String? reason;

  @override
  Widget build(BuildContext context) {
    final display = _ConsultationReasonDisplay.fromReason(reason);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (display.plainText != null) ...[
          Text(
            display.plainText!,
            style: const TextStyle(color: radiologyNavy, height: 1.45),
          ),
          if (display.hasStructuredValues) const SizedBox(height: 10),
        ],
        if (!display.hasValues)
          const Text('등록된 협진 사유가 없습니다.',
              style: TextStyle(color: radiologyMuted)),
        if (display.analysisType != null)
          _ReasonValue(
              label: '분석 유형', value: _analysisTypeLabel(display.analysisType!)),
        if (display.aiJudgment != null) ...[
          if (display.analysisType != null) const SizedBox(height: 10),
          _ReasonValue(label: 'AI 판정', value: display.aiJudgment!),
        ],
        if (display.lesionInfo != null) ...[
          if (display.analysisType != null || display.aiJudgment != null)
            const SizedBox(height: 10),
          _ReasonValue(label: '병변 정보', value: display.lesionInfo!),
        ],
      ],
    );
  }
}

class _ReasonValue extends StatelessWidget {
  const _ReasonValue({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(color: radiologyMuted, fontSize: 11)),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(
              color: radiologyNavy,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              height: 1.35,
            ),
          ),
        ],
      );
}

class _ConsultationReasonDisplay {
  const _ConsultationReasonDisplay({
    required this.plainText,
    required this.analysisType,
    required this.aiJudgment,
    required this.lesionInfo,
  });

  factory _ConsultationReasonDisplay.fromReason(String? reason) {
    final lines = (reason ?? '')
        .split(RegExp(r'\r?\n'))
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
    const analysisTypeLabels = [
      '분석 유형',
      'analysis type',
      'analysis_type',
    ];
    const judgmentLabels = [
      'AI 판정',
      'ai judgment',
      'is_positive',
    ];
    const lesionCountLabels = [
      '병변 개수',
      'lesion count',
      'lesion_count',
    ];
    const totalVolumeLabels = [
      '병변 총 부피',
      '총 병변 부피',
      'total volume',
      'total_volume_ml',
    ];
    final analysisType = _reasonValue(lines, analysisTypeLabels);
    final aiJudgment = _reasonValue(lines, judgmentLabels);
    final lesionCount = _reasonValue(lines, lesionCountLabels);
    final totalVolume = _reasonValue(lines, totalVolumeLabels);
    final lesionParts = <String>[
      if (lesionCount != null)
        lesionCount.endsWith('개') ? lesionCount : '$lesionCount개',
      if (totalVolume != null)
        totalVolume.toLowerCase().endsWith('ml')
            ? totalVolume
            : '총 $totalVolume mL',
    ];
    return _ConsultationReasonDisplay(
      plainText: lines
              .where((line) =>
                  !_isReasonValueLine(line, analysisTypeLabels) &&
                  !_isReasonValueLine(line, judgmentLabels) &&
                  !_isReasonValueLine(line, lesionCountLabels) &&
                  !_isReasonValueLine(line, totalVolumeLabels))
              .join('\n')
              .trim()
              .isEmpty
          ? null
          : lines
              .where((line) =>
                  !_isReasonValueLine(line, analysisTypeLabels) &&
                  !_isReasonValueLine(line, judgmentLabels) &&
                  !_isReasonValueLine(line, lesionCountLabels) &&
                  !_isReasonValueLine(line, totalVolumeLabels))
              .join('\n')
              .trim(),
      analysisType: analysisType,
      aiJudgment: aiJudgment,
      lesionInfo: lesionParts.isEmpty ? null : lesionParts.join(' · '),
    );
  }

  final String? plainText;
  final String? analysisType;
  final String? aiJudgment;
  final String? lesionInfo;

  bool get hasStructuredValues =>
      analysisType != null || aiJudgment != null || lesionInfo != null;
  bool get hasValues => plainText != null || hasStructuredValues;
}

bool _isReasonValueLine(String line, List<String> labels) =>
    _reasonValue([line], labels) != null;

String? _reasonValue(List<String> lines, List<String> labels) {
  for (final line in lines) {
    for (final label in labels) {
      final pattern = RegExp(
        '^${RegExp.escape(label)}\\s*[:=：]\\s*(.+)\$',
        caseSensitive: false,
      );
      final match = pattern.firstMatch(line);
      if (match != null) {
        final value = match.group(1)?.trim();
        if (value != null && value.isNotEmpty) {
          return value;
        }
      }
    }
  }
  return null;
}

String _analysisTypeLabel(String analysisType) => switch (analysisType) {
      'HEMORRHAGIC_STROKE_CT' => 'CT 뇌출혈 분석',
      'ISCHEMIC_STROKE_DWI_ADC' => 'MRI 허혈성 뇌졸중 분석',
      'CEREBRAL_ANEURYSM_MRA' => 'MRA 뇌동맥류 분석',
      _ => analysisType,
    };

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
            child:
                const Icon(Icons.person_outline_rounded, color: radiologyBlue),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  consultation.patientName.isEmpty
                      ? '환자 정보 없음'
                      : consultation.patientName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: radiologyNavy,
                      fontSize: 17,
                      fontWeight: FontWeight.w800),
                ),
                if (consultation.patientNo.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(consultation.patientNo,
                      style:
                          const TextStyle(color: radiologyMuted, fontSize: 12)),
                ],
                if (demographics.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(demographics.join(' · '),
                      style:
                          const TextStyle(color: radiologyMuted, fontSize: 12)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (consultation.priority.isNotEmpty)
                _CompactBadge(
                    label: _priorityLabel(consultation.priority),
                    color: _priorityColor(consultation.priority)),
              if (consultation.priority.isNotEmpty) const SizedBox(height: 6),
              _CompactBadge(
                  label: _statusLabel(consultation.status),
                  color: _statusColor(consultation.status)),
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
        child: Text(label,
            style: TextStyle(
                color: color, fontSize: 11, fontWeight: FontWeight.w800)),
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
              child: Text(label,
                  style: const TextStyle(color: radiologyMuted, fontSize: 13)),
            ),
            Expanded(
              child: Text(
                _textOrFallback(value),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    color: radiologyNavy, fontWeight: FontWeight.w700),
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
      'ROUTINE' || 'NORMAL' => '비응급',
      'HIGH' || 'URGENT' => '긴급',
      'CRITICAL' => '응급',
      _ => priority,
    };

Color _priorityColor(String priority) => switch (priority) {
      'CRITICAL' => radiologyDanger,
      'HIGH' || 'URGENT' => radiologyWarning,
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
