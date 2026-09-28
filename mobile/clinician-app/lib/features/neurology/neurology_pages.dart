import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../auth/clinician_session.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'neurology_patients_page.dart';

class NeurologyEmergencyPage extends StatefulWidget {
  const NeurologyEmergencyPage(
      {super.key, required this.apiClient, required this.onOpenDetail});

  final ClinicianApiClient apiClient;
  final ValueChanged<EmergencyWorklistItem> onOpenDetail;

  @override
  State<NeurologyEmergencyPage> createState() => _NeurologyEmergencyPageState();
}

class _NeurologyEmergencyPageState extends State<NeurologyEmergencyPage> {
  List<EmergencyWorklistItem> _items = const [];
  bool _loading = true;
  String? _error;
  String? _selectedPriority;

  @override
  void initState() {
    super.initState();
    _loadWorklist();
  }

  Future<void> _loadWorklist() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await widget.apiClient.get(
        '/api/v1/neurology/emergency-worklist',
        query: {if (_selectedPriority != null) 'priority': _selectedPriority!},
      );
      final items = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) =>
              EmergencyWorklistItem.fromJson(Map<String, dynamic>.from(item)))
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

  void _selectPriority(String? priority) {
    if (_selectedPriority == priority) return;
    setState(() => _selectedPriority = priority);
    _loadWorklist();
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '응급 Worklist'),
          const SizedBox(height: 6),
          const Text('본인에게 배정된 긴급·응급 환자를 확인합니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 13)),
          const SizedBox(height: 16),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              _EmergencyFilterChip(
                  label: '전체',
                  selected: _selectedPriority == null,
                  onTap: () => _selectPriority(null)),
              const SizedBox(width: 8),
              _EmergencyFilterChip(
                  label: '긴급',
                  selected: _selectedPriority == 'EMERGENCY',
                  onTap: () => _selectPriority('EMERGENCY')),
              const SizedBox(width: 8),
              _EmergencyFilterChip(
                  label: '응급',
                  selected: _selectedPriority == 'URGENT',
                  onTap: () => _selectPriority('URGENT')),
            ]),
          ),
          const SizedBox(height: 14),
          if (_loading)
            const Center(
                child: Padding(
                    padding: EdgeInsets.all(32),
                    child: CircularProgressIndicator()))
          else if (_error != null)
            _RetryCard(message: _error!, onRetry: _loadWorklist)
          else if (_items.isEmpty)
            const RadiologyEmptyState(
                icon: Icons.emergency_outlined, message: '현재 확인할 응급 알림이 없습니다.')
          else
            ..._items.map((item) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _EmergencyWorklistCard(
                      item: item, onTap: () => widget.onOpenDetail(item)),
                )),
        ],
      );
}

class NeurologyEmergencyDetailPage extends StatefulWidget {
  const NeurologyEmergencyDetailPage(
      {super.key,
      required this.apiClient,
      required this.item,
      required this.onAcknowledged});

  final ClinicianApiClient apiClient;
  final EmergencyWorklistItem item;
  final VoidCallback onAcknowledged;

  @override
  State<NeurologyEmergencyDetailPage> createState() =>
      _NeurologyEmergencyDetailPageState();
}

class _NeurologyEmergencyDetailPageState
    extends State<NeurologyEmergencyDetailPage> {
  late EmergencyWorklistItem _item;
  bool _acknowledging = false;

  @override
  void initState() {
    super.initState();
    _item = widget.item;
  }

  Future<void> _acknowledge() async {
    if (_acknowledging || !_item.canAcknowledge) return;
    setState(() => _acknowledging = true);
    try {
      final response = await widget.apiClient
          .post('/api/v1/emergency-events/${_item.eventId}/acknowledge');
      if (!mounted) return;
      setState(() {
        _item = _item.copyWith(
          eventStatus: response['status']?.toString() ?? 'ACKNOWLEDGED',
          acknowledgedAt: response['acknowledged_at']?.toString(),
        );
      });
      widget.onAcknowledged();
    } on ClinicianApiException catch (error) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('응급 알림을 확인하지 못했습니다.')));
    } finally {
      if (mounted) setState(() => _acknowledging = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          _EmergencyPatientHeader(item: _item),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '우선순위 및 점수'),
          const SizedBox(height: 10),
          RadiologyInfoCard(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              Row(children: [
                Expanded(
                    child: _PriorityInfo(
                        label: '초기 우선순위', priority: _item.triagePriority)),
                Container(width: 1, height: 48, color: radiologyBorder),
                Expanded(
                    child: _PriorityInfo(
                        label: '현재 우선순위', priority: _item.effectivePriority)),
              ]),
              const SizedBox(height: 14),
              const Divider(height: 1, color: radiologyBorder),
              const SizedBox(height: 12),
              _DetailInfoRow(
                  label: '총점',
                  value:
                      _item.totalScore == null ? '-' : '${_item.totalScore}점',
                  icon: Icons.fact_check_outlined,
                  emphasizeValue: true),
            ]),
          ),
          const SizedBox(height: 14),
          _EmergencyDetailCard(title: '주요 정보', children: [
            _DetailInfoRow(label: 'LKW', value: _formatDateTime(_item.lkwAt)),
            _DetailInfoRow(
                label: '발병 시각', value: _formatDateTime(_item.onsetAt)),
            if (_item.symptomNote.isNotEmpty)
              _DetailInfoRow(label: '증상 메모', value: _item.symptomNote),
          ]),
          if (_item.abnormalFindings.isNotEmpty ||
              _item.redFlags.isNotEmpty) ...[
            const SizedBox(height: 14),
            _EmergencyDetailCard(title: '추가 정보', children: [
              if (_item.abnormalFindings.isNotEmpty)
                _DetailInfoRow(
                    label: '비정상 소견',
                    value: _summarizeFindings(_item.abnormalFindings)),
              if (_item.redFlags.isNotEmpty)
                _DetailInfoRow(
                    label: 'Red Flags',
                    value: _summarizeFindings(_item.redFlags)),
            ]),
          ],
          const SizedBox(height: 14),
          _EmergencyDetailCard(title: '응급 알림', children: [
            _AlarmStatusRow(item: _item),
            _DetailInfoRow(
                label: '알림 시각', value: _formatDateTime(_item.notifiedAt)),
            _DetailInfoRow(
                label: '확인 시각', value: _formatDateTime(_item.acknowledgedAt)),
          ]),
          const SizedBox(height: 22),
          FilledButton.icon(
            onPressed:
                _item.canAcknowledge && !_acknowledging ? _acknowledge : null,
            style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
                backgroundColor: radiologyBlue,
                disabledBackgroundColor: _item.isAcknowledged
                    ? const Color(0xFFE3F1E7)
                    : null,
                disabledForegroundColor:
                    _item.isAcknowledged ? radiologySuccess : null),
            icon: _acknowledging
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : Icon(_item.isAcknowledged
                    ? Icons.check_circle_outline
                    : Icons.notifications_active_outlined),
            label: Text(_item.isAcknowledged ? '확인 완료' : '응급 알림 확인'),
          ),
        ],
      );
}

class _EmergencyFilterChip extends StatelessWidget {
  const _EmergencyFilterChip(
      {required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
        selectedColor: const Color(0xFFEAF2FF),
        labelStyle: TextStyle(
            color: selected ? radiologyBlue : radiologyMuted,
            fontWeight: FontWeight.w700,
            fontSize: 12),
        side: const BorderSide(color: radiologyBorder),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      );
}

class _EmergencyWorklistCard extends StatelessWidget {
  const _EmergencyWorklistCard({required this.item, required this.onTap});
  final EmergencyWorklistItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hasSexBadge = item.sex == 'M' || item.sex == 'F';

    return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: RadiologyInfoCard(
          padding: const EdgeInsets.all(14),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _EmergencyPriorityIcon(priority: item.displayPriority),
            const SizedBox(width: 12),
            Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Row(children: [
                    Expanded(
                        child: Row(children: [
                      Flexible(
                          child: Text(
                              item.patientName.isEmpty
                                  ? '환자 정보 없음'
                                  : item.patientName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: radiologyNavy,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800))),
                      if (hasSexBadge) ...[
                        const SizedBox(width: 8),
                        _SexBadge(sex: item.sex!),
                      ],
                    ])),
                    const SizedBox(width: 8),
                    _EmergencyPriorityBadge(priority: item.displayPriority),
                  ]),
                  if (item.patientNo.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(item.patientNo,
                        style: const TextStyle(
                            color: radiologyMuted, fontSize: 12))
                  ],
                  if (item.age != null) ...[
                    const SizedBox(height: 2),
                    Text('${item.age}세',
                        style: const TextStyle(
                            color: radiologyMuted, fontSize: 12))
                  ],
                  if (item.symptomNote.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(item.symptomNote,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: radiologyNavy, fontSize: 13, height: 1.35))
                  ],
                  const SizedBox(height: 7),
                  Row(children: [
                    Icon(
                        item.isAcknowledged
                            ? Icons.check_circle_outline
                            : Icons.notifications_active_outlined,
                        color: item.isAcknowledged
                            ? radiologySuccess
                            : const Color(0xFFB45309),
                        size: 16),
                    const SizedBox(width: 4),
                    Expanded(
                        child: Text(item.isAcknowledged ? '확인 완료' : '미확인',
                            style: const TextStyle(
                                color: radiologyMuted, fontSize: 11))),
                    if (item.displayTime != null)
                      Text(_formatDateTime(item.displayTime),
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 11)),
                  ]),
                ])),
            const SizedBox(width: 4),
            const Padding(
                padding: EdgeInsets.only(top: 28),
                child:
                    Icon(Icons.chevron_right_rounded, color: radiologyMuted)),
          ]),
        ),
      );
  }
}

class _EmergencyPatientHeader extends StatelessWidget {
  const _EmergencyPatientHeader({required this.item});
  final EmergencyWorklistItem item;

  @override
  Widget build(BuildContext context) {
    final hasSexBadge = item.sex == 'M' || item.sex == 'F';

    return RadiologyInfoCard(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Row(children: [
                    Flexible(
                        child: Text(
                            item.patientName.isEmpty
                                ? '환자 정보 없음'
                                : item.patientName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                color: radiologyNavy,
                                fontSize: 16,
                                fontWeight: FontWeight.w800))),
                    if (hasSexBadge) ...[
                      const SizedBox(width: 8),
                      _SexBadge(sex: item.sex!),
                    ],
                  ]),
                  if (item.patientNo.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(item.patientNo,
                        style: const TextStyle(
                            color: radiologyMuted, fontSize: 12))
                  ],
                  if (item.age != null) ...[
                    const SizedBox(height: 3),
                    Text('${item.age}세',
                        style: const TextStyle(
                            color: radiologyMuted, fontSize: 12))
                  ],
                ])),
            _EmergencyPriorityBadge(priority: item.displayPriority),
          ]),
          const Divider(height: 24, color: radiologyBorder),
          _DetailInfoRow(
              label: '초기평가 완료', value: _formatDateTime(item.completedAt)),
          _DetailInfoRow(label: 'LKW', value: _formatDateTime(item.lkwAt)),
          if (item.symptomNote.isNotEmpty)
            _DetailInfoRow(label: '증상 메모', value: item.symptomNote),
        ]),
      );
  }
}

class _PriorityInfo extends StatelessWidget {
  const _PriorityInfo({required this.label, required this.priority});
  final String label;
  final String priority;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label,
              style: const TextStyle(color: radiologyMuted, fontSize: 12)),
          const SizedBox(height: 7),
          _EmergencyPriorityBadge(priority: priority),
        ]),
      );
}

class _EmergencyDetailCard extends StatelessWidget {
  const _EmergencyDetailCard({required this.title, required this.children});
  final String title;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title,
              style: const TextStyle(
                  color: radiologyNavy,
                  fontSize: 17,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 10),
          ...children,
        ]),
      );
}

class _DetailInfoRow extends StatelessWidget {
  const _DetailInfoRow({
    required this.label,
    required this.value,
    this.icon,
    this.emphasizeValue = false,
  });
  final String label;
  final String value;
  final IconData? icon;
  final bool emphasizeValue;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (icon != null) ...[
            Icon(icon, color: radiologyBlue, size: 20),
            const SizedBox(width: 9)
          ],
          SizedBox(
              width: 84,
              child: Text(label,
                  style: const TextStyle(
                      color: radiologyMuted,
                      fontSize: 13,
                      fontWeight: FontWeight.w500))),
          const SizedBox(width: 10),
          Expanded(
              child: Text(value,
                  style: TextStyle(
                      color: radiologyNavy,
                      fontSize: emphasizeValue ? 16 : 14,
                      fontWeight:
                          emphasizeValue ? FontWeight.w800 : FontWeight.w700,
                      height: 1.4))),
        ]),
      );
}

class _AlarmStatusRow extends StatelessWidget {
  const _AlarmStatusRow({required this.item});

  final EmergencyWorklistItem item;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(
            width: 84,
            child: Text(
              '알림 상태',
              style: TextStyle(
                color: radiologyMuted,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 10),
          RadiologyStatusChip(
            label: _eventStatusLabel(item.eventStatus),
            color: item.isAcknowledged ? radiologySuccess : radiologyWarning,
          ),
        ]),
      );
}

class _EmergencyPriorityIcon extends StatelessWidget {
  const _EmergencyPriorityIcon({required this.priority});
  final String priority;
  @override
  Widget build(BuildContext context) => Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
            color: _priorityBackground(priority),
            borderRadius: BorderRadius.circular(14)),
        child: Icon(Icons.emergency_rounded, color: _priorityColor(priority)),
      );
}

class _EmergencyPriorityBadge extends StatelessWidget {
  const _EmergencyPriorityBadge({required this.priority});
  final String priority;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
            color: _priorityBackground(priority),
            borderRadius: BorderRadius.circular(999)),
        child: Text(_priorityLabel(priority),
            style: TextStyle(
                color: _priorityColor(priority),
                fontSize: 11,
                fontWeight: FontWeight.w800)),
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
            borderRadius: BorderRadius.circular(999)),
        child: Text(sex,
            style: const TextStyle(
                color: radiologyMuted, fontSize: 11, fontWeight: FontWeight.w700)),
      );
}

class EmergencyWorklistItem {
  const EmergencyWorklistItem({
    required this.assessmentId,
    required this.encounterId,
    required this.patientName,
    required this.patientNo,
    required this.sex,
    required this.age,
    required this.totalScore,
    required this.triagePriority,
    required this.effectivePriority,
    required this.onsetAt,
    required this.lkwAt,
    required this.completedAt,
    required this.symptomNote,
    required this.assignedNeurologist,
    required this.abnormalFindings,
    required this.redFlags,
    required this.eventId,
    required this.eventStatus,
    required this.notifiedAt,
    required this.acknowledgedAt,
  });

  factory EmergencyWorklistItem.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    final assigned = json['assigned_neurologist'] as Map?;
    final event = json['event'] as Map?;
    return EmergencyWorklistItem(
      assessmentId: json['assessment_id']?.toString() ?? '',
      encounterId: json['encounter_id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      sex: patient?['sex']?.toString(),
      age: patient?['age'] as int? ?? patient?['estimated_age'] as int?,
      totalScore: json['total_score'] as int?,
      triagePriority: json['triage_priority']?.toString() ?? '',
      effectivePriority: json['effective_priority']?.toString() ?? '',
      onsetAt: json['onset_at']?.toString(),
      lkwAt: json['lkw_at']?.toString(),
      completedAt: json['completed_at']?.toString(),
      symptomNote: json['symptom_note']?.toString() ?? '',
      assignedNeurologist: assigned?['name']?.toString() ?? '',
      abnormalFindings: _stringValues(json['abnormal_findings']),
      redFlags: _stringValues(json['red_flags']),
      eventId: event?['id']?.toString() ?? '',
      eventStatus: event?['status']?.toString() ?? '',
      notifiedAt: event?['notified_at']?.toString(),
      acknowledgedAt: event?['acknowledged_at']?.toString(),
    );
  }

  final String assessmentId;
  final String encounterId;
  final String patientName;
  final String patientNo;
  final String? sex;
  final int? age;
  final int? totalScore;
  final String triagePriority;
  final String effectivePriority;
  final String? onsetAt;
  final String? lkwAt;
  final String? completedAt;
  final String symptomNote;
  final String assignedNeurologist;
  final List<String> abnormalFindings;
  final List<String> redFlags;
  final String eventId;
  final String eventStatus;
  final String? notifiedAt;
  final String? acknowledgedAt;

  String get demographics => [
        if (sex != null && sex!.isNotEmpty) sex!,
        if (age != null) '$age세'
      ].join(' / ');
  String get displayPriority =>
      effectivePriority.isNotEmpty ? effectivePriority : triagePriority;
  String? get displayTime => lkwAt ?? notifiedAt;
  bool get isAcknowledged =>
      eventStatus == 'ACKNOWLEDGED' || acknowledgedAt != null;
  bool get canAcknowledge =>
      !isAcknowledged && eventStatus == 'NOTIFIED' && eventId.isNotEmpty;

  EmergencyWorklistItem copyWith(
          {String? eventStatus, String? acknowledgedAt}) =>
      EmergencyWorklistItem(
        assessmentId: assessmentId,
        encounterId: encounterId,
        patientName: patientName,
        patientNo: patientNo,
        sex: sex,
        age: age,
        totalScore: totalScore,
        triagePriority: triagePriority,
        effectivePriority: effectivePriority,
        onsetAt: onsetAt,
        lkwAt: lkwAt,
        completedAt: completedAt,
        symptomNote: symptomNote,
        assignedNeurologist: assignedNeurologist,
        abnormalFindings: abnormalFindings,
        redFlags: redFlags,
        eventId: eventId,
        eventStatus: eventStatus ?? this.eventStatus,
        notifiedAt: notifiedAt,
        acknowledgedAt: acknowledgedAt ?? this.acknowledgedAt,
      );
}

List<String> _stringValues(dynamic value) => (value as List? ?? const [])
    .map((item) {
      if (item is Map) {
        return item['detail']?.toString() ??
            item['note']?.toString() ??
            item['label']?.toString() ??
            item['item_code']?.toString() ??
            '';
      }
      return item.toString();
    })
    .where((item) => item.isNotEmpty)
    .toList(growable: false);

String _summarizeFindings(List<String> values) {
  final unique = values
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toSet()
      .toList();
  return unique.isEmpty ? '정보 없음' : unique.join(', ');
}

Color _priorityColor(String priority) => switch (priority) {
      'EMERGENCY' => const Color(0xFFB42318),
      'URGENT' => const Color(0xFFB45309),
      _ => radiologyMuted,
    };

Color _priorityBackground(String priority) => switch (priority) {
      'EMERGENCY' => const Color(0xFFFFE8E8),
      'URGENT' => const Color(0xFFFFF0DB),
      _ => const Color(0xFFEAF2FF),
    };

String _priorityLabel(String priority) => switch (priority) {
      'EMERGENCY' => '긴급',
      'URGENT' => '응급',
      'NON_EMERGENCY' => '일반',
      _ => priority.isEmpty ? '-' : priority,
    };

String _eventStatusLabel(String status) => switch (status) {
      'NOTIFIED' => '미확인',
      'ACKNOWLEDGED' => '확인 완료',
      _ => status.isEmpty ? '-' : status,
    };

class NeurologyHomePage extends StatefulWidget {
  const NeurologyHomePage({
    super.key,
    required this.apiClient,
    required this.userName,
    required this.currentUserId,
    required this.onSelectTab,
    required this.onOpenClinicalRecords,
    required this.onOpenConsultationDetail,
  });

  final ClinicianApiClient apiClient;
  final String userName;
  final String currentUserId;
  final ValueChanged<int> onSelectTab;
  final VoidCallback onOpenClinicalRecords;
  final ValueChanged<String> onOpenConsultationDetail;

  @override
  State<NeurologyHomePage> createState() => _NeurologyHomePageState();
}

class _NeurologyHomePageState extends State<NeurologyHomePage> {
  List<_RecentStudy> _recentStudies = const [];
  List<_HomeConsultation> _recentConsultations = const [];
  List<_HomePatient> _recentPatients = const [];
  int? _emergencyCount;
  bool _loadingConsultations = true;
  bool _loadingPatients = true;
  String? _consultationsError;
  String? _patientsError;

  @override
  void initState() {
    super.initState();
    _loadEmergencyCount();
    _loadRecentStudies();
    _loadRecentConsultations();
    _loadRecentPatients();
  }

  Future<void> _loadEmergencyCount() async {
    try {
      final response = await widget.apiClient.get(
        '/api/v1/neurology/emergency-worklist',
      );
      final count = response['count'];
      final results = response['results'];
      final resolvedCount = count is num
          ? count.toInt()
          : results is List
              ? results.length
              : null;
      if (mounted) {
        setState(() => _emergencyCount = resolvedCount);
      }
    } catch (_) {
      // Keep the summary card in its existing pending state on a failed load.
    }
  }

  Future<void> _loadRecentStudies() async {
    try {
      final response = await widget.apiClient.get('/api/v1/imaging-studies');
      final studies = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _RecentStudy.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) {
        setState(() => _recentStudies = studies);
      }
    } catch (_) {
      // Recent patient rows remain available when their optional study date cannot load.
    }
  }

  Future<void> _loadRecentConsultations() async {
    setState(() {
      _loadingConsultations = true;
      _consultationsError = null;
    });
    try {
      final response = await widget.apiClient.get(
        '/api/v1/consultations',
        query: const {'viewer_relation': 'REQUESTED_BY'},
      );
      final consultations = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) =>
              _HomeConsultation.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) {
        setState(() => _recentConsultations = consultations);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _consultationsError = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _consultationsError = '최근 협진을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _loadingConsultations = false);
      }
    }
  }

  Future<void> _loadRecentPatients() async {
    setState(() {
      _loadingPatients = true;
      _patientsError = null;
    });
    try {
      final response = await widget.apiClient.get('/api/v1/patients');
      final patients = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _HomePatient.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) {
        setState(() => _recentPatients = patients);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _patientsError = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _patientsError = '최근 환자를 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _loadingPatients = false);
      }
    }
  }

  int get _consultationAttentionCount => _recentConsultations
      .where((consultation) => consultation.status == 'RESPONDED')
      .length;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 116),
        children: [
          _GreetingBanner(userName: widget.userName),
          const SizedBox(height: 22),
          const RadiologySectionTitle(title: '오늘 업무 요약'),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _SummaryCard(
                  icon: Icons.emergency_rounded,
                  iconBackground: const Color(0xFFFFE8E8),
                  iconColor: const Color(0xFFB42318),
                  label: '응급 환자',
                  value: _emergencyCount?.toString() ?? '-',
                  caption: '확인 대기',
                  onTap: () => widget.onSelectTab(0),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _SummaryCard(
                  icon: Icons.forum_outlined,
                  iconBackground: const Color(0xFFEAF2FF),
                  iconColor: radiologyBlue,
                  label: '협진 요청',
                  value: _loadingConsultations
                      ? '-'
                      : _consultationAttentionCount.toString(),
                  caption: '확인 필요',
                  onTap: () => widget.onSelectTab(3),
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),
          _HomeSectionHeader(
              title: '최근 협진', onTap: () => widget.onSelectTab(3)),
          const SizedBox(height: 8),
          _RecentConsultationsCard(
            loading: _loadingConsultations,
            error: _consultationsError,
            consultations: _recentConsultations.take(2).toList(growable: false),
            onRetry: _loadRecentConsultations,
            onTap: widget.onOpenConsultationDetail,
          ),
          const SizedBox(height: 20),
          _HomeSectionHeader(
              title: '최근 환자', onTap: () => widget.onSelectTab(1)),
          const SizedBox(height: 8),
          _RecentPatientsCard(
            loading: _loadingPatients,
            error: _patientsError,
            patients: _recentPatients.take(2).toList(growable: false),
            recentStudies: _recentStudies,
            onRetry: _loadRecentPatients,
            onTap: (patientId) => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => NeurologyPatientDetailPage(
                  apiClient: widget.apiClient,
                  patientId: patientId,
                  currentUserId: widget.currentUserId,
                  onOpenConsultationDetail: widget.onOpenConsultationDetail,
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          const _EncouragementCard(),
        ],
      );
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.iconBackground,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.caption,
    required this.onTap,
  });

  final IconData icon;
  final Color iconBackground;
  final Color iconColor;
  final String label;
  final String value;
  final String caption;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: RadiologyInfoCard(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: iconBackground,
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: iconColor),
              ),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label,
                        style: const TextStyle(
                            color: radiologyMuted,
                            fontSize: 13,
                            fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(value,
                        style: const TextStyle(
                            color: radiologyNavy,
                            fontSize: 24,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Text(caption,
                        style: const TextStyle(
                            color: radiologyMuted, fontSize: 11)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded,
                  color: radiologyMuted, size: 20),
            ],
          ),
        ),
      );
}

class _GreetingBanner extends StatelessWidget {
  const _GreetingBanner({
    required this.userName,
  });

  final String userName;

  @override
  Widget build(BuildContext context) {
    final rawName = userName.trim();

    final displayName = rawName.isEmpty
        ? '의료진'
        : rawName
            .replaceFirst(RegExp(r'^신경과\s*'), '')
            .replaceFirst(RegExp(r'^영상의학과\s*'), '');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        18,
        18,
        12,
        18,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: radiologyBorder,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            flex: 7,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$displayName님,',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '오늘도 좋은 하루 되세요.',
                  maxLines: 2,
                  style: TextStyle(
                    color: radiologyNavy,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    height: 1.2,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  '정확한 진료로 환자의 내일을\n지켜갑니다.',
                  style: TextStyle(
                    color: radiologyMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 4,
            child: Transform.scale(
              scale: 1.12,
              alignment: Alignment.centerRight,
              child: Image.asset(
                'asset/images/main2.png',
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const SizedBox.shrink(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HomeSectionHeader extends StatelessWidget {
  const _HomeSectionHeader({required this.title, required this.onTap});

  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Text(title,
              style: const TextStyle(
                  color: radiologyNavy,
                  fontSize: 19,
                  fontWeight: FontWeight.w800)),
          const Spacer(),
          TextButton.icon(
            onPressed: onTap,
            style: TextButton.styleFrom(
              foregroundColor: radiologyBlue,
              padding: const EdgeInsets.symmetric(horizontal: 4),
            ),
            icon: const Icon(Icons.chevron_right_rounded, size: 18),
            label: const Text('전체보기',
                style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ],
      );
}

class _RecentConsultationsCard extends StatelessWidget {
  const _RecentConsultationsCard({
    required this.loading,
    required this.error,
    required this.consultations,
    required this.onRetry,
    required this.onTap,
  });

  final bool loading;
  final String? error;
  final List<_HomeConsultation> consultations;
  final VoidCallback onRetry;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    if (loading) return const _CompactLoadingCard();
    if (error != null) return _RetryCard(message: error!, onRetry: onRetry);
    if (consultations.isEmpty) {
      return const _CompactEmptyCard(
          icon: Icons.forum_outlined, message: '최근 요청한 협진이 없습니다.');
    }
    return RadiologyInfoCard(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          for (var index = 0; index < consultations.length; index++) ...[
            _ConsultationRow(
                consultation: consultations[index],
                onTap: () => onTap(consultations[index].id)),
            if (index < consultations.length - 1)
              const Divider(height: 1, color: radiologyBorder),
          ],
        ],
      ),
    );
  }
}

class _RecentPatientsCard extends StatelessWidget {
  const _RecentPatientsCard({
    required this.loading,
    required this.error,
    required this.patients,
    required this.recentStudies,
    required this.onRetry,
    required this.onTap,
  });

  final bool loading;
  final String? error;
  final List<_HomePatient> patients;
  final List<_RecentStudy> recentStudies;
  final VoidCallback onRetry;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    if (loading) return const _CompactLoadingCard();
    if (error != null) return _RetryCard(message: error!, onRetry: onRetry);
    if (patients.isEmpty) {
      return const _CompactEmptyCard(
          icon: Icons.person_search_outlined, message: '최근 확인한 환자가 없습니다.');
    }
    return RadiologyInfoCard(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          for (var index = 0; index < patients.length; index++) ...[
            _PatientRow(
              patient: patients[index],
              recentStudyDate: _recentStudyDate(patients[index].id),
              onTap: () => onTap(patients[index].id),
            ),
            if (index < patients.length - 1)
              const Divider(height: 1, color: radiologyBorder),
          ],
        ],
      ),
    );
  }

  String? _recentStudyDate(String patientId) {
    for (final study in recentStudies) {
      if (study.patientId == patientId) return study.studyDateTime;
    }
    return null;
  }
}

class _ConsultationRow extends StatelessWidget {
  const _ConsultationRow({required this.consultation, required this.onTap});

  final _HomeConsultation consultation;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: consultation.id.isEmpty ? null : onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _RowIcon(icon: Icons.forum_outlined),
              const SizedBox(width: 11),
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
                                    fontWeight: FontWeight.w800))),
                        const SizedBox(width: 8),
                        _StatusBadge(status: consultation.status),
                      ],
                    ),
                    if (consultation.patientNo.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(consultation.patientNo,
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 12)),
                    ],
                    if (consultation.destinationLabel.isNotEmpty) ...[
                      const SizedBox(height: 7),
                      Text(consultation.destinationLabel,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              color: radiologyNavy,
                              fontSize: 13,
                              fontWeight: FontWeight.w600)),
                    ],
                    if (consultation.requestedAt != null) ...[
                      const SizedBox(height: 4),
                      Text(_formatDateTime(consultation.requestedAt),
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 11)),
                    ],
                  ],
                ),
              ),
              const Padding(
                  padding: EdgeInsets.only(top: 22),
                  child:
                      Icon(Icons.chevron_right_rounded, color: radiologyMuted)),
            ],
          ),
        ),
      );
}

class _PatientRow extends StatelessWidget {
  const _PatientRow(
      {required this.patient,
      required this.recentStudyDate,
      required this.onTap});

  final _HomePatient patient;
  final String? recentStudyDate;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: patient.id.isEmpty ? null : onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            children: [
              _RowIcon(
                  label: patient.name.isEmpty
                      ? null
                      : patient.name.substring(0, 1),
                  icon: Icons.person_outline_rounded),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                            child: Row(children: [
                          Flexible(
                              child: Text(
                                  patient.name.isEmpty
                                      ? '환자 정보 없음'
                                      : patient.name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                      color: radiologyNavy,
                                      fontSize: 16,
                                      fontWeight: FontWeight.w800))),
                          if (patient.sex == 'M' || patient.sex == 'F') ...[
                            const SizedBox(width: 8),
                            _SexBadge(sex: patient.sex!),
                          ],
                        ])),
                        if (patient.status.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          _StatusBadge(status: patient.status),
                        ],
                      ],
                    ),
                    if (patient.patientNo.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(patient.patientNo,
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 12)),
                    ],
                    if (patient.estimatedAge != null) ...[
                      const SizedBox(height: 3),
                      Text('${patient.estimatedAge}세',
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 12)),
                    ],
                    if (recentStudyDate != null) ...[
                      const SizedBox(height: 5),
                      Text(_formatDateTime(recentStudyDate),
                          style: const TextStyle(
                              color: radiologyMuted, fontSize: 11)),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 4),
              const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
            ],
          ),
        ),
      );
}

class _RowIcon extends StatelessWidget {
  const _RowIcon({required this.icon, this.label});

  final IconData icon;
  final String? label;

  @override
  Widget build(BuildContext context) => Container(
        width: 42,
        height: 42,
        alignment: Alignment.center,
        decoration: BoxDecoration(
            color: const Color(0xFFEAF2FF),
            borderRadius: BorderRadius.circular(14)),
        child: label == null
            ? Icon(icon, color: radiologyBlue)
            : Text(label!,
                style: const TextStyle(
                    color: radiologyBlue, fontWeight: FontWeight.w800)),
      );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final isComplete =
        {'COMPLETED', 'CLOSED', 'RESPONDED', 'ACTIVE'}.contains(status);
    final isAlert =
        {'URGENT', 'STAT', 'CRITICAL', 'REQUESTED'}.contains(status);
    final color = isAlert
        ? const Color(0xFFB42318)
        : isComplete
            ? const Color(0xFF2F7D4C)
            : radiologyBlue;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(999)),
      child: Text(_statusLabel(status),
          style: TextStyle(
              color: color, fontSize: 11, fontWeight: FontWeight.w700)),
    );
  }
}

class _CompactLoadingCard extends StatelessWidget {
  const _CompactLoadingCard();

  @override
  Widget build(BuildContext context) => const RadiologyInfoCard(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(
            child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2))),
      );
}

class _CompactEmptyCard extends StatelessWidget {
  const _CompactEmptyCard({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        child: Row(children: [
          Icon(icon, color: radiologyMuted),
          const SizedBox(width: 10),
          Text(message,
              style: const TextStyle(color: radiologyMuted, fontSize: 13))
        ]),
      );
}

class _EncouragementCard extends StatelessWidget {
  const _EncouragementCard();

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(16),
        child: const Row(
          children: [
            _RowIcon(icon: Icons.favorite_border_rounded),
            SizedBox(width: 12),
            Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Text('오늘도 수고 많으십니다.',
                      style: TextStyle(
                          color: radiologyNavy, fontWeight: FontWeight.w800)),
                  SizedBox(height: 3),
                  Text('작은 관심이 환자의 더 나은 내일을 만듭니다.',
                      style: TextStyle(color: radiologyMuted, fontSize: 12))
                ])),
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

class _RecentStudy {
  const _RecentStudy({
    required this.id,
    required this.patientId,
    required this.patientName,
    required this.modalities,
    required this.studyDateTime,
    required this.status,
    required this.criticalFinding,
  });

  factory _RecentStudy.fromJson(Map<String, dynamic> json) {
    final patient = json['patient'] as Map?;
    return _RecentStudy(
      id: json['study_id']?.toString() ?? '',
      patientId: patient?['id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      modalities: (json['modalities'] as List? ?? const [])
          .map((item) => item.toString())
          .join(', '),
      studyDateTime: json['study_datetime']?.toString(),
      status: json['status']?.toString() ?? '',
      criticalFinding: json['critical_finding'] == true,
    );
  }

  final String id;
  final String patientId;
  final String patientName;
  final String modalities;
  final String? studyDateTime;
  final String status;
  final bool criticalFinding;

  String get details => [
        if (modalities.isNotEmpty) modalities,
        if (studyDateTime != null) _formatDateTime(studyDateTime),
        if (status.isNotEmpty) status,
      ].join(' · ');
}

class _HomeConsultation {
  const _HomeConsultation({
    required this.id,
    required this.patientName,
    required this.patientNo,
    required this.type,
    required this.assigneeName,
    required this.assigneeDepartment,
    required this.status,
    required this.requestedAt,
  });

  factory _HomeConsultation.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    final assignee = json['assigned_to'] as Map?;
    return _HomeConsultation(
      id: json['consultation_id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      type: json['type']?.toString() ??
          json['consultation_type']?.toString() ??
          '',
      assigneeName: assignee?['name']?.toString() ?? '',
      assigneeDepartment: assignee?['department']?.toString() ?? '',
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
  final String status;
  final String? requestedAt;

  String get targetLabel => _consultationTypeLabel(type);

  String get destinationLabel => [
        if (targetLabel.isNotEmpty) targetLabel,
        if (assigneeName.isNotEmpty)
          assigneeName
        else if (assigneeDepartment.isNotEmpty)
          assigneeDepartment,
      ].join(' · ');
}

class _HomePatient {
  const _HomePatient({
    required this.id,
    required this.patientNo,
    required this.name,
    required this.estimatedAge,
    required this.sex,
    required this.status,
  });

  factory _HomePatient.fromJson(Map<String, dynamic> json) => _HomePatient(
        id: json['id']?.toString() ?? '',
        patientNo: json['patient_no']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
        estimatedAge: json['estimated_age'] as int?,
        sex: json['sex']?.toString(),
        status: json['status']?.toString() ?? '',
      );

  final String id;
  final String patientNo;
  final String name;
  final int? estimatedAge;
  final String? sex;
  final String status;

  String get demographics => [
        if (sex != null && sex!.isNotEmpty) sex!,
        if (estimatedAge != null) '$estimatedAge세',
      ].join(' · ');
}

class NeurologyProfilePage extends StatelessWidget {
  const NeurologyProfilePage(
      {super.key, required this.user, required this.onLogout});
  final ClinicianUser user;
  final VoidCallback onLogout;

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
                title: const Text('로그아웃하시겠습니까?'),
                content: const Text('현재 로그인 세션이 종료됩니다.'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(dialogContext, false),
                      child: const Text('취소')),
                  FilledButton(
                      onPressed: () => Navigator.pop(dialogContext, true),
                      child: const Text('로그아웃'))
                ]));
    if (confirmed == true && context.mounted) onLogout();
  }

  @override
  Widget build(BuildContext context) =>
      ListView(padding: const EdgeInsets.fromLTRB(20, 20, 20, 32), children: [
        RadiologyInfoCard(
            child: ListTile(
                leading: const CircleAvatar(
                    backgroundColor: Color(0xFFEAF2FF),
                    child: Icon(Icons.person_rounded, color: radiologyBlue)),
                title: Text(user.name.isEmpty ? '이름 정보 없음' : user.name,
                    style: const TextStyle(
                        color: radiologyNavy, fontWeight: FontWeight.w800)),
                subtitle:
                    Text(user.loginId.isNotEmpty ? user.loginId : user.email),
                trailing: const Text('신경과',
                    style: TextStyle(
                        color: radiologyBlue, fontWeight: FontWeight.w700)))),
        const SizedBox(height: 22),
        const RadiologySectionTitle(title: '설정'),
        const SizedBox(height: 10),
        const _SettingsCard(
            icon: Icons.notifications_none_rounded, title: '알림 설정'),
        const SizedBox(height: 10),
        const _SettingsCard(icon: Icons.settings_outlined, title: '앱 설정'),
        const SizedBox(height: 24),
        OutlinedButton.icon(
            onPressed: () => _confirmLogout(context),
            icon: const Icon(Icons.logout_rounded),
            label: const Text('로그아웃')),
      ]);
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.icon, required this.title});
  final IconData icon;
  final String title;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
          child: Row(children: [
        Icon(icon, color: radiologyBlue),
        const SizedBox(width: 12),
        Expanded(
            child: Text(title,
                style: const TextStyle(
                    color: radiologyNavy, fontWeight: FontWeight.w800))),
        const Icon(Icons.chevron_right_rounded, color: radiologyMuted)
      ]));
}

String _formatDateTime(String? value) {
  final dateTime = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value ?? '정보 없음';
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}

String _consultationTypeLabel(String value) => switch (value) {
      'RADIOLOGY' => '영상의학과',
      'NEUROSURGERY' => '신경외과',
      'NEUROSURGEON' => '신경외과',
      _ => value,
    };

String _statusLabel(String value) => switch (value) {
      'REQUESTED' => '요청',
      'ACCEPTED' => '수락',
      'IN_PROGRESS' => '진행 중',
      'RESPONDED' => '회신 완료',
      'CLOSED' => '완료',
      'REJECTED' => '거절',
      'CANCELLED' => '취소',
      'EXPIRED' => '만료',
      'ACTIVE' => '진료 중',
      'INACTIVE' => '비활성',
      _ => value,
    };
