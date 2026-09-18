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

  static void openSchedule(BuildContext context, ApiClient client) => _open(
      context,
      _MedicationSchedulePage(apiClient: client));
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
  State<MedicationsPage> createState() => _MedicationsPageState();
}

class _MedicationsPageState extends State<MedicationsPage> {
  late final PatientPrescriptionsApi _api =
      PatientPrescriptionsApi(widget.apiClient);
  List<PrescriptionItemSummary> _items = const [];
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
      final items = await _api.listItems();
      if (!mounted) return;
      setState(() {
        _items = items;
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

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            const _MedicationGuideBanner(),
            const SizedBox(height: 16),
            _TodayMedicationSummary(itemCount: _items.length),
            const SizedBox(height: 14),
            if (_loading)
              const Padding(
                  padding: EdgeInsets.symmetric(vertical: 28),
                  child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              _MedicationErrorCard(message: _error!, onRetry: _load)
            else if (_items.isNotEmpty)
              ..._groupedMedicationItems(_items).map(
                (group) => _MedicationGroup(
                  group: group,
                  onTapItem: _openPrescriptionDetail,
                ),
              ),
            const SizedBox(height: 4),
            const Text('복약 관리 메뉴',
                style: TextStyle(
                    color: _text, fontSize: 17, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            _menu(Icons.calendar_month_outlined, '복약 일정',
                '복약 예정 일정을 확인할 수 있어요.',
                () => MedicationsPage.openSchedule(context, widget.apiClient)),
            const SizedBox(height: 11),
            _menu(Icons.fact_check_outlined, '복약 기록',
                '복약 완료 내역을 확인할 수 있어요.',
                () => MedicationsPage.openHistory(context, widget.apiClient)),
            const SizedBox(height: 14),
            const _MedicationSupportCard(),
          ],
        ),
      );

  void _openPrescriptionDetail(PrescriptionItemSummary item) {
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => _PrescriptionDetailPage(item: item)));
  }

  Widget _menu(
          IconData icon, String title, String description, VoidCallback onTap) =>
      Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(17),
          child: Ink(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: const Color(0xFFDDE2F3)),
              borderRadius: BorderRadius.circular(17),
            ),
            child: Row(children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                    color: _soft, borderRadius: BorderRadius.circular(12)),
                child: Icon(icon, color: _primary, size: 21),
              ),
              const SizedBox(width: 13),
              Expanded(child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(
                            color: _text,
                            fontSize: 16,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 3),
                    Text(description,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 12)),
                  ])),
              const Icon(Icons.chevron_right_rounded, color: _muted),
            ]),
          ),
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
              child: Image.asset('assets/images/image2.png', fit: BoxFit.contain),
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

class _TodayMedicationSummary extends StatelessWidget {
  const _TodayMedicationSummary({required this.itemCount});

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
            const Expanded(child: Text('오늘의 복약', style: TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w800))),
            Text(_todayLabel(), style: const TextStyle(color: _muted, fontSize: 12)),
          ]),
          const SizedBox(height: 15),
          if (itemCount == 0)
            const _EmptyTodayMedicationContent()
          else
            Row(children: [
              Container(
                width: 54,
                height: 54,
                decoration: const BoxDecoration(color: _soft, shape: BoxShape.circle),
                child: const Icon(Icons.medication_outlined, color: _primary, size: 27),
              ),
              const SizedBox(width: 13),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('오늘 복용할 약 $itemCount개', style: const TextStyle(color: _text, fontSize: 16, fontWeight: FontWeight.w800)),
                const SizedBox(height: 5),
                const Text('처방된 복약 정보를 확인해 주세요.', style: TextStyle(color: _muted, fontSize: 12)),
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
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('오늘 복용할 약이 없어요.', style: TextStyle(color: _text, fontSize: 15, fontWeight: FontWeight.w800)),
          SizedBox(height: 5),
          Text('등록된 처방이 생기면 이곳에서 확인할 수 있어요.', style: TextStyle(color: _muted, fontSize: 12, height: 1.35)),
          SizedBox(height: 8),
          Text('오늘도 건강한 하루 되세요!', style: TextStyle(color: _primary, fontSize: 12, fontWeight: FontWeight.w700)),
        ])),
      ]);
}

class _MedicationSupportCard extends StatelessWidget {
  const _MedicationSupportCard();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F4FF),
          border: Border.all(color: const Color(0xFFDDE6FA)),
          borderRadius: BorderRadius.circular(18),
        ),
        child: const Row(children: [
          Icon(Icons.support_agent_rounded, color: _primary, size: 27),
          SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('궁금한 점이 있으신가요?', style: TextStyle(color: _text, fontWeight: FontWeight.w800)),
            SizedBox(height: 3),
            Text('고객센터로 문의하시면 빠르게 도와드릴게요.', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _muted, fontSize: 12)),
          ])),
        ]),
      );
}

String _todayLabel() {
  final today = DateTime.now();
  const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
  return '${today.year}.${today.month.toString().padLeft(2, '0')}.${today.day.toString().padLeft(2, '0')} (${weekdays[today.weekday - 1]})';
}

class _MedicationSection {
  const _MedicationSection({required this.title, required this.icon, required this.items});

  final String title;
  final IconData icon;
  final List<PrescriptionItemSummary> items;
}

List<_MedicationSection> _groupedMedicationItems(
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
        _MedicationSection(
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

class _MedicationGroup extends StatelessWidget {
  const _MedicationGroup({required this.group, required this.onTapItem});

  final _MedicationSection group;
  final ValueChanged<PrescriptionItemSummary> onTapItem;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(group.icon, color: _primary, size: 19),
            const SizedBox(width: 7),
            Expanded(child: Text(group.title, style: const TextStyle(color: _text, fontSize: 16, fontWeight: FontWeight.w800))),
            Text('${group.items.length}개', style: const TextStyle(color: _muted, fontSize: 13)),
          ]),
          const SizedBox(height: 8),
          ...group.items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: _MedicationItemCard(item: item, onTap: () => onTapItem(item)),
              )),
        ]),
      );
}

class _MedicationItemCard extends StatelessWidget {
  const _MedicationItemCard({required this.item, required this.onTap});
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
                    Text(item.medicationName.isEmpty ? '-' : item.medicationName,
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
  State<_MedicationSchedulePage> createState() => _MedicationSchedulePageState();
}

class _MedicationSchedulePageState extends State<_MedicationSchedulePage> {
  late final MedicationSchedulesApi _api = MedicationSchedulesApi(widget.apiClient);
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
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                        color: _soft, borderRadius: BorderRadius.circular(16)),
                    child: const Text('오늘',
                        style: TextStyle(color: _primary, fontSize: 12, fontWeight: FontWeight.w700))),
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
              ..._groupedSchedules(_schedules).map((group) => _ScheduleGroup(group: group)),
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
    final weekStart = selectedDate.subtract(Duration(days: selectedDate.weekday - 1));
    final days = List.generate(7, (index) => weekStart.add(Duration(days: index)));
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
              onPressed: () => onSelect(selectedDate.subtract(const Duration(days: 7))),
              icon: const Icon(Icons.chevron_left_rounded, color: _primary)),
          Expanded(
              child: Text('${selectedDate.year}년 ${selectedDate.month}월',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: _text, fontWeight: FontWeight.w800))),
          IconButton(
              visualDensity: VisualDensity.compact,
              onPressed: () => onSelect(selectedDate.add(const Duration(days: 7))),
              icon: const Icon(Icons.chevron_right_rounded, color: _primary)),
        ]),
        const SizedBox(height: 7),
        Row(children: [
          for (var index = 0; index < days.length; index++)
            Expanded(child: _WeekDayCell(
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
  const _WeekDayCell({required this.date, required this.label, required this.selected, required this.onTap});

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
                  child: Text('${date.day}', style: TextStyle(color: selected ? Colors.white : _text, fontSize: 13, fontWeight: FontWeight.w700))),
            ]),
          ),
        ),
      );
}

class _ScheduleSection {
  const _ScheduleSection({required this.title, required this.icon, required this.items});
  final String title;
  final IconData icon;
  final List<MedicationScheduleSummary> items;
}

List<_ScheduleSection> _groupedSchedules(List<MedicationScheduleSummary> schedules) {
  final groups = <String, List<MedicationScheduleSummary>>{};
  for (final schedule in schedules) {
    final slot = (schedule.timeSlot?.trim() ?? '').toUpperCase();
    final title = slot.contains('아침') || slot.contains('MORNING')
        ? '아침'
        : slot.contains('점심') || slot.contains('LUNCH') || slot.contains('NOON')
            ? '점심'
            : slot.contains('저녁') || slot.contains('EVENING') || slot.contains('NIGHT')
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
            icon: title == '저녁' ? Icons.nightlight_round : title == '기타' ? Icons.schedule_outlined : Icons.wb_sunny_outlined,
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
            Text('${group.title} (${group.items.length}개)', style: const TextStyle(color: _text, fontSize: 16, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 8),
          ...group.items.map((schedule) => Padding(
              padding: const EdgeInsets.only(bottom: 9), child: _ScheduleCard(schedule: schedule))),
        ]),
      );
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({required this.schedule});
  final MedicationScheduleSummary schedule;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
        child: Row(children: [
          const _GenericPill(),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(schedule.medicationName.isEmpty ? '-' : schedule.medicationName, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _text, fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            Text(_scheduleSubtitle(schedule), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12)),
          ])),
          if (_hasScheduleStatus(schedule.status)) _ScheduleStatusBadge(status: schedule.status!),
        ]),
      );
}

class _ScheduleStatusBadge extends StatelessWidget {
  const _ScheduleStatusBadge({required this.status});
  final String status;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(color: _soft, borderRadius: BorderRadius.circular(14)),
        child: Text(status, style: const TextStyle(color: _primary, fontSize: 11, fontWeight: FontWeight.w700)),
      );
}

class _ScheduleEmptyState extends StatelessWidget {
  const _ScheduleEmptyState();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(color: const Color(0xFFF8F9FE), border: Border.all(color: const Color(0xFFE3E6F1)), borderRadius: BorderRadius.circular(18)),
        child: const Column(children: [
          Icon(Icons.calendar_today_outlined, color: _primary, size: 32),
          SizedBox(height: 10),
          Text('선택한 날짜의 복약 일정이 없습니다.', style: TextStyle(color: _text, fontWeight: FontWeight.w700)),
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

DateTime _dateOnly(DateTime value) => DateTime(value.year, value.month, value.day);

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
    values.add('${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}');
  }
  if (schedule.dose?.trim().isNotEmpty == true) values.add(schedule.dose!.trim());
  if (schedule.timeSlot?.trim().isNotEmpty == true) values.add(schedule.timeSlot!.trim());
  return values.isEmpty ? '-' : values.join(' · ');
}
