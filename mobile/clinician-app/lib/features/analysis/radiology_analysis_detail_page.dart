import 'package:flutter/material.dart';

import 'radiology_analysis_requests_page.dart';
import '../radiology/widgets/radiology_ui.dart';

class RadiologyAnalysisDetailPage extends StatelessWidget {
  const RadiologyAnalysisDetailPage({super.key, required this.request});

  final RadiologyAnalysisRequest request;

  bool get _isUrgent => request.priority == 'STAT' || request.priority == 'URGENT';

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('AI 분석 요청 상세')),
        body: SafeArea(
          top: false,
          child: Column(
            children: [
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    if (_isUrgent) _UrgentNotice(priority: request.priority),
                    if (_isUrgent) const SizedBox(height: 12),
                    RadiologyInfoCard(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.analytics_outlined,
                                  color: radiologyBlue),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  request.analysisType.isEmpty
                                      ? '분석 종류 정보 없음'
                                      : request.analysisType,
                                  style: const TextStyle(
                                    color: radiologyNavy,
                                    fontSize: 20,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                              RadiologyStatusChip(
                                label: _statusLabel(request.status),
                                color: _statusColor(request.status),
                              ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          _InfoRow(label: '분석 ID', value: request.analysisId),
                          _InfoRow(label: '검사 Study ID', value: request.studyId),
                          _InfoRow(label: '처리 단계', value: request.stage),
                          _InfoRow(label: '우선순위', value: request.priority),
                          _InfoRow(
                            label: '요청 시각',
                            value: _formatDateTime(request.requestedAt),
                          ),
                          _InfoRow(
                            label: '완료 시각',
                            value: _formatDateTime(request.completedAt),
                          ),
                          _InfoRow(label: '모델 코드', value: request.modelCode),
                          _InfoRow(label: '모델 버전', value: request.modelVersion),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => _showRejectDialog(context),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFFB34B58),
                            minimumSize: const Size.fromHeight(50),
                          ),
                          child: const Text('거절'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => _showApproveDialog(context),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size.fromHeight(50),
                          ),
                          child: const Text('승인'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );

  Future<void> _showApproveDialog(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('AI 분석 요청을 승인하시겠습니까?'),
        content: _isUrgent
            ? Text('${request.priority} 긴급 요청입니다. 현재 Backend API 연결 전에는 승인 상태를 변경할 수 없습니다.')
            : const Text('현재 Backend API 연결 전에는 승인 상태를 변경할 수 없습니다.'),
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
    if (confirmed == true && context.mounted) {
      _showApiPendingMessage(context);
    }
  }

  Future<void> _showRejectDialog(BuildContext context) async {
    final controller = TextEditingController();
    String? selectedReason;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('AI 분석 요청 거절'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_isUrgent)
                  _UrgentNotice(priority: request.priority),
                if (_isUrgent) const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: selectedReason,
                  decoration: const InputDecoration(
                    labelText: '거절 사유',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: '입력 영상 부족', child: Text('입력 영상 부족')),
                    DropdownMenuItem(value: '분석 대상 아님', child: Text('분석 대상 아님')),
                    DropdownMenuItem(value: '기타', child: Text('기타')),
                  ],
                  onChanged: (value) => setDialogState(() => selectedReason = value),
                ),
                if (selectedReason == '기타') ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: controller,
                    maxLength: 255,
                    decoration: const InputDecoration(
                      hintText: '거절 사유를 입력해 주세요.',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('거절 확인'),
            ),
          ],
        ),
      ),
    );
    controller.dispose();
    if (confirmed == true && context.mounted) {
      _showApiPendingMessage(context);
    }
  }

  void _showApiPendingMessage(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('현재 Backend API 연결 대기 상태입니다.')),
    );
  }
}

class _UrgentNotice extends StatelessWidget {
  const _UrgentNotice({required this.priority});

  final String priority;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFFFFF1F2),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            const Icon(Icons.priority_high_rounded, color: Color(0xFFB34B58)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '$priority 긴급 요청입니다.',
                style: const TextStyle(
                  color: Color(0xFF9C3340),
                  fontWeight: FontWeight.w800,
                ),
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
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 94,
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

String _statusLabel(String status) => switch (status) {
      'QUEUED' => '대기',
      'PROCESSING' => '처리중',
      'RETRYING' => '재시도',
      'COMPLETED' => '완료',
      'FAILED' => '실패',
      'CANCELLED' => '취소',
      _ => status.isEmpty ? '정보 없음' : status,
    };

Color _statusColor(String status) => switch (status) {
      'QUEUED' || 'RETRYING' => const Color(0xFFB46912),
      'PROCESSING' => const Color(0xFF2563B8),
      'FAILED' || 'CANCELLED' => const Color(0xFFCC4D5B),
      _ => const Color(0xFF208563),
    };

String _formatDateTime(String? value) {
  if (value == null || value.isEmpty) {
    return '정보 없음';
  }
  final dateTime = DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.'
      '${dateTime.day.toString().padLeft(2, '0')} '
      '${dateTime.hour.toString().padLeft(2, '0')}:'
      '${dateTime.minute.toString().padLeft(2, '0')}';
}
