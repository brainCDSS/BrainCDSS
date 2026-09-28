import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import 'patient_prescriptions_api.dart';

const _primary = Color(0xFF7567C8);
const _soft = Color(0xFFEEEAFE);
const _border = Color(0xFFCFD7E8);
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
        _schedulesApi.listForDate(DateTime.now()),
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

  Future<void> reload() => _load();

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            const _MedicationGuideBanner(),
            const SizedBox(height: 16),
            _TodayScheduleCard(
              schedules: _todaySchedules,
              loading: _loading,
              takingScheduleIds: _takingScheduleIds,
              onMarkTaken: _markTaken,
              onUndoTaken: _confirmUndoTaken,
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
    Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => _PrescriptionDetailPage(item: item)));
  }

  void _openActiveMedicationList() {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => _ActiveMedicationListPage(items: _items),
    ));
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
      await _schedulesApi.updateIntake(schedule.intakeId!, 'SKIPPED');
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
    required this.schedules,
    required this.loading,
    required this.takingScheduleIds,
    required this.onMarkTaken,
    required this.onUndoTaken,
  });

  final List<MedicationScheduleSummary> schedules;
  final bool loading;
  final Set<String> takingScheduleIds;
  final ValueChanged<MedicationScheduleSummary> onMarkTaken;
  final ValueChanged<MedicationScheduleSummary> onUndoTaken;

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
              Text(_todayLabel(),
                  style: const TextStyle(color: _muted, fontSize: 12)),
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
            ...schedules.map((schedule) => _TodayScheduleRow(
                  schedule: schedule,
                  saving: takingScheduleIds.contains(schedule.scheduleId),
                  onMarkTaken: () => onMarkTaken(schedule),
                  onUndoTaken: () => onUndoTaken(schedule),
                )),
          ],
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
          if (taken)
            const SizedBox(width: 28)
          else
            GestureDetector(
              onTap: saving ? null : onMarkTaken,
              child: Icon(Icons.radio_button_unchecked_rounded,
                  color: saving
                      ? const Color(0xFFE1E3EE)
                      : const Color(0xFFB9B5EC),
                  size: 28),
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
  final today = DateTime.now();
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
  final today = _dateOnly(DateTime.now());
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

class _ActiveMedicationListPage extends StatelessWidget {
  const _ActiveMedicationListPage({required this.items});

  final List<PrescriptionItemSummary> items;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('처방받은 약')),
      body: ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final item = items[index];
          return _ActiveMedicationRow(
            item: item,
            showDivider: false,
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => _PrescriptionDetailPage(item: item),
              ),
            ),
          );
        },
      ),
    );
  }
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
  late DateTime _selectedDate = _dateOnly(DateTime.now());
  List<MedicationScheduleSummary> _schedules = const [];
  String? _error;
  bool _loading = true;

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
              ..._groupedSchedules(_schedules)
                  .map((group) => _ScheduleGroup(group: group)),
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
  const _ScheduleGroup({required this.group});
  final _ScheduleSection group;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(group.icon, color: _primary, size: 20),
            const SizedBox(width: 7),
            Text('${group.title} (${group.items.length}개)',
                style: const TextStyle(
                    color: _text, fontSize: 16, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 8),
          ...group.items.map((schedule) => Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: _ScheduleCard(schedule: schedule))),
        ]),
      );
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({required this.schedule});
  final MedicationScheduleSummary schedule;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: _border),
            borderRadius: BorderRadius.circular(18)),
        child: Row(children: [
          const _GenericPill(),
          const SizedBox(width: 12),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(
                    schedule.medicationName.isEmpty
                        ? '-'
                        : schedule.medicationName,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: _text,
                        fontSize: 15,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(_scheduleSubtitle(schedule),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: _muted, fontSize: 12)),
              ])),
          if (_hasScheduleStatus(schedule.status))
            _ScheduleStatusBadge(status: schedule.status!),
        ]),
      );
}

class _ScheduleStatusBadge extends StatelessWidget {
  const _ScheduleStatusBadge({required this.status});
  final String status;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
            color: _soft, borderRadius: BorderRadius.circular(14)),
        child: Text(status,
            style: const TextStyle(
                color: _primary, fontSize: 11, fontWeight: FontWeight.w700)),
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
  const _PrescriptionDetailPage({required this.item});
  final PrescriptionItemSummary item;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('처방 상세')),
        body: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
            children: [
              const _PrescriptionGuideBanner(),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: _border),
                    borderRadius: BorderRadius.circular(22)),
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        const _GenericPill(size: 54),
                        const SizedBox(width: 14),
                        Expanded(
                            child: Text(
                                item.medicationName.isEmpty
                                    ? '-'
                                    : item.medicationName,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    color: _text,
                                    fontSize: 21,
                                    height: 1.3,
                                    fontWeight: FontWeight.w800))),
                      ]),
                      const SizedBox(height: 22),
                      _PrescriptionInfoItem(
                          icon: Icons.medication_outlined,
                          label: '복용량',
                          value: _doseText(item)),
                      _PrescriptionInfoItem(
                          icon: Icons.repeat_rounded,
                          label: '복용 횟수',
                          value: '하루 ${item.frequencyPerDay}회'),
                      _PrescriptionInfoItem(
                          icon: Icons.schedule_outlined,
                          label: '복용 시점',
                          value: _optionalText(item.timing)),
                      _PrescriptionInfoItem(
                          icon: Icons.calendar_today_outlined,
                          label: '복용 시작일',
                          value: _formatDate(item.startDate)),
                      _PrescriptionInfoItem(
                          icon: Icons.date_range_outlined,
                          label: '복용 기간',
                          value: '${item.durationDays}일'),
                      if (item.instructions?.trim().isNotEmpty == true) ...[
                        const SizedBox(height: 6),
                        const Text('복약 안내',
                            style: TextStyle(color: _muted, fontSize: 13)),
                        const SizedBox(height: 7),
                        Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                                color: _soft,
                                borderRadius: BorderRadius.circular(15)),
                            child: Text(item.instructions!,
                                style: const TextStyle(
                                    color: _text, height: 1.45))),
                      ],
                    ]),
              ),
            ]),
      );
}

class _PrescriptionGuideBanner extends StatelessWidget {
  const _PrescriptionGuideBanner();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
            color: _soft, borderRadius: BorderRadius.circular(20)),
        child:
            const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.info_outline_rounded, color: _primary, size: 23),
          SizedBox(width: 11),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text('처방 안내',
                    style: TextStyle(
                        color: _text,
                        fontSize: 16,
                        fontWeight: FontWeight.w800)),
                SizedBox(height: 5),
                Text('처방 정보를 확인해보세요.',
                    style: TextStyle(
                        color: _text,
                        fontSize: 14,
                        fontWeight: FontWeight.w700)),
                SizedBox(height: 3),
                Text('복용량, 복용 횟수, 복용 시점과 기간을 확인할 수 있어요.',
                    style: TextStyle(color: _muted, fontSize: 12, height: 1.4)),
              ])),
        ]),
      );
}

class _PrescriptionInfoItem extends StatelessWidget {
  const _PrescriptionInfoItem(
      {required this.icon, required this.label, required this.value});
  final IconData icon;
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(children: [
          Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                  color: _soft, borderRadius: BorderRadius.circular(12)),
              child: Icon(icon, color: _primary, size: 20)),
          const SizedBox(width: 12),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(label,
                    style: const TextStyle(color: _muted, fontSize: 12)),
                const SizedBox(height: 3),
                Text(value,
                    style: const TextStyle(
                        color: _text,
                        fontSize: 15,
                        fontWeight: FontWeight.w700)),
              ])),
        ]),
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
              border: Border.all(color: const Color(0xFFD5D0F2)),
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

bool _isToday(DateTime date) => _sameDay(date, DateTime.now());

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
