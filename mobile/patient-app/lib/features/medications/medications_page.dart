import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../profile/profile_page.dart';
import 'patient_prescriptions_api.dart';

const _primary = Color(0xFF356FAF);
const _soft = Color(0xFFEAF2FC);
const _border = Color(0xFFC8D8EC);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);

class MedicationsPage extends StatefulWidget {
  const MedicationsPage({super.key, required this.apiClient});
  final ApiClient apiClient;

  static void openSchedule(BuildContext context, ApiClient client) =>
      _open(context, _MedicationSchedulePage(apiClient: client));
  static void openHistory(BuildContext context, ApiClient client) => _open(
      context,
      const _MedicationEmptyPage(
          title: '복약 기록',
          icon: Icons.fact_check_outlined,
          message: '등록된 복약 기록이 없습니다.',
          description: '복약 기록이 등록되면 이곳에서 확인할 수 있습니다.'));
  static void openNotificationSettings(BuildContext context) => _open(
      context,
      const _MedicationEmptyPage(
          title: '복약 알림 설정',
          icon: Icons.notifications_none_outlined,
          message: '설정할 복약 일정이 없습니다.',
          description: '복약 일정이 등록되면 알림을 설정할 수 있습니다.'));
  static void _open(BuildContext context, Widget page) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));

  @override
  State<MedicationsPage> createState() => MedicationsPageState();
}

class MedicationsPageState extends State<MedicationsPage> {
  late final PatientPrescriptionsApi _api =
      PatientPrescriptionsApi(widget.apiClient);
  late final MedicationSchedulesApi _schedulesApi =
      MedicationSchedulesApi(widget.apiClient);
  List<PrescriptionItemSummary> _items = const [];
  List<MedicationScheduleSummary> _todaySchedules = const [];
  String? _error;
  bool _loading = true;
  final Set<String> _takingScheduleIds = {};
  DateTime? _focusAt;

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
      final results = await Future.wait([
        _api.listItems(),
        _schedulesApi.listForDate(koreaNow()),
      ]);
      if (!mounted) return;
      setState(() {
        _items = results[0] as List<PrescriptionItemSummary>;
        _todaySchedules = results[1] as List<MedicationScheduleSummary>;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _error = '복약 정보를 불러오지 못했습니다.';
          _loading = false;
        });
      }
    }
  }

  Future<void> reload({DateTime? focusAt}) {
    _focusAt = focusAt;
    return _load();
  }

  void clearReminderFocus() {
    if (_focusAt != null && mounted) setState(() => _focusAt = null);
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            const _MedicationGuideBanner(),
            const SizedBox(height: 16),
            if (_focusAt != null) ...[
              _MedicationReminderNotice(focusAt: _focusAt!),
              const SizedBox(height: 12),
            ],
            _TodayScheduleCard(
              key: ValueKey(_focusAt == null
                  ? null
                  : '${_focusAt!.year}-${_focusAt!.month}-${_focusAt!.day}-${_focusAt!.hour}-${_focusAt!.minute}'),
              schedules: _todaySchedules,
              loading: _loading,
              takingScheduleIds: _takingScheduleIds,
              onMarkTaken: _markTaken,
              onUndoTaken: _confirmUndoTaken,
              onOpenSchedule: _openSchedule,
              focusAt: _focusAt,
            ),
            const SizedBox(height: 14),
            if (_loading)
              const Padding(
                  padding: EdgeInsets.symmetric(vertical: 28),
                  child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              _MedicationErrorCard(message: _error!, onRetry: _load)
            else
              _ActiveMedicationCard(
                items: _items,
                onTapItem: _openPrescriptionDetail,
                onViewAll: _openActiveMedicationList,
              ),
          ],
        ),
      );

  void _openPrescriptionDetail(PrescriptionItemSummary item) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _PrescriptionDetailPage(
        item: item,
        apiClient: widget.apiClient,
      ),
    ));
  }

  void _openActiveMedicationList() {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _ActiveMedicationListPage(
        items: _items,
        apiClient: widget.apiClient,
      ),
    ));
  }

  void _openSchedule() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _MedicationSchedulePage(apiClient: widget.apiClient),
      ),
    );
  }

  Future<void> _markTaken(MedicationScheduleSummary schedule) async {
    if (schedule.scheduleId.isEmpty ||
        _takingScheduleIds.contains(schedule.scheduleId)) {
      return;
    }
    setState(() => _takingScheduleIds.add(schedule.scheduleId));
    try {
      if (schedule.intakeId?.isNotEmpty == true) {
        await _schedulesApi.updateIntake(schedule.intakeId!, 'TAKEN');
      } else {
        await _schedulesApi.markTaken(schedule.scheduleId);
      }
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('복용 상태를 변경하지 못했습니다.')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('복용 상태를 저장하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _takingScheduleIds.remove(schedule.scheduleId));
      }
    }
  }

  Future<void> _confirmUndoTaken(MedicationScheduleSummary schedule) async {
    if (schedule.intakeId?.isEmpty != false ||
        _takingScheduleIds.contains(schedule.scheduleId)) {
      return;
    }
    final shouldUndo = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('복용 완료를 취소할까요?'),
        content: const Text('실수로 완료 처리한 경우 복용 상태를 되돌릴 수 있어요.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('되돌리기'),
          ),
        ],
      ),
    );
    if (shouldUndo != true || !mounted) {
      return;
    }
    setState(() => _takingScheduleIds.add(schedule.scheduleId));
    try {
      await _schedulesApi.deleteIntake(schedule.intakeId!);
      await _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('복용 상태를 변경하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _takingScheduleIds.remove(schedule.scheduleId));
      }
    }
  }
}

class _MedicationReminderNotice extends StatelessWidget {
  const _MedicationReminderNotice({required this.focusAt});

  final DateTime focusAt;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: const Color(0xFFEAF2FC),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            const Icon(Icons.notifications_active_outlined,
                color: _primary, size: 19),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '${_formatTime(focusAt)} 복약 일정을 확인해 주세요.',
                style: const TextStyle(
                  color: _text,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
}

class _MedicationGuideBanner extends StatelessWidget {
  const _MedicationGuideBanner();

  @override
  Widget build(BuildContext context) => Container(
        height: 146,
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Stack(children: [
          const Positioned(
            left: 17,
            top: 17,
            right: 126,
            child: _MedicationBannerText(),
          ),
          Positioned(
            right: -4,
            bottom: -6,
            width: 142,
            height: 142,
            child: IgnorePointer(
              child:
                  Image.asset('assets/images/image2.png', fit: BoxFit.contain),
            ),
          ),
        ]),
      );
}

class _MedicationBannerText extends StatelessWidget {
  const _MedicationBannerText();

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          _BannerLabel(),
          SizedBox(height: 10),
          Text('오늘의 복약을\n잊지 말고 챙겨보세요!',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: _text,
                  fontSize: 19,
                  height: 1.18,
                  fontWeight: FontWeight.w800)),
          SizedBox(height: 7),
          Text('정해진 시간에 꾸준히 복용하면\n더 건강한 하루를 만들 수 있어요.',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: _muted, fontSize: 11.5, height: 1.35)),
        ],
      );
}

class _BannerLabel extends StatelessWidget {
  const _BannerLabel();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
            color: const Color(0xFFDCD9FF),
            borderRadius: BorderRadius.circular(20)),
        child: const Text('오늘도 꾸준히 복용해요',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
                color: _primary, fontSize: 11, fontWeight: FontWeight.w700)),
      );
}

class _TodayScheduleCard extends StatelessWidget {
  const _TodayScheduleCard({
    super.key,
    required this.schedules,
    required this.loading,
    required this.takingScheduleIds,
    required this.onMarkTaken,
    required this.onUndoTaken,
    required this.onOpenSchedule,
    this.focusAt,
  });

  final List<MedicationScheduleSummary> schedules;
  final bool loading;
  final Set<String> takingScheduleIds;
  final ValueChanged<MedicationScheduleSummary> onMarkTaken;
  final ValueChanged<MedicationScheduleSummary> onUndoTaken;
  final VoidCallback onOpenSchedule;
  final DateTime? focusAt;

  @override
  Widget build(BuildContext context) {
    final completed = schedules.where((item) => item.status == 'TAKEN').length;
    final progress = schedules.isEmpty ? 0.0 : completed / schedules.length;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: _border),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.calendar_today_outlined,
                  color: _primary, size: 21),
              const SizedBox(width: 8),
              const Expanded(
                child: Text('오늘의 복약',
                    style: TextStyle(
                        color: _text,
                        fontSize: 18,
                        fontWeight: FontWeight.w800)),
              ),
              TextButton.icon(
                onPressed: onOpenSchedule,
                icon: const Icon(Icons.calendar_month_outlined, size: 16),
                label: Text('${_todayLabel()} 일정'),
                style: TextButton.styleFrom(
                  foregroundColor: _primary,
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (loading)
            const Center(
                child: Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator()))
          else if (schedules.isEmpty)
            const _EmptyTodayMedicationContent()
          else ...[
            Row(
              children: [
                Text('$completed / ${schedules.length} 완료',
                    style: const TextStyle(
                        color: _text,
                        fontSize: 14,
                        fontWeight: FontWeight.w800)),
                const Spacer(),
                Text('${(progress * 100).round()}%',
                    style: const TextStyle(
                        color: _primary,
                        fontSize: 14,
                        fontWeight: FontWeight.w800)),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(99),
              child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 8,
                  backgroundColor: const Color(0xFFE8E9F5)),
            ),
            const SizedBox(height: 10),
            ..._todayTimeGroups(schedules).map(
              (group) => _TodayTimeGroupCard(
                group: group,
                initiallyExpanded:
                    focusAt != null && _sameMinute(group.time, focusAt),
                takingScheduleIds: takingScheduleIds,
                onMarkTaken: onMarkTaken,
                onUndoTaken: onUndoTaken,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TodayTimeGroup {
  const _TodayTimeGroup({
    required this.time,
    required this.label,
    required this.icon,
    required this.items,
  });

  final DateTime? time;
  final String label;
  final IconData icon;
  final List<MedicationScheduleSummary> items;

  int get completedCount => items.where((item) => item.status == 'TAKEN').length;
}

List<_TodayTimeGroup> _todayTimeGroups(
  List<MedicationScheduleSummary> schedules,
) {
  final groups = <String, List<MedicationScheduleSummary>>{};
  for (final schedule in schedules) {
    final time = schedule.scheduledAt;
    final key = time == null
        ? 'unknown-${schedule.timeSlot ?? ''}'
        : '${time.year}-${time.month}-${time.day}-${time.hour}-${time.minute}';
    groups.putIfAbsent(key, () => []).add(schedule);
  }
  final result = groups.values.map((items) {
    items.sort((first, second) => (first.medicationName).compareTo(second.medicationName));
    final first = items.first;
    final slot = (first.timeSlot ?? '').toUpperCase();
    final label = slot.contains('MORNING')
        ? '아침'
        : slot.contains('LUNCH') || slot.contains('NOON')
            ? '점심'
            : slot.contains('EVENING') || slot.contains('NIGHT')
                ? '저녁'
                : slot.contains('BEDTIME')
                    ? '취침 전'
                    : '복약';
    final icon = label == '저녁' || label == '취침 전'
        ? Icons.nightlight_round
        : label == '점심'
            ? Icons.wb_sunny_outlined
            : Icons.wb_sunny_rounded;
    return _TodayTimeGroup(
      time: first.scheduledAt,
      label: label,
      icon: icon,
      items: items,
    );
  }).toList();
  result.sort((first, second) {
    final firstTime = first.time;
    final secondTime = second.time;
    if (firstTime == null || secondTime == null) return 0;
    return firstTime.compareTo(secondTime);
  });
  return result;
}

class _TodayTimeGroupCard extends StatefulWidget {
  const _TodayTimeGroupCard({
    required this.group,
    required this.initiallyExpanded,
    required this.takingScheduleIds,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final _TodayTimeGroup group;
  final bool initiallyExpanded;
  final Set<String> takingScheduleIds;
  final ValueChanged<MedicationScheduleSummary> onMarkTaken;
  final ValueChanged<MedicationScheduleSummary> onUndoTaken;

  @override
  State<_TodayTimeGroupCard> createState() => _TodayTimeGroupCardState();
}

class _TodayTimeGroupCardState extends State<_TodayTimeGroupCard> {
  late bool _expanded = widget.initiallyExpanded;

  @override
  Widget build(BuildContext context) {
    final group = widget.group;
    final previewNames = group.items
        .take(3)
        .map((item) => item.medicationName)
        .where((name) => name.isNotEmpty)
        .join(' · ');
    final visibleItems = _expanded ? group.items : group.items.take(3).toList();
    return Container(
      margin: const EdgeInsets.only(top: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FBFF),
        border: Border.all(color: _border),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.all(13),
              child: Row(
                children: [
                  Icon(group.icon, color: _primary, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${group.label} ${_formatTime(group.time)}',
                          style: const TextStyle(
                            color: _text,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        if (previewNames.isNotEmpty) ...[
                          const SizedBox(height: 3),
                          Text(
                            group.items.length > 3
                                ? '$previewNames 외 ${group.items.length - 3}종'
                                : previewNames,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: _muted, fontSize: 12),
                          ),
                        ],
                      ],
                    ),
                  ),
                  Text(
                    '${group.completedCount}/${group.items.length}',
                    style: const TextStyle(
                      color: _primary,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: _muted,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            const Divider(height: 1, color: Color(0xFFE5EAF4)),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 13),
              child: Column(
                children: [
                  for (final schedule in visibleItems)
                    _TodayScheduleRow(
                      schedule: schedule,
                      saving: widget.takingScheduleIds.contains(schedule.scheduleId),
                      onMarkTaken: () => widget.onMarkTaken(schedule),
                      onUndoTaken: () => widget.onUndoTaken(schedule),
                    ),
                ],
              ),
            ),
          ],
          if (!_expanded && group.items.length > 3)
            TextButton(
              onPressed: () => setState(() => _expanded = true),
              child: Text('전체 보기 (${group.items.length}개)'),
            ),
        ],
      ),
    );
  }
}

class _TodayScheduleRow extends StatelessWidget {
  const _TodayScheduleRow({
    required this.schedule,
    required this.saving,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final MedicationScheduleSummary schedule;
  final bool saving;
  final VoidCallback onMarkTaken;
  final VoidCallback onUndoTaken;

  @override
  Widget build(BuildContext context) {
    final taken = schedule.status == 'TAKEN';
    final time = schedule.scheduledAt;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 11),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: Color(0xFFEDF0F7))),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 58,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_formatTime(time),
                    style: const TextStyle(
                        color: _text,
                        fontSize: 14,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 3),
                Row(children: [
                  Icon(_timeSlotIcon(schedule.timeSlot),
                      color: _primary, size: 14),
                  const SizedBox(width: 3),
                  Expanded(
                      child: Text(_timeSlotText(schedule.timeSlot),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: _muted, fontSize: 11))),
                ]),
              ],
            ),
          ),
          _MedicationStatusButton(
            taken: taken,
            enabled: !saving,
            onTap: taken ? onUndoTaken : onMarkTaken,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    schedule.medicationName.isEmpty
                        ? '-'
                        : schedule.medicationName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: _text,
                        fontSize: 14,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 3),
                Text(_scheduleDose(schedule),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: _muted, fontSize: 12)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (taken)
            GestureDetector(
                onTap: saving ? null : onUndoTaken,
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.check_circle_rounded,
                      color: Color(0xFF3BAF82), size: 22),
                  const SizedBox(width: 4),
                  Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    const Text('복용 완료',
                        style: TextStyle(
                            color: Color(0xFF29986D),
                            fontSize: 12,
                            fontWeight: FontWeight.w800)),
                    if (schedule.takenAt != null)
                      Text('${_formatTime(schedule.takenAt)} 복용',
                          style: const TextStyle(color: _muted, fontSize: 10)),
                  ])
                ]))
          else
            TextButton(
              onPressed: saving ? null : onMarkTaken,
              style: TextButton.styleFrom(
                  backgroundColor: _soft,
                  foregroundColor: _primary,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap),
              child: Text(saving ? '저장 중' : '복용했어요',
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 12)),
            ),
        ],
      ),
    );
  }
}

class _MedicationStatusCircle extends StatelessWidget {
  const _MedicationStatusCircle({required this.taken});

  final bool taken;

  @override
  Widget build(BuildContext context) => Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          color: taken ? const Color(0xFF3BAF82) : Colors.white,
          shape: BoxShape.circle,
          border: Border.all(
            color: taken ? const Color(0xFF3BAF82) : _primary,
            width: 1.6,
          ),
        ),
        child: taken
            ? const Icon(Icons.check_rounded, color: Colors.white, size: 18)
            : null,
      );
}

class _MedicationStatusButton extends StatelessWidget {
  const _MedicationStatusButton({
    required this.taken,
    required this.enabled,
    required this.onTap,
  });

  final bool taken;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        enabled: enabled,
        label: taken ? '복용 완료 취소' : '복용 완료',
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: enabled ? onTap : null,
            customBorder: const CircleBorder(),
            child: SizedBox(
              width: 48,
              height: 48,
              child: Center(child: _MedicationStatusCircle(taken: taken)),
            ),
          ),
        ),
      );
}

class TodayMedicationSummary extends StatelessWidget {
  const TodayMedicationSummary({super.key, required this.itemCount});

  final int itemCount;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(17),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Expanded(
                child: Text('오늘의 복약',
                    style: TextStyle(
                        color: _text,
                        fontSize: 18,
                        fontWeight: FontWeight.w800))),
            Text(_todayLabel(),
                style: const TextStyle(color: _muted, fontSize: 12)),
          ]),
          const SizedBox(height: 15),
          if (itemCount == 0)
            const _EmptyTodayMedicationContent()
          else
            Row(children: [
              Container(
                width: 54,
                height: 54,
                decoration:
                    const BoxDecoration(color: _soft, shape: BoxShape.circle),
                child: const Icon(Icons.medication_outlined,
                    color: _primary, size: 27),
              ),
              const SizedBox(width: 13),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Text('오늘 복용할 약 $itemCount개',
                        style: const TextStyle(
                            color: _text,
                            fontSize: 16,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 5),
                    const Text('처방된 복약 정보를 확인해 주세요.',
                        style: TextStyle(color: _muted, fontSize: 12)),
                  ])),
            ]),
        ]),
      );
}

class _EmptyTodayMedicationContent extends StatelessWidget {
  const _EmptyTodayMedicationContent();

  @override
  Widget build(BuildContext context) => Row(children: [
        Container(
          width: 72,
          height: 72,
          alignment: Alignment.center,
          decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFE0E4F1), width: 8)),
          child: const Text('0/0',
              style: TextStyle(
                  color: _text, fontSize: 17, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 14),
        const Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('오늘 복용할 약이 없어요.',
              style: TextStyle(
                  color: _text, fontSize: 15, fontWeight: FontWeight.w800)),
          SizedBox(height: 5),
          Text('등록된 처방이 생기면 이곳에서 확인할 수 있어요.',
              style: TextStyle(color: _muted, fontSize: 12, height: 1.35)),
          SizedBox(height: 8),
          Text('오늘도 건강한 하루 되세요!',
              style: TextStyle(
                  color: _primary, fontSize: 12, fontWeight: FontWeight.w700)),
        ])),
      ]);
}

String _todayLabel() {
  final today = koreaNow();
  const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
  return '${today.year}.${today.month.toString().padLeft(2, '0')}.${today.day.toString().padLeft(2, '0')} (${weekdays[today.weekday - 1]})';
}

String _formatTime(DateTime? value) {
  if (value == null) {
    return '-';
  }
  return '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
}

String _timeSlotText(String? value) {
  final slot = (value ?? '').toUpperCase();
  if (slot.contains('MORNING')) {
    return '아침';
  }
  if (slot.contains('AFTERNOON') ||
      slot.contains('LUNCH') ||
      slot.contains('NOON')) {
    return '점심';
  }
  if (slot.contains('EVENING') || slot.contains('NIGHT')) {
    return '저녁';
  }
  return value?.trim().isNotEmpty == true ? value!.trim() : '복약';
}

IconData _timeSlotIcon(String? value) {
  final slot = (value ?? '').toUpperCase();
  if (slot.contains('EVENING') || slot.contains('NIGHT')) {
    return Icons.nightlight_round;
  }
  if (slot.contains('AFTERNOON') ||
      slot.contains('LUNCH') ||
      slot.contains('NOON')) {
    return Icons.wb_sunny_outlined;
  }
  return Icons.wb_sunny_outlined;
}

String _scheduleDose(MedicationScheduleSummary schedule) {
  final dose = schedule.dose?.trim() ?? '';
  final slot = _timeSlotText(schedule.timeSlot);
  return dose.isEmpty ? slot : '$dose · $slot';
}

class _ActiveMedicationCard extends StatelessWidget {
  const _ActiveMedicationCard({
    required this.items,
    required this.onTapItem,
    required this.onViewAll,
  });

  final List<PrescriptionItemSummary> items;
  final ValueChanged<PrescriptionItemSummary> onTapItem;
  final VoidCallback onViewAll;

  @override
  Widget build(BuildContext context) {
    final visibleItems = items.take(3).toList();
    final showAll = false;
    final onToggle = onViewAll;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: _border),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.medication_outlined, color: _primary, size: 22),
              const SizedBox(width: 8),
              const Expanded(
                  child: Text('처방받은 약',
                      style: TextStyle(
                          color: _text,
                          fontSize: 18,
                          fontWeight: FontWeight.w800))),
              Text('${items.length}개',
                  style: const TextStyle(
                      color: _muted,
                      fontSize: 13,
                      fontWeight: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 8),
          if (items.isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: onViewAll,
                child: const Text('전체보기'),
              ),
            ),
          if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 10),
              child: Text('처방받은 약이 없습니다.',
                  style: TextStyle(color: _muted, fontSize: 13)),
            )
          else ...[
            for (var index = 0; index < visibleItems.length; index++)
              _ActiveMedicationRow(
                item: visibleItems[index],
                showDivider: index > 0,
                onTap: () => onTapItem(visibleItems[index]),
              ),
            if (items.length > 3)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: SizedBox(
                  width: double.infinity,
                  child: TextButton.icon(
                    onPressed: onToggle,
                    icon: Icon(showAll
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded),
                    label: Text(showAll ? '접기' : '+ ${items.length - 3}개 더 보기'),
                    style: TextButton.styleFrom(
                        foregroundColor: _primary, backgroundColor: _soft),
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _ActiveMedicationRow extends StatelessWidget {
  const _ActiveMedicationRow({
    required this.item,
    required this.showDivider,
    required this.onTap,
  });

  final PrescriptionItemSummary item;
  final bool showDivider;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      type: MaterialType.transparency,
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 11),
          decoration: BoxDecoration(
            border: showDivider
                ? const Border(top: BorderSide(color: Color(0xFFEDF0F7)))
                : null,
          ),
          child: Row(
            children: [
              const _GenericPill(size: 38),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Expanded(
                          child: Text(
                              item.medicationName.isEmpty
                                  ? '-'
                                  : item.medicationName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: _text,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w800))),
                      const SizedBox(width: 6),
                      _PrescriptionPeriodBadge(item: item),
                    ]),
                    const SizedBox(height: 3),
                    Text(
                        '하루 ${item.frequencyPerDay}회${_timingSuffix(item.timing)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 12)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: _muted),
            ],
          ),
        ),
      ),
    );
  }
}

enum _PrescriptionPeriodStatus { active, upcoming, ended }

_PrescriptionPeriodStatus? _prescriptionPeriodStatus(
    PrescriptionItemSummary item) {
  final startDate = item.startDate;
  if (startDate == null || item.durationDays <= 0) {
    return null;
  }
  final today = _dateOnly(koreaNow());
  final start = _dateOnly(startDate);
  final endExclusive = start.add(Duration(days: item.durationDays));
  if (today.isBefore(start)) {
    return _PrescriptionPeriodStatus.upcoming;
  }
  if (!today.isBefore(endExclusive)) {
    return _PrescriptionPeriodStatus.ended;
  }
  return _PrescriptionPeriodStatus.active;
}

class _PrescriptionPeriodBadge extends StatelessWidget {
  const _PrescriptionPeriodBadge({required this.item});

  final PrescriptionItemSummary item;

  @override
  Widget build(BuildContext context) {
    final status = _prescriptionPeriodStatus(item);
    if (status == null) {
      return const SizedBox.shrink();
    }
    final label = switch (status) {
      _PrescriptionPeriodStatus.active => '복용 중',
      _PrescriptionPeriodStatus.upcoming => '복용 예정',
      _PrescriptionPeriodStatus.ended => '복용 종료',
    };
    final color = switch (status) {
      _PrescriptionPeriodStatus.active => const Color(0xFF2E8B64),
      _PrescriptionPeriodStatus.upcoming => _primary,
      _PrescriptionPeriodStatus.ended => _muted,
    };
    final background = switch (status) {
      _PrescriptionPeriodStatus.active => const Color(0xFFE6F5EE),
      _PrescriptionPeriodStatus.upcoming => _soft,
      _PrescriptionPeriodStatus.ended => const Color(0xFFF0F2F6),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label,
          style: TextStyle(
              color: color, fontSize: 10, fontWeight: FontWeight.w700)),
    );
  }
}

enum _PrescriptionMedicationFilter { all, active, upcoming, ended }

class _ActiveMedicationListPage extends StatefulWidget {
  const _ActiveMedicationListPage({
    required this.items,
    required this.apiClient,
  });

  final List<PrescriptionItemSummary> items;
  final ApiClient apiClient;

  @override
  State<_ActiveMedicationListPage> createState() =>
      _ActiveMedicationListPageState();
}

class _ActiveMedicationListPageState extends State<_ActiveMedicationListPage> {
  _PrescriptionMedicationFilter _selected = _PrescriptionMedicationFilter.all;

  int _count(_PrescriptionMedicationFilter filter) => switch (filter) {
        _PrescriptionMedicationFilter.all => widget.items.length,
        _PrescriptionMedicationFilter.active => widget.items
            .where((item) =>
                _prescriptionPeriodStatus(item) ==
                _PrescriptionPeriodStatus.active)
            .length,
        _PrescriptionMedicationFilter.upcoming => widget.items
            .where((item) =>
                _prescriptionPeriodStatus(item) ==
                _PrescriptionPeriodStatus.upcoming)
            .length,
        _PrescriptionMedicationFilter.ended => widget.items
            .where((item) =>
                _prescriptionPeriodStatus(item) ==
                _PrescriptionPeriodStatus.ended)
            .length,
      };

  List<PrescriptionItemSummary> get _filteredItems => switch (_selected) {
        _PrescriptionMedicationFilter.all => widget.items,
        _PrescriptionMedicationFilter.active => widget.items
            .where((item) =>
                _prescriptionPeriodStatus(item) ==
                _PrescriptionPeriodStatus.active)
            .toList(),
        _PrescriptionMedicationFilter.upcoming => widget.items
            .where((item) =>
                _prescriptionPeriodStatus(item) ==
                _PrescriptionPeriodStatus.upcoming)
            .toList(),
        _PrescriptionMedicationFilter.ended => widget.items
            .where((item) =>
                _prescriptionPeriodStatus(item) ==
                _PrescriptionPeriodStatus.ended)
            .toList(),
      };

  @override
  Widget build(BuildContext context) {
    final filteredItems = _filteredItems;
    return Scaffold(
      appBar: AppBar(title: const Text('처방받은 약')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          Text(
            '처방 약 ${widget.items.length}개',
            style: const TextStyle(
              color: _text,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final filter in _PrescriptionMedicationFilter.values)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(
                        '${_prescriptionFilterLabel(filter)} ${_count(filter)}',
                      ),
                      selected: _selected == filter,
                      onSelected: (_) => setState(() => _selected = filter),
                      selectedColor: _soft,
                      backgroundColor: Colors.white,
                      side: BorderSide(
                        color: _selected == filter ? _primary : _border,
                      ),
                      labelStyle: TextStyle(
                        color: _selected == filter ? _primary : _muted,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (filteredItems.isEmpty)
            _PrescriptionFilterEmptyState(filter: _selected)
          else
            ...filteredItems.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: _PrescriptionMedicationListItem(
                  item: item,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _PrescriptionDetailPage(
                        item: item,
                        apiClient: widget.apiClient,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

String _prescriptionFilterLabel(_PrescriptionMedicationFilter filter) =>
    switch (filter) {
      _PrescriptionMedicationFilter.all => '전체',
      _PrescriptionMedicationFilter.active => '복용 중',
      _PrescriptionMedicationFilter.upcoming => '복용 예정',
      _PrescriptionMedicationFilter.ended => '복용 종료',
    };

class _PrescriptionMedicationListItem extends StatelessWidget {
  const _PrescriptionMedicationListItem({
    required this.item,
    required this.onTap,
  });

  final PrescriptionItemSummary item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final frequency = item.frequencyPerDay > 0
        ? '하루 ${item.frequencyPerDay}회'
        : null;
    final timing = item.timing?.trim();
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: _border),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _GenericPill(size: 42),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            item.medicationName.isEmpty
                                ? '-'
                                : item.medicationName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: _text,
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        _PrescriptionPeriodBadge(item: item),
                      ],
                    ),
                    if (frequency != null) ...[
                      const SizedBox(height: 5),
                      Text(
                        frequency,
                        style: const TextStyle(color: _muted, fontSize: 12),
                      ),
                    ],
                    if (timing != null && timing.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        timing,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 12),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 4),
              const Icon(Icons.chevron_right_rounded, color: _muted),
            ],
          ),
        ),
      ),
    );
  }
}

class _PrescriptionFilterEmptyState extends StatelessWidget {
  const _PrescriptionFilterEmptyState({required this.filter});

  final _PrescriptionMedicationFilter filter;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 20),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          filter == _PrescriptionMedicationFilter.all
              ? '처방받은 약이 없습니다.'
              : '${_prescriptionFilterLabel(filter)}인 약이 없습니다.',
          textAlign: TextAlign.center,
          style: const TextStyle(color: _muted, fontSize: 13),
        ),
      );
}

class MedicationSection {
  const MedicationSection(
      {required this.title, required this.icon, required this.items});

  final String title;
  final IconData icon;
  final List<PrescriptionItemSummary> items;
}

List<MedicationSection> groupedMedicationItems(
    List<PrescriptionItemSummary> items) {
  final groups = <String, List<PrescriptionItemSummary>>{};
  for (final item in items) {
    final timing = item.timing?.trim() ?? '';
    final key = timing.contains('아침')
        ? '아침'
        : timing.contains('점심')
            ? '점심'
            : timing.contains('저녁')
                ? '저녁'
                : '복용 약';
    groups.putIfAbsent(key, () => []).add(item);
  }
  const order = ['아침', '점심', '저녁', '복용 약'];
  return [
    for (final title in order)
      if (groups.containsKey(title))
        MedicationSection(
          title: title,
          icon: title == '저녁'
              ? Icons.nightlight_round
              : title == '복용 약'
                  ? Icons.medication_outlined
                  : Icons.wb_sunny_outlined,
          items: groups[title]!,
        ),
  ];
}

class MedicationGroup extends StatelessWidget {
  const MedicationGroup(
      {super.key, required this.group, required this.onTapItem});

  final MedicationSection group;
  final ValueChanged<PrescriptionItemSummary> onTapItem;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(group.icon, color: _primary, size: 19),
            const SizedBox(width: 7),
            Expanded(
                child: Text(group.title,
                    style: const TextStyle(
                        color: _text,
                        fontSize: 16,
                        fontWeight: FontWeight.w800))),
            Text('${group.items.length}개',
                style: const TextStyle(color: _muted, fontSize: 13)),
          ]),
          const SizedBox(height: 8),
          ...group.items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: MedicationItemCard(
                    item: item, onTap: () => onTapItem(item)),
              )),
        ]),
      );
}

class MedicationItemCard extends StatelessWidget {
  const MedicationItemCard(
      {super.key, required this.item, required this.onTap});
  final PrescriptionItemSummary item;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Ink(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: _border),
                borderRadius: BorderRadius.circular(18)),
            child: Row(children: [
              const _GenericPill(),
              const SizedBox(width: 14),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Text(
                        item.medicationName.isEmpty ? '-' : item.medicationName,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: _text,
                            fontSize: 16,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Text(
                        '하루 ${item.frequencyPerDay}회${_timingSuffix(item.timing)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 13)),
                  ])),
              const Icon(Icons.chevron_right_rounded, color: _primary),
            ]),
          ),
        ),
      );
}

class _MedicationSchedulePage extends StatefulWidget {
  const _MedicationSchedulePage({required this.apiClient});

  final ApiClient apiClient;

  @override
  State<_MedicationSchedulePage> createState() =>
      _MedicationSchedulePageState();
}

class _MedicationSchedulePageState extends State<_MedicationSchedulePage> {
  late final MedicationSchedulesApi _api =
      MedicationSchedulesApi(widget.apiClient);
  late DateTime _selectedDate = _dateOnly(koreaNow());
  List<MedicationScheduleSummary> _schedules = const [];
  String? _error;
  bool _loading = true;
  final Set<String> _savingScheduleIds = {};

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
      final schedules = await _api.listForDate(_selectedDate);
      if (!mounted) return;
      setState(() {
        _schedules = schedules;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = '복약 일정을 불러오지 못했습니다.';
        _loading = false;
      });
    }
  }

  void _changeDate(DateTime date) {
    setState(() => _selectedDate = _dateOnly(date));
    _load();
  }

  Future<void> _markTaken(MedicationScheduleSummary schedule) async {
    if (schedule.scheduleId.isEmpty ||
        _savingScheduleIds.contains(schedule.scheduleId)) {
      return;
    }
    setState(() => _savingScheduleIds.add(schedule.scheduleId));
    try {
      if (schedule.intakeId?.isNotEmpty == true) {
        await _api.updateIntake(schedule.intakeId!, 'TAKEN');
      } else {
        await _api.markTaken(schedule.scheduleId);
      }
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.message)),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('복용 상태를 변경하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _savingScheduleIds.remove(schedule.scheduleId));
      }
    }
  }

  Future<void> _confirmUndoTaken(MedicationScheduleSummary schedule) async {
    if (schedule.intakeId?.isEmpty != false ||
        _savingScheduleIds.contains(schedule.scheduleId)) {
      return;
    }
    final shouldUndo = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('복용 완료를 취소할까요?'),
        content: const Text('복용 상태를 다시 변경할 수 있어요.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('되돌리기'),
          ),
        ],
      ),
    );
    if (shouldUndo != true || !mounted) return;

    setState(() => _savingScheduleIds.add(schedule.scheduleId));
    try {
      await _api.deleteIntake(schedule.intakeId!);
      await _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('복용 상태를 변경하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _savingScheduleIds.remove(schedule.scheduleId));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('복약 일정')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            _WeekCalendar(selectedDate: _selectedDate, onSelect: _changeDate),
            const SizedBox(height: 18),
            Row(children: [
              Expanded(
                  child: Text(_selectedDateTitle(_selectedDate),
                      style: const TextStyle(
                          color: _text,
                          fontSize: 19,
                          fontWeight: FontWeight.w800))),
              if (_isToday(_selectedDate))
                Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                        color: _soft, borderRadius: BorderRadius.circular(16)),
                    child: const Text('오늘',
                        style: TextStyle(
                            color: _primary,
                            fontSize: 12,
                            fontWeight: FontWeight.w700))),
            ]),
            const SizedBox(height: 12),
            if (_loading)
              const Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              _MedicationErrorCard(message: _error!, onRetry: _load)
            else if (_schedules.isEmpty)
              const _ScheduleEmptyState()
            else
              ..._groupedSchedulesByMinute(_schedules).map(
                (group) => _ScheduleGroup(
                  group: group,
                  savingScheduleIds: _savingScheduleIds,
                  onMarkTaken: _markTaken,
                  onUndoTaken: _confirmUndoTaken,
                ),
              ),
          ],
        ),
      );
}

class _WeekCalendar extends StatelessWidget {
  const _WeekCalendar({required this.selectedDate, required this.onSelect});

  final DateTime selectedDate;
  final ValueChanged<DateTime> onSelect;

  @override
  Widget build(BuildContext context) {
    final weekStart =
        selectedDate.subtract(Duration(days: selectedDate.weekday - 1));
    final days =
        List.generate(7, (index) => weekStart.add(Duration(days: index)));
    const weekdayLabels = ['월', '화', '수', '목', '금', '토', '일'];
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20)),
      child: Column(children: [
        Row(children: [
          IconButton(
              visualDensity: VisualDensity.compact,
              onPressed: () =>
                  onSelect(selectedDate.subtract(const Duration(days: 7))),
              icon: const Icon(Icons.chevron_left_rounded, color: _primary)),
          Expanded(
              child: Text('${selectedDate.year}년 ${selectedDate.month}월',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: _text, fontWeight: FontWeight.w800))),
          IconButton(
              visualDensity: VisualDensity.compact,
              onPressed: () =>
                  onSelect(selectedDate.add(const Duration(days: 7))),
              icon: const Icon(Icons.chevron_right_rounded, color: _primary)),
        ]),
        const SizedBox(height: 7),
        Row(children: [
          for (var index = 0; index < days.length; index++)
            Expanded(
                child: _WeekDayCell(
                    date: days[index],
                    label: weekdayLabels[index],
                    selected: _sameDay(days[index], selectedDate),
                    onTap: () => onSelect(days[index]))),
        ]),
      ]),
    );
  }
}

class _WeekDayCell extends StatelessWidget {
  const _WeekDayCell(
      {required this.date,
      required this.label,
      required this.selected,
      required this.onTap});

  final DateTime date;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(24),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Column(children: [
              Text(label, style: const TextStyle(color: _muted, fontSize: 11)),
              const SizedBox(height: 6),
              Container(
                  width: 32,
                  height: 32,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                      color: selected ? _primary : Colors.transparent,
                      shape: BoxShape.circle),
                  child: Text('${date.day}',
                      style: TextStyle(
                          color: selected ? Colors.white : _text,
                          fontSize: 13,
                          fontWeight: FontWeight.w700))),
            ]),
          ),
        ),
      );
}

class _ScheduleSection {
  const _ScheduleSection(
      {required this.title, required this.icon, required this.items});
  final String title;
  final IconData icon;
  final List<MedicationScheduleSummary> items;
}

List<_ScheduleSection> _groupedSchedulesByMinute(
  List<MedicationScheduleSummary> schedules,
) {
  final groups = _todayTimeGroups(schedules);
  return [
    for (final group in groups)
      _ScheduleSection(
        title: '${group.label} ${_formatTime(group.time)}',
        icon: group.icon,
        items: group.items,
      ),
  ];
}

List<_ScheduleSection> _groupedSchedules(
    List<MedicationScheduleSummary> schedules) {
  final groups = <String, List<MedicationScheduleSummary>>{};
  for (final schedule in schedules) {
    final slot = (schedule.timeSlot?.trim() ?? '').toUpperCase();
    final title = slot.contains('아침') || slot.contains('MORNING')
        ? '아침'
        : slot.contains('점심') || slot.contains('LUNCH') || slot.contains('NOON')
            ? '점심'
            : slot.contains('저녁') ||
                    slot.contains('EVENING') ||
                    slot.contains('NIGHT')
                ? '저녁'
                : '기타';
    groups.putIfAbsent(title, () => []).add(schedule);
  }
  const order = ['아침', '점심', '저녁', '기타'];
  return [
    for (final title in order)
      if (groups.containsKey(title))
        _ScheduleSection(
            title: title,
            icon: title == '저녁'
                ? Icons.nightlight_round
                : title == '기타'
                    ? Icons.schedule_outlined
                    : Icons.wb_sunny_outlined,
            items: groups[title]!),
  ];
}

class _ScheduleGroup extends StatelessWidget {
  const _ScheduleGroup({
    required this.group,
    required this.savingScheduleIds,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final _ScheduleSection group;
  final Set<String> savingScheduleIds;
  final ValueChanged<MedicationScheduleSummary> onMarkTaken;
  final ValueChanged<MedicationScheduleSummary> onUndoTaken;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: const BoxDecoration(
              color: _soft,
              borderRadius: BorderRadius.vertical(top: Radius.circular(19)),
            ),
            child: Row(children: [
              Icon(group.icon, color: _primary, size: 22),
              const SizedBox(width: 9),
              Expanded(
                child: Text(
                  '${group.title} (${group.items.length}개)',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: _text,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Column(
              children: [
                for (var index = 0; index < group.items.length; index++) ...[
                  _ScheduleCard(
                    schedule: group.items[index],
                    saving: savingScheduleIds.contains(group.items[index].scheduleId),
                    onMarkTaken: () => onMarkTaken(group.items[index]),
                    onUndoTaken: () => onUndoTaken(group.items[index]),
                  ),
                  if (index < group.items.length - 1)
                    const Divider(height: 1, color: Color(0xFFE7EDF6)),
                ],
              ],
            ),
          ),
        ]),
      );
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({
    required this.schedule,
    required this.saving,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final MedicationScheduleSummary schedule;
  final bool saving;
  final VoidCallback onMarkTaken;
  final VoidCallback onUndoTaken;

  @override
  Widget build(BuildContext context) {
    final status = schedule.status?.trim().toUpperCase();
    final dose = schedule.dose?.trim();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Row(children: [
        _ScheduleStatusIndicator(
          status: status,
          saving: saving,
          onMarkTaken: onMarkTaken,
          onUndoTaken: onUndoTaken,
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 48,
          child: Text(
            _formatTime(schedule.scheduledAt),
            style: const TextStyle(
              color: _muted,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              schedule.medicationName.isEmpty ? '-' : schedule.medicationName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: _text,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
            if (dose != null && dose.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                dose,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: _muted, fontSize: 13),
              ),
            ],
          ]),
        ),
        const SizedBox(width: 8),
        _ScheduleStatusAction(
          status: status,
          saving: saving,
          onMarkTaken: onMarkTaken,
          onUndoTaken: onUndoTaken,
        ),
      ]),
    );
  }
}

class _ScheduleStatusIndicator extends StatelessWidget {
  const _ScheduleStatusIndicator({
    required this.status,
    required this.saving,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final String? status;
  final bool saving;
  final VoidCallback onMarkTaken;
  final VoidCallback onUndoTaken;

  @override
  Widget build(BuildContext context) {
    if (status == 'SKIPPED') {
      return const SizedBox(
        width: 48,
        height: 48,
        child: Center(
          child: _ScheduleSkippedCircle(),
        ),
      );
    }
    if (status == 'PENDING' || status == 'TAKEN') {
      return _MedicationStatusButton(
        taken: status == 'TAKEN',
        enabled: !saving,
        onTap: status == 'TAKEN' ? onUndoTaken : onMarkTaken,
      );
    }
    return const SizedBox(
      width: 48,
      height: 48,
      child: Center(child: _ScheduleSkippedCircle()),
    );
  }
}

class _ScheduleSkippedCircle extends StatelessWidget {
  const _ScheduleSkippedCircle();

  @override
  Widget build(BuildContext context) => Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFFC5CCD8), width: 1.6),
        ),
      );
}

class _ScheduleStatusAction extends StatelessWidget {
  const _ScheduleStatusAction({
    required this.status,
    required this.saving,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final String? status;
  final bool saving;
  final VoidCallback onMarkTaken;
  final VoidCallback onUndoTaken;

  @override
  Widget build(BuildContext context) {
    if (status == 'TAKEN') {
      return InkWell(
        onTap: saving ? null : onUndoTaken,
        borderRadius: BorderRadius.circular(16),
        child: const _ScheduleStatusBadge(
          label: '복용 완료',
          background: Color(0xFFE6F5EE),
          foreground: Color(0xFF29986D),
        ),
      );
    }
    if (status == 'SKIPPED') {
      return const _ScheduleStatusBadge(
        label: '건너뜀',
        background: Color(0xFFF0F2F6),
        foreground: _muted,
      );
    }
    if (status == 'PENDING') {
      return OutlinedButton(
        onPressed: saving ? null : onMarkTaken,
        style: OutlinedButton.styleFrom(
          foregroundColor: _primary,
          side: const BorderSide(color: _primary),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          minimumSize: Size.zero,
          visualDensity: VisualDensity.compact,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        child: Text(
          saving ? '처리 중' : '복용했어요',
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
        ),
      );
    }
    return const SizedBox.shrink();
  }
}

class _ScheduleStatusBadge extends StatelessWidget {
  const _ScheduleStatusBadge({
    required this.label,
    required this.background,
    required this.foreground,
  });

  final String label;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: foreground,
            fontSize: 12,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _ScheduleEmptyState extends StatelessWidget {
  const _ScheduleEmptyState();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
            color: const Color(0xFFF8F9FE),
            border: Border.all(color: const Color(0xFFE3E6F1)),
            borderRadius: BorderRadius.circular(18)),
        child: const Column(children: [
          Icon(Icons.calendar_today_outlined, color: _primary, size: 32),
          SizedBox(height: 10),
          Text('선택한 날짜의 복약 일정이 없습니다.',
              style: TextStyle(color: _text, fontWeight: FontWeight.w700)),
        ]),
      );
}

class _PrescriptionDetailPage extends StatelessWidget {
  const _PrescriptionDetailPage({
    required this.item,
    required this.apiClient,
  });

  final PrescriptionItemSummary item;
  final ApiClient apiClient;

  @override
  Widget build(BuildContext context) {
    final fields = <_PrescriptionDetailField>[
      if (item.medicationCode?.trim().isNotEmpty == true)
        _PrescriptionDetailField('약 코드', item.medicationCode!.trim()),
      if (_doseText(item).isNotEmpty)
        _PrescriptionDetailField('복용량', _doseText(item)),
      if (item.frequencyPerDay > 0)
        _PrescriptionDetailField('복용 횟수', '하루 ${item.frequencyPerDay}회'),
      if (item.timing?.trim().isNotEmpty == true)
        _PrescriptionDetailField('복용 시간', item.timing!.trim()),
      if (item.route?.trim().isNotEmpty == true)
        _PrescriptionDetailField('복용 경로', item.route!.trim()),
      if (item.startDate != null)
        _PrescriptionDetailField('복용 시작일', _formatDate(item.startDate)),
      if (item.durationDays > 0)
        _PrescriptionDetailField('복용 기간', '${item.durationDays}일'),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('약 상세 정보')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: _border),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const _GenericPill(size: 60),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.medicationName.isEmpty
                                ? '-'
                                : item.medicationName,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: _text,
                              fontSize: 19,
                              height: 1.3,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          if (item.medicationCode?.trim().isNotEmpty == true) ...[
                            const SizedBox(height: 4),
                            Text(
                              item.medicationCode!.trim(),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: _muted,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    _PrescriptionPeriodBadge(item: item),
                  ],
                ),
                if (fields.isNotEmpty) ...[
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Divider(height: 1, color: _border),
                  ),
                  for (final field in fields)
                    _PrescriptionDetailRow(field: field),
                ],
              ],
            ),
          ),
          const SizedBox(height: 14),
          _PrescriptionInstructionsCard(instructions: item.instructions),
          const SizedBox(height: 14),
          _PrescriptionDetailMenu(
            icon: Icons.notifications_none_rounded,
            label: '복약 알림 설정',
            onTap: () => ProfilePage.openNotifications(context, apiClient),
          ),
        ],
      ),
    );
  }
}

class _PrescriptionDetailField {
  const _PrescriptionDetailField(this.label, this.value);

  final String label;
  final String value;
}

class _PrescriptionDetailRow extends StatelessWidget {
  const _PrescriptionDetailRow({required this.field});

  final _PrescriptionDetailField field;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 94,
              child: Text(
                field.label,
                style: const TextStyle(color: _muted, fontSize: 13),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                field.value,
                textAlign: TextAlign.right,
                softWrap: true,
                style: const TextStyle(
                  color: _text,
                  fontSize: 14,
                  height: 1.4,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
}

class _PrescriptionInstructionsCard extends StatelessWidget {
  const _PrescriptionInstructionsCard({required this.instructions});

  final String? instructions;

  List<String> get _guidance {
    final instruction = instructions?.trim();
    if (instruction?.isNotEmpty == true) {
      return instruction!
          .split(RegExp(r'\r?\n'))
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
    }
    return const [
      '처방받은 용법과 용량을 확인해 주세요.',
      '정해진 복용 시간과 횟수를 지켜 주세요.',
      '복용 방법이 궁금하거나 이상 증상이 있으면 의료진 또는 약사에게 문의해 주세요.',
    ];
  }

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.info_outline_rounded, color: _primary, size: 22),
            SizedBox(width: 9),
            Text('복약 안내',
                style: TextStyle(
                    color: _text, fontSize: 16, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 12),
          for (final guidance in _guidance) ...[
            _PrescriptionGuidanceBullet(text: guidance),
            if (guidance != _guidance.last) const SizedBox(height: 7),
          ],
        ]),
      );
}

class _PrescriptionGuidanceBullet extends StatelessWidget {
  const _PrescriptionGuidanceBullet({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Icon(Icons.circle, color: _muted, size: 4),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: _muted,
                fontSize: 14,
                height: 1.55,
              ),
            ),
          ),
        ],
      );
}

class _PrescriptionDetailMenu extends StatelessWidget {
  const _PrescriptionDetailMenu({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              border: Border.all(color: _border),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _soft,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: _primary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(label,
                    style: const TextStyle(
                        color: _text,
                        fontSize: 15,
                        fontWeight: FontWeight.w700)),
              ),
              const Icon(Icons.chevron_right_rounded, color: _muted),
            ]),
          ),
        ),
      );
}

class _GenericPill extends StatelessWidget {
  const _GenericPill({this.size = 46});
  final double size;
  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: const BoxDecoration(color: _soft, shape: BoxShape.circle),
        child: Center(
          child: Container(
            width: size * .56,
            height: size * .32,
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: _primary),
              borderRadius: BorderRadius.circular(size),
            ),
          ),
        ),
      );
}

class _MedicationErrorCard extends StatelessWidget {
  const _MedicationErrorCard({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(18)),
      child: Column(children: [
        const Icon(Icons.error_outline_rounded, color: _primary, size: 36),
        const SizedBox(height: 12),
        Text(message, textAlign: TextAlign.center),
        const SizedBox(height: 12),
        OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('다시 시도'))
      ]));
}

class _MedicationEmptyPage extends StatelessWidget {
  const _MedicationEmptyPage(
      {required this.title,
      required this.icon,
      required this.message,
      required this.description});
  final String title, message, description;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
          child: Padding(
              padding: const EdgeInsets.all(20),
              child: Container(
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 42),
                  decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border.all(color: _border),
                      borderRadius: BorderRadius.circular(18)),
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(icon, color: _primary, size: 40),
                    const SizedBox(height: 14),
                    Text(message,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                            color: _text, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 7),
                    Text(description,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: _muted, height: 1.45))
                  ])))));
}

String _timingSuffix(String? timing) =>
    timing == null || timing.trim().isEmpty ? '' : ' · ${timing.trim()}';
String _optionalText(String? value) =>
    value == null || value.trim().isEmpty ? '-' : value.trim();
String _doseText(PrescriptionItemSummary item) =>
    [item.dose, item.doseUnit].where((value) => value.isNotEmpty).join(' ');
String _formatDate(DateTime? value) => value == null
    ? '-'
    : '${value.year}.${value.month.toString().padLeft(2, '0')}.${value.day.toString().padLeft(2, '0')}';

DateTime _dateOnly(DateTime value) =>
    DateTime(value.year, value.month, value.day);

bool _sameDay(DateTime first, DateTime second) =>
    first.year == second.year &&
    first.month == second.month &&
    first.day == second.day;

bool _sameMinute(DateTime? first, DateTime? second) =>
    first != null &&
    second != null &&
    first.year == second.year &&
    first.month == second.month &&
    first.day == second.day &&
    first.hour == second.hour &&
    first.minute == second.minute;

bool _isToday(DateTime date) => _sameDay(date, koreaNow());

String _selectedDateTitle(DateTime date) {
  const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
  return '${date.month}월 ${date.day}일 (${weekdays[date.weekday - 1]})';
}

bool _hasScheduleStatus(String? status) => status?.trim().isNotEmpty == true;

String _scheduleSubtitle(MedicationScheduleSummary schedule) {
  final values = <String>[];
  if (schedule.scheduledAt != null) {
    final date = schedule.scheduledAt!;
    values.add(
        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}');
  }
  if (schedule.dose?.trim().isNotEmpty == true) {
    values.add(schedule.dose!.trim());
  }
  if (schedule.timeSlot?.trim().isNotEmpty == true) {
    values.add(schedule.timeSlot!.trim());
  }
  return values.isEmpty ? '-' : values.join(' · ');
}
