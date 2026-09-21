import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyEmergencyItem {
  const NeurologyEmergencyItem({
    required this.assessmentId,
    required this.encounterId,
    required this.patientName,
    required this.patientNo,
    required this.totalScore,
    required this.priority,
    required this.lkwAt,
    required this.eventId,
    required this.eventStatus,
  });

  factory NeurologyEmergencyItem.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    final event = json['event'] as Map?;
    return NeurologyEmergencyItem(
      assessmentId: json['assessment_id']?.toString() ?? '',
      encounterId: json['encounter_id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      totalScore: (json['total_score'] as num?)?.toInt(),
      priority: json['triage_priority']?.toString() ?? '',
      lkwAt: json['lkw_at']?.toString(),
      eventId: event?['id']?.toString(),
      eventStatus: event?['status']?.toString(),
    );
  }

  final String assessmentId;
  final String encounterId;
  final String patientName;
  final String patientNo;
  final int? totalScore;
  final String priority;
  final String? lkwAt;
  final String? eventId;
  final String? eventStatus;
}

class NeurologyEmergencyWorklistPage extends StatefulWidget {
  const NeurologyEmergencyWorklistPage({
    super.key,
    required this.apiClient,
  });

  final ClinicianApiClient apiClient;

  @override
  State<NeurologyEmergencyWorklistPage> createState() =>
      _NeurologyEmergencyWorklistPageState();
}

class _NeurologyEmergencyWorklistPageState
    extends State<NeurologyEmergencyWorklistPage> {
  List<NeurologyEmergencyItem> _items = const [];
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
      final response = await widget.apiClient.get(
        '/api/v1/neurology/emergency-worklist',
      );
      final items = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => NeurologyEmergencyItem.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(growable: false);
      if (mounted) setState(() => _items = items);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '응급 Worklist를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _acknowledge(NeurologyEmergencyItem item) async {
    final eventId = item.eventId;
    if (eventId == null || eventId.isEmpty) return;
    try {
      await widget.apiClient.post(
        '/api/v1/emergency-events/$eventId/acknowledge',
      );
      await _load();
    } on ClinicianApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
            const RadiologySectionTitle(title: '응급 Worklist'),
            const SizedBox(height: 8),
            const Text(
              '본인에게 배정된 완료 평가의 간호사 선택 triage를 확인합니다.',
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
            else if (_items.isEmpty)
              const RadiologyEmptyState(
                icon: Icons.emergency_outlined,
                message: '배정된 긴급·응급 환자가 없습니다.',
              )
            else
              ..._items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: RadiologyInfoCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Expanded(
                            child: Text(
                              item.patientName.isEmpty
                                  ? '환자 정보 없음'
                                  : item.patientName,
                              style: const TextStyle(
                                color: radiologyNavy,
                                fontSize: 16,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          RadiologyStatusChip(
                            label: item.priority,
                            color: item.priority == 'EMERGENCY'
                                ? const Color(0xFFB34B58)
                                : const Color(0xFFB46912),
                          ),
                        ]),
                        const SizedBox(height: 8),
                        Text(
                          '${item.patientNo} · 스크리닝 ${item.totalScore ?? '-'} · LKW ${_format(item.lkwAt)}',
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 12),
                        ),
                        if (item.eventStatus == 'NOTIFIED') ...[
                          const SizedBox(height: 12),
                          FilledButton.icon(
                            onPressed: () => _acknowledge(item),
                            icon: const Icon(Icons.done_rounded),
                            label: const Text('알림 확인'),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      );
}

String _format(String? value) {
  final parsed = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (parsed == null) return '정보 없음';
  return '${parsed.month.toString().padLeft(2, '0')}/'
      '${parsed.day.toString().padLeft(2, '0')} '
      '${parsed.hour.toString().padLeft(2, '0')}:'
      '${parsed.minute.toString().padLeft(2, '0')}';
}
