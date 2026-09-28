import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../medications/patient_prescriptions_api.dart';
import '../profile/profile_page.dart';
import 'notifications_api.dart';

const _brandBlue = Color(0xFF356FAF);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);
const _border = Color(0xFFCFD7E8);

enum _NotificationFilter { all, unread, read }

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({
    super.key,
    required this.apiClient,
    this.onOpenMedicationReminder,
    this.onOpenAppointmentReminder,
  });

  final ApiClient apiClient;
  final Future<void> Function([DateTime? scheduledAt])?
      onOpenMedicationReminder;
  final Future<void> Function()? onOpenAppointmentReminder;

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  late final NotificationsApi _api = NotificationsApi(widget.apiClient);
  NotificationResponse? _data;
  String? _error;
  _NotificationFilter _filter = _NotificationFilter.all;

  @override
  void initState() {
    super.initState();
    notificationRefreshNotifier.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    notificationRefreshNotifier.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final value = await _api.list(
        unreadOnly: _filter == _NotificationFilter.unread,
      );
      if (mounted) {
        setState(() => _data = value);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = '알림을 불러오지 못했습니다.');
      }
    }
  }

  Future<bool> _read(PatientNotification item) async {
    if (item.isRead) return true;
    try {
      await _api.markRead(item.id);
      notificationRefreshNotifier.value++;
      await _load();
      return true;
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.message)),
        );
      }
      return false;
    }
  }

  Future<void> _openNotification(PatientNotification item) async {
    final read = await _read(item);
    if (!read) return;
    if (_opensMedicationManagement(item)) {
      await widget.onOpenMedicationReminder?.call(_scheduledAt(item));
      return;
    }
    if (_opensAppointmentManagement(item)) {
      await widget.onOpenAppointmentReminder?.call();
    }
  }

  Future<void> _changeFilter(_NotificationFilter value) async {
    if (_filter == value) return;
    setState(() => _filter = value);
    await _load();
  }

  List<PatientNotification> get _shownItems {
    final items = _data?.items ?? const <PatientNotification>[];
    if (_filter == _NotificationFilter.read) {
      return items.where((item) => item.isRead).toList();
    }
    return items;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          leading: IconButton(
            tooltip: '뒤로가기',
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => Navigator.of(context).maybePop(),
          ),
          title: const Text('알림센터'),
          actions: [
            IconButton(
              tooltip: '알림 설정',
              icon: const Icon(Icons.settings_outlined),
              onPressed: () => ProfilePage.openNotifications(
                context,
                widget.apiClient,
              ),
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
            children: [
              _FilterBar(selected: _filter, onSelected: _changeFilter),
              const SizedBox(height: 16),
              if (_data == null && _error == null)
                const Padding(
                  padding: EdgeInsets.only(top: 72),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error != null)
                _ErrorState(message: _error!, onRetry: _load)
              else if (_data!.items.isEmpty)
                const _EmptyNotifications()
              else if (_shownItems.isEmpty)
                const _FilteredEmptyNotifications()
              else
                ..._shownItems.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _NotificationCard(
                      item: item,
                      onTap: () => _openNotification(item),
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({required this.selected, required this.onSelected});

  final _NotificationFilter selected;
  final ValueChanged<_NotificationFilter> onSelected;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 8,
        children: [
          _FilterChip(
            label: '전체',
            selected: selected == _NotificationFilter.all,
            onSelected: () => onSelected(_NotificationFilter.all),
          ),
          _FilterChip(
            label: '미확인',
            selected: selected == _NotificationFilter.unread,
            onSelected: () => onSelected(_NotificationFilter.unread),
          ),
          _FilterChip(
            label: '확인',
            selected: selected == _NotificationFilter.read,
            onSelected: () => onSelected(_NotificationFilter.read),
          ),
        ],
      );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final bool selected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) => ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onSelected(),
        selectedColor: const Color(0xFFDCEBFC),
        backgroundColor: Colors.white,
        side: BorderSide(color: selected ? _brandBlue : _border),
        labelStyle: TextStyle(
          color: selected ? _brandBlue : _muted,
          fontWeight: FontWeight.w700,
        ),
      );
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.item, required this.onTap});

  final PatientNotification item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Ink(
            padding: const EdgeInsets.all(15),
            decoration: BoxDecoration(
              color: item.isRead ? Colors.white : const Color(0xFFF3F8FF),
              border: Border.all(
                color: item.isRead ? _border : const Color(0xFF9ABCE2),
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _NotificationIcon(item: item),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              item.title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: _text,
                                fontSize: 15,
                                fontWeight: item.isRead
                                    ? FontWeight.w600
                                    : FontWeight.w800,
                              ),
                            ),
                          ),
                          if (!item.isRead) ...[
                            const SizedBox(width: 7),
                            const _UnreadDot(),
                          ],
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        item.body,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: _muted,
                          fontSize: 13,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 9),
                      Row(
                        children: [
                          Text(
                            _categoryLabel(item.category),
                            style: const TextStyle(
                              color: _brandBlue,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _formatReceivedAt(item.createdAt),
                              style: const TextStyle(
                                color: _muted,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _NotificationIcon extends StatelessWidget {
  const _NotificationIcon({required this.item});

  final PatientNotification item;

  @override
  Widget build(BuildContext context) => Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: item.severity == 'CRITICAL'
              ? const Color(0xFFFFEEEE)
              : const Color(0xFFE8F1FC),
          borderRadius: BorderRadius.circular(13),
        ),
        child: Icon(
          _categoryIcon(item.category),
          color: item.severity == 'CRITICAL'
              ? const Color(0xFFE94E4E)
              : _brandBlue,
          size: 21,
        ),
      );
}

class _UnreadDot extends StatelessWidget {
  const _UnreadDot();

  @override
  Widget build(BuildContext context) => Container(
        width: 7,
        height: 7,
        decoration: const BoxDecoration(
          color: _brandBlue,
          shape: BoxShape.circle,
        ),
      );
}

class _EmptyNotifications extends StatelessWidget {
  const _EmptyNotifications();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.only(top: 92),
        child: Column(
          children: [
            Icon(Icons.notifications_none_rounded, color: _brandBlue, size: 48),
            SizedBox(height: 14),
            Text(
              '아직 도착한 알림이 없어요',
              style: TextStyle(
                color: _text,
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
            SizedBox(height: 7),
            Text(
              '예약 및 복약 알림이 도착하면 이곳에서 확인할 수 있어요.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 13, height: 1.45),
            ),
          ],
        ),
      );
}

class _FilteredEmptyNotifications extends StatelessWidget {
  const _FilteredEmptyNotifications();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.only(top: 72),
        child: Center(
          child: Text(
            '선택한 조건의 알림이 없습니다.',
            style: TextStyle(color: _muted),
          ),
        ),
      );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 72),
        child: Center(
          child: Column(
            children: [
              Text(message, style: const TextStyle(color: _muted)),
              const SizedBox(height: 8),
              TextButton(onPressed: onRetry, child: const Text('다시 시도')),
            ],
          ),
        ),
      );
}

String _categoryLabel(String category) {
  switch (category.toUpperCase()) {
    case 'EMERGENCY':
      return '중요 건강 알림';
    case 'CONSULTATION':
      return '진료 알림';
    case 'PRESCRIPTION':
      return '처방 알림';
    case 'MEDICATION_SAFETY':
      return '약물 안전 알림';
    case 'MEDICATION':
      return '복약 알림';
    case 'IMAGING':
      return '검사 결과 알림';
    case 'AI_ANALYSIS':
      return 'AI 분석 결과 알림';
    case 'APPOINTMENT':
      return '예약 알림';
    case 'SYSTEM':
      return '서비스 알림';
    case 'CRITICAL':
      return '긴급 알림';
    default:
      return category;
  }
}

IconData _categoryIcon(String category) {
  switch (category.toUpperCase()) {
    case 'EMERGENCY':
    case 'CRITICAL':
      return Icons.warning_amber_rounded;
    case 'CONSULTATION':
      return Icons.medical_services_outlined;
    case 'PRESCRIPTION':
      return Icons.medication_outlined;
    case 'MEDICATION_SAFETY':
      return Icons.health_and_safety_outlined;
    case 'MEDICATION':
      return Icons.medication_outlined;
    case 'IMAGING':
      return Icons.biotech_outlined;
    case 'AI_ANALYSIS':
      return Icons.auto_awesome_outlined;
    case 'APPOINTMENT':
      return Icons.calendar_month_outlined;
    case 'SYSTEM':
      return Icons.info_outline_rounded;
    default:
      return Icons.notifications_outlined;
  }
}

bool _opensMedicationManagement(PatientNotification item) {
  final category = item.category.toUpperCase();
  final eventType = item.data['event_type']?.toString();
  if (category == 'PRESCRIPTION' && eventType == 'PRESCRIPTION_FINALIZED') {
    final prescriptionId = item.data['prescription_id']?.toString().trim();
    return prescriptionId != null && prescriptionId.isNotEmpty;
  }

  if (category != 'MEDICATION' || eventType != 'MEDICATION_REMINDER') {
    return false;
  }

  final scheduleId = item.data['medication_schedule_id']?.toString().trim();
  return scheduleId != null && scheduleId.isNotEmpty;
}

bool _opensAppointmentManagement(PatientNotification item) =>
    item.category.toUpperCase() == 'APPOINTMENT' &&
    item.data['event_type']?.toString() == 'APPOINTMENT_REMINDER';

DateTime? _scheduledAt(PatientNotification item) =>
    parseKoreaDateTime(item.data['scheduled_at']);

String _formatReceivedAt(DateTime? value) {
  if (value == null) return '수신 시각 정보 없음';
  final local = value.toLocal();
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${local.year}.${twoDigits(local.month)}.${twoDigits(local.day)} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}
