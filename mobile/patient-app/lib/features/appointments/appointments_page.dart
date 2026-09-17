import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../home/home_api.dart';
import 'appointments_api.dart';

const _primary = Color(0xFF5665B8);
const _soft = Color(0xFFE5E8FF);
const _border = Color(0xFFD8DDF4);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);
const _danger = Color(0xFFE94E4E);

enum AppointmentTab { upcoming, past }

enum ReservationStep { date, clinician, confirm }

class AppointmentsPage extends StatefulWidget {
  const AppointmentsPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  static void openReservation(BuildContext context, ApiClient apiClient,
      {VoidCallback? onChanged}) {
    Navigator.of(context).push(
      MaterialPageRoute(
          builder: (_) => _ReservationStartPage(
              apiClient: apiClient, onChanged: onChanged)),
    );
  }

  @override
  State<AppointmentsPage> createState() => AppointmentsPageState();
}

class AppointmentsPageState extends State<AppointmentsPage> {
  late final HomeApi _api;
  bool _loading = true;
  String? _error;
  List<HomeAppointment> _appointments = const [];
  AppointmentTab _selectedTab = AppointmentTab.upcoming;
  DateTime _displayedMonth = _monthStart(DateTime.now());
  DateTime? _selectedDate;

  Future<void> reload() => _load();

  void showUpcoming() => setState(() => _selectedTab = AppointmentTab.upcoming);

  void showPast() => setState(() => _selectedTab = AppointmentTab.past);

  @override
  void initState() {
    super.initState();
    _api = HomeApi(widget.apiClient);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _api.getMyAppointments();
      if (!mounted) return;
      setState(() {
        _appointments = result;
        if (_selectedDate == null) {
          _selectedDate = _initialSelectedDate(result);
          _displayedMonth = _monthStart(_selectedDate!);
        }
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
        _error = '예약 정보를 불러오지 못했습니다.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final upcoming = _appointments.where((item) {
      final date = item.scheduledAt;
      return date != null &&
          !date.isBefore(now) &&
          !{'CANCELLED', 'REJECTED', 'COMPLETED'}.contains(item.status);
    }).toList();
    final past =
        _appointments.where((item) => !upcoming.contains(item)).toList();
    final selectedUpcoming = _selectedDate == null
        ? upcoming
        : upcoming
            .where((item) =>
                _isSameDay(item.scheduledAt?.toLocal(), _selectedDate!))
            .toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          _ReserveBanner(
              onTap: () => AppointmentsPage.openReservation(
                  context, widget.apiClient,
                  onChanged: _load)),
          const SizedBox(height: 22),
          _AppointmentSummary(
            upcomingCount: upcoming.length,
            pastCount: past.length,
            selectedTab: _selectedTab,
            onUpcomingTap: showUpcoming,
            onPastTap: showPast,
          ),
          const SizedBox(height: 22),
          if (_selectedTab == AppointmentTab.upcoming) ...[
            _AppointmentCalendar(
              displayedMonth: _displayedMonth,
              selectedDate: _selectedDate,
              appointments: upcoming,
              onPreviousMonth: () => setState(() {
                _displayedMonth =
                    DateTime(_displayedMonth.year, _displayedMonth.month - 1);
              }),
              onNextMonth: () => setState(() {
                _displayedMonth =
                    DateTime(_displayedMonth.year, _displayedMonth.month + 1);
              }),
              onDateSelected: (date) => setState(() => _selectedDate = date),
            ),
            const SizedBox(height: 22),
            _SelectedDateHeader(
              date: _selectedDate,
              count: selectedUpcoming.length,
            ),
            const SizedBox(height: 10),
            if (_loading)
              const _StateCard.loading()
            else if (_error != null)
              _StateCard.error(message: _error!, onRetry: _load)
            else if (selectedUpcoming.isEmpty)
              const _StateCard.empty(
                icon: Icons.event_available_outlined,
                title: '선택한 날짜에 예약이 없습니다.',
                description: '다른 날짜를 선택해 예약 일정을 확인해 보세요.',
              )
            else
              ...selectedUpcoming.map((item) => _AppointmentTile(
                    appointment: item,
                    onTap: () => _openDetail(item),
                  )),
          ] else ...[
            const _SectionTitle('지난 예약'),
            const SizedBox(height: 10),
            if (_loading)
              const _StateCard.loading()
            else if (_error != null)
              _StateCard.error(message: _error!, onRetry: _load)
            else if (past.isEmpty)
              const _StateCard.empty(
                icon: Icons.history_rounded,
                title: '지난 예약이 없습니다.',
                description: '완료되거나 취소된 예약이 여기에 표시됩니다.',
              )
            else
              ...past.map((item) => _AppointmentTile(
                    appointment: item,
                    onTap: () => _openDetail(item),
                  )),
          ],
        ],
      ),
    );
  }

  DateTime _initialSelectedDate(List<HomeAppointment> appointments) {
    final today = _dateOnly(DateTime.now());
    final upcoming = appointments.where((item) {
      final date = item.scheduledAt;
      return date != null &&
          !date.isBefore(DateTime.now()) &&
          !{'CANCELLED', 'REJECTED', 'COMPLETED'}.contains(item.status);
    }).toList()
      ..sort((a, b) => a.scheduledAt!.compareTo(b.scheduledAt!));

    if (upcoming
        .any((item) => _isSameDay(item.scheduledAt?.toLocal(), today))) {
      return today;
    }
    return upcoming.isEmpty
        ? today
        : _dateOnly(upcoming.first.scheduledAt!.toLocal());
  }

  Future<void> _openDetail(HomeAppointment appointment) async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => AppointmentDetailPage(
          appointment: appointment, apiClient: widget.apiClient),
    ));
    await _load();
  }
}

class _ReserveBanner extends StatelessWidget {
  const _ReserveBanner({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: Ink(
          padding: const EdgeInsets.fromLTRB(20, 18, 12, 12),
          decoration: BoxDecoration(
            color: _soft,
            borderRadius: BorderRadius.circular(24),
          ),
          child: Row(
            children: [
              const Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '진료 예약하기',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: _primary,
                        fontSize: 19,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      '원하는 날짜와 의료진을 선택해\n간편하게 예약해 보세요.',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: _muted, height: 1.45),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 92,
                child: Image.asset(
                  'assets/images/hojjang_main.png',
                  fit: BoxFit.contain,
                ),
              ),
            ],
          ),
        ),
      );
}

class _AppointmentSummary extends StatelessWidget {
  const _AppointmentSummary({
    required this.upcomingCount,
    required this.pastCount,
    required this.selectedTab,
    required this.onUpcomingTap,
    required this.onPastTap,
  });

  final int upcomingCount;
  final int pastCount;
  final AppointmentTab selectedTab;
  final VoidCallback onUpcomingTap;
  final VoidCallback onPastTap;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  '내 예약',
                  style: TextStyle(
                    color: _text,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              TextButton(
                onPressed: onUpcomingTap,
                style: TextButton.styleFrom(
                  foregroundColor: _primary,
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  minimumSize: const Size(0, 36),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('전체보기'),
                    SizedBox(width: 2),
                    Icon(Icons.chevron_right_rounded, size: 18),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _AppointmentCountButton(
                  label: '예정된 예약',
                  count: upcomingCount,
                  selected: selectedTab == AppointmentTab.upcoming,
                  onTap: onUpcomingTap,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _AppointmentCountButton(
                  label: '지난 예약',
                  count: pastCount,
                  selected: selectedTab == AppointmentTab.past,
                  onTap: onPastTap,
                ),
              ),
            ],
          ),
        ],
      );
}

class _AppointmentCountButton extends StatelessWidget {
  const _AppointmentCountButton({
    required this.label,
    required this.count,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final int count;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          decoration: BoxDecoration(
            color: selected ? _soft : Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: selected ? _soft : _border),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: selected ? _primary : _muted,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Text(
                '$count',
                style: TextStyle(
                  color: selected ? _primary : _muted,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      );
}

class _AppointmentCalendar extends StatelessWidget {
  const _AppointmentCalendar({
    required this.displayedMonth,
    required this.selectedDate,
    required this.appointments,
    this.firstSelectableDate,
    this.compact = false,
    required this.onPreviousMonth,
    required this.onNextMonth,
    required this.onDateSelected,
  });

  final DateTime displayedMonth;
  final DateTime? selectedDate;
  final List<HomeAppointment> appointments;
  final DateTime? firstSelectableDate;
  final bool compact;
  final VoidCallback onPreviousMonth;
  final VoidCallback onNextMonth;
  final ValueChanged<DateTime> onDateSelected;

  @override
  Widget build(BuildContext context) {
    final firstWeekday =
        DateTime(displayedMonth.year, displayedMonth.month).weekday % 7;
    final daysInMonth =
        DateTime(displayedMonth.year, displayedMonth.month + 1, 0).day;

    return Container(
      padding: compact
          ? const EdgeInsets.fromLTRB(12, 8, 12, 10)
          : const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              IconButton(
                onPressed: onPreviousMonth,
                icon: const Icon(Icons.chevron_left_rounded, color: _primary),
                tooltip: '이전 달',
              ),
              Expanded(
                child: Text(
                  '${displayedMonth.year}년 ${displayedMonth.month}월',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: _text,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              IconButton(
                onPressed: onNextMonth,
                icon: const Icon(Icons.chevron_right_rounded, color: _primary),
                tooltip: '다음 달',
              ),
            ],
          ),
          SizedBox(height: compact ? 2 : 6),
          const Row(
            children: [
              _CalendarWeekday('일', color: Color(0xFFC75A6A)),
              _CalendarWeekday('월'),
              _CalendarWeekday('화'),
              _CalendarWeekday('수'),
              _CalendarWeekday('목'),
              _CalendarWeekday('금'),
              _CalendarWeekday('토', color: Color(0xFF5665B8)),
            ],
          ),
          SizedBox(height: compact ? 2 : 4),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: 42,
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 7,
              mainAxisExtent: compact ? 36 : 42,
            ),
            itemBuilder: (context, index) {
              final day = index - firstWeekday + 1;
              if (day < 1 || day > daysInMonth) return const SizedBox.shrink();

              final date =
                  DateTime(displayedMonth.year, displayedMonth.month, day);
              final selected = _isSameDay(date, selectedDate);
              final disabled = firstSelectableDate != null &&
                  date.isBefore(_dateOnly(firstSelectableDate!));
              final hasAppointment = appointments.any(
                (item) => _isSameDay(item.scheduledAt?.toLocal(), date),
              );

              return InkWell(
                onTap: disabled ? null : () => onDateSelected(date),
                borderRadius: BorderRadius.circular(99),
                child: Center(
                  child: Container(
                    width: compact ? 32 : 34,
                    height: compact ? 32 : 34,
                    decoration: BoxDecoration(
                      color: selected ? _primary : Colors.transparent,
                      shape: BoxShape.circle,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '$day',
                          style: TextStyle(
                            color: selected
                                ? Colors.white
                                : disabled
                                    ? const Color(0xFFB8BFCD)
                                    : _text,
                            fontSize: 13,
                            fontWeight:
                                selected ? FontWeight.w800 : FontWeight.w500,
                          ),
                        ),
                        if (hasAppointment)
                          Container(
                            width: 4,
                            height: 4,
                            margin: const EdgeInsets.only(top: 2),
                            decoration: BoxDecoration(
                              color: selected
                                  ? Colors.white
                                  : const Color(0xFF8B96E8),
                              shape: BoxShape.circle,
                            ),
                          )
                        else
                          const SizedBox(height: 6),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _CalendarWeekday extends StatelessWidget {
  const _CalendarWeekday(this.label, {this.color = _muted});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
              color: color, fontSize: 12, fontWeight: FontWeight.w700),
        ),
      );
}

class _SelectedDateHeader extends StatelessWidget {
  const _SelectedDateHeader({required this.date, required this.count});

  final DateTime? date;
  final int count;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: Text(
              date == null ? '예정된 예약' : _formatSelectedDate(date!),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                  color: _text, fontSize: 17, fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '$count건의 예약이 있습니다.',
            style: const TextStyle(color: _muted, fontSize: 12),
          ),
        ],
      );
}

class _AppointmentTile extends StatelessWidget {
  const _AppointmentTile({required this.appointment, required this.onTap});
  final HomeAppointment appointment;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final date = appointment.scheduledAt?.toLocal();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Ink(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: _border),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: _soft,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(
                  Icons.calendar_today_outlined,
                  color: _primary,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            date == null
                                ? '예약 일시 정보 없음'
                                : _formatAppointmentDate(date),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: _text,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        _AppointmentStatusBadge(status: appointment.status),
                      ],
                    ),
                    if (appointment.departmentName.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Text(
                        appointment.departmentName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: _text,
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                    if (appointment.clinicianName.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        appointment.clinicianName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 14),
                      ),
                    ],
                    if (appointment.hospitalName.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        appointment.hospitalName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 13),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 4),
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Icon(Icons.chevron_right_rounded, color: _muted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class AppointmentDetailPage extends StatefulWidget {
  const AppointmentDetailPage(
      {super.key, required this.appointment, required this.apiClient});
  final HomeAppointment appointment;
  final ApiClient apiClient;

  @override
  State<AppointmentDetailPage> createState() => _AppointmentDetailPageState();
}

class _AppointmentDetailPageState extends State<AppointmentDetailPage> {
  Map<String, dynamic>? _detail;
  String? _error;
  bool _isCancelling = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final value = await AppointmentsApi(widget.apiClient)
          .detail(widget.appointment.appointmentId);
      if (mounted)
        setState(() {
          _detail = value;
          _error = null;
        });
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '예약 상세를 불러오지 못했습니다.');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_detail == null)
      return Scaffold(
          appBar: AppBar(title: const Text('예약 상세')),
          body: Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : TextButton(
                      onPressed: _load, child: Text('$_error 다시 시도'))));
    String nested(String key) {
      final value = _detail![key];
      return value is Map ? value['name']?.toString() ?? '' : '';
    }

    final date = DateTime.tryParse(_detail!['scheduled_at']?.toString() ?? '')
        ?.toLocal();
    return Scaffold(
      appBar: AppBar(title: const Text('예약 상세')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        _InfoCard(
            title:
                nested('department').isEmpty ? '진료 예약' : nested('department'),
            rows: {
              '예약일시': date == null ? '-' : _formatDate(date),
              '병원': nested('hospital').isEmpty ? '-' : nested('hospital'),
              '의료진': nested('clinician').isEmpty ? '-' : nested('clinician'),
              '상태': _statusLabel(_detail!['status']?.toString() ?? ''),
              '예약 유형': _detail!['request_type']?.toString() ?? '-',
            }),
        const SizedBox(height: 18),
        Row(children: [
          Expanded(
              child: OutlinedButton(
                  onPressed: () async {
                    final changed = await Navigator.of(context).push<bool>(
                        MaterialPageRoute(
                            builder: (_) => _ReservationChangePage(
                                apiClient: widget.apiClient,
                                appointment: widget.appointment)));
                    if (changed == true && context.mounted)
                      Navigator.pop(context);
                  },
                  child: const Text('예약 변경'))),
          const SizedBox(width: 10),
          Expanded(
              child: OutlinedButton(
                  style: OutlinedButton.styleFrom(foregroundColor: _danger),
                  onPressed: _isCancelling ? null : () => _showCancel(context),
                  child: Text(_isCancelling ? '취소 중...' : '예약 취소'))),
        ]),
      ]),
    );
  }

  void _showCancel(BuildContext context) {
    final reason = TextEditingController();
    showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
              title: const Text('예약을 취소할까요?'),
              content: TextField(
                  controller: reason,
                  decoration: const InputDecoration(labelText: '취소 사유 (선택)')),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(dialogContext),
                    child: const Text('닫기')),
                FilledButton(
                    onPressed: () async {
                      if (_isCancelling) return;
                      setState(() => _isCancelling = true);
                      try {
                        await AppointmentsApi(widget.apiClient).cancel(
                            widget.appointment.appointmentId,
                            reason: reason.text);
                        if (dialogContext.mounted) Navigator.pop(dialogContext);
                        if (context.mounted) Navigator.pop(context);
                      } on ApiException catch (error) {
                        if (dialogContext.mounted)
                          ScaffoldMessenger.of(dialogContext).showSnackBar(
                              SnackBar(content: Text(error.message)));
                      } catch (_) {
                        if (dialogContext.mounted)
                          ScaffoldMessenger.of(dialogContext).showSnackBar(
                              const SnackBar(
                                  content: Text('예약 취소를 처리하지 못했습니다.')));
                      } finally {
                        if (mounted) setState(() => _isCancelling = false);
                      }
                    },
                    child: const Text('예약 취소')),
              ],
            ));
  }
}

class _ReservationStartPage extends StatelessWidget {
  const _ReservationStartPage({required this.apiClient, this.onChanged});
  final ApiClient apiClient;
  final VoidCallback? onChanged;
  @override
  Widget build(BuildContext context) => _SlotSelectionPage(
        apiClient: apiClient,
        title: '진료 예약',
        onSubmit: (slotId) => AppointmentsApi(apiClient).create(slotId),
        onChanged: onChanged,
      );
}

class _ReservationChangePage extends StatelessWidget {
  const _ReservationChangePage(
      {required this.apiClient, required this.appointment});
  final ApiClient apiClient;
  final HomeAppointment appointment;
  @override
  Widget build(BuildContext context) => _SlotSelectionPage(
        apiClient: apiClient,
        title: '예약 변경',
        fixedClinicianId: appointment.clinicianId,
        onSubmit: (slotId) => AppointmentsApi(apiClient)
            .reschedule(appointment.appointmentId, slotId),
      );
}

class _SlotSelectionPage extends StatefulWidget {
  const _SlotSelectionPage(
      {required this.apiClient,
      required this.title,
      required this.onSubmit,
      this.fixedClinicianId,
      this.onChanged});
  final ApiClient apiClient;
  final String title;
  final String? fixedClinicianId;
  final Future<void> Function(String slotId) onSubmit;
  final VoidCallback? onChanged;
  @override
  State<_SlotSelectionPage> createState() => _SlotSelectionPageState();
}

class _SlotSelectionPageState extends State<_SlotSelectionPage> {
  late final AppointmentsApi _api = AppointmentsApi(widget.apiClient);
  List<ClinicianOption> _clinicians = const [];
  List<AppointmentSlot> _slots = const [];
  String? _clinicianId;
  String? _selectedSlotId;
  DateTime _date = DateTime.now();
  DateTime _displayedMonth = _monthStart(DateTime.now());
  ReservationStep _step = ReservationStep.date;
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _clinicianId = widget.fixedClinicianId?.isNotEmpty == true
        ? widget.fixedClinicianId
        : null;
    if (_clinicianId == null) {
      _loadClinicians();
    } else {
      _loadSlots();
    }
  }

  Future<void> _loadClinicians() async {
    try {
      final values = await _api.clinicians();
      if (!mounted) return;
      setState(() {
        _clinicians = values;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (mounted)
        setState(() {
          _error = error.message;
          _loading = false;
        });
    } catch (_) {
      if (mounted)
        setState(() {
          _error = '의료진 목록을 불러오지 못했습니다.';
          _loading = false;
        });
    }
  }

  Future<void> _loadSlots() async {
    final clinicianId = _clinicianId;
    if (clinicianId == null || clinicianId.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
      _selectedSlotId = null;
    });
    try {
      final values = await _api.slots(clinicianId, _date);
      if (mounted)
        setState(() {
          _slots = values;
          _loading = false;
        });
    } on ApiException catch (error) {
      if (mounted)
        setState(() {
          _slots = const [];
          _error = error.message;
          _loading = false;
        });
    } catch (_) {
      if (mounted)
        setState(() {
          _slots = const [];
          _error = '예약 가능 시간을 불러오지 못했습니다.';
          _loading = false;
        });
    }
  }

  void _selectDate(DateTime value) {
    setState(() {
      _date = value;
      _selectedSlotId = null;
    });
    if (_clinicianId != null) _loadSlots();
  }

  void _showClinicianStep() {
    setState(() => _step = ReservationStep.clinician);
    if (_clinicianId != null && _slots.isEmpty) _loadSlots();
  }

  ClinicianOption? get _selectedClinician {
    for (final clinician in _clinicians) {
      if (clinician.id == _clinicianId) return clinician;
    }
    return null;
  }

  AppointmentSlot? get _selectedSlot {
    for (final slot in _slots) {
      if (slot.id == _selectedSlotId) return slot;
    }
    return null;
  }

  Future<void> _submit() async {
    final slotId = _selectedSlotId;
    if (slotId == null || _submitting) return;
    setState(() => _submitting = true);
    try {
      await widget.onSubmit(slotId);
      widget.onChanged?.call();
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (error) {
      if (mounted)
        setState(() {
          _error = error.message;
          _submitting = false;
        });
    } catch (_) {
      if (mounted) setState(() => _error = '요청을 처리하지 못했습니다.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title)),
        body: SafeArea(
          top: false,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
            children: [
              _ReservationStepIndicator(step: _step),
              const SizedBox(height: 24),
              if (_step == ReservationStep.date) _buildDateStep(),
              if (_step == ReservationStep.clinician) _buildClinicianStep(),
              if (_step == ReservationStep.confirm) _buildConfirmStep(),
            ],
          ),
        ),
      );

  Widget _buildDateStep() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _ReservationStepTitle(
            title: '예약 날짜를 선택해 주세요.',
            description: '원하는 진료 날짜를 먼저 선택해 주세요.',
          ),
          const SizedBox(height: 18),
          _AppointmentCalendar(
            displayedMonth: _displayedMonth,
            selectedDate: _date,
            appointments: const [],
            firstSelectableDate: _dateOnly(DateTime.now()),
            compact: true,
            onPreviousMonth: () => setState(() {
              final now = _monthStart(DateTime.now());
              final previous =
                  DateTime(_displayedMonth.year, _displayedMonth.month - 1);
              if (!previous.isBefore(now)) _displayedMonth = previous;
            }),
            onNextMonth: () => setState(() {
              _displayedMonth =
                  DateTime(_displayedMonth.year, _displayedMonth.month + 1);
            }),
            onDateSelected: _selectDate,
          ),
          const SizedBox(height: 14),
          _SelectedReservationDateCard(date: _date),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 54,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: _primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16)),
              ),
              onPressed: _showClinicianStep,
              child: const Text('다음'),
            ),
          ),
        ],
      );

  Widget _buildClinicianStep() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _ReservationStepTitle(
            title: '의료진과 시간을 선택해 주세요.',
            description: '선택한 날짜에 예약 가능한 시간을 확인합니다.',
          ),
          const SizedBox(height: 16),
          if (widget.fixedClinicianId == null) ...[
            const Text(
              '의료진 선택',
              style: TextStyle(
                  color: _text, fontSize: 16, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            if (_loading && _clinicians.isEmpty)
              const Center(child: CircularProgressIndicator())
            else if (_error != null && _clinicians.isEmpty)
              _StateCard.error(message: _error!, onRetry: _loadClinicians)
            else
              ..._clinicians.map((clinician) => _ClinicianSelectionCard(
                    clinician: clinician,
                    selected: clinician.id == _clinicianId,
                    onTap: () {
                      if (_clinicianId == clinician.id) return;
                      setState(() => _clinicianId = clinician.id);
                      _loadSlots();
                    },
                  )),
            const SizedBox(height: 18),
          ],
          const Text(
            '예약 가능 시간',
            style: TextStyle(
                color: _text, fontSize: 16, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          if (_clinicianId == null)
            const _StateCard.empty(
              icon: Icons.person_search_outlined,
              title: '의료진을 선택해 주세요.',
              description: '의료진을 선택하면 예약 가능한 시간이 표시됩니다.',
            )
          else if (_loading)
            const Center(
                child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ))
          else if (_error != null)
            _StateCard.error(message: _error!, onRetry: _loadSlots)
          else if (_slots.isEmpty)
            const _StateCard.empty(
              icon: Icons.event_busy_outlined,
              title: '예약 가능한 시간이 없습니다.',
              description: '다른 날짜 또는 의료진을 선택해 주세요.',
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _slots
                  .map((slot) => _SlotTimeButton(
                        label: _formatSlotTime(slot.startAt),
                        selected: _selectedSlotId == slot.id,
                        onTap: () => setState(() => _selectedSlotId = slot.id),
                      ))
                  .toList(),
            ),
          const SizedBox(height: 22),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => setState(() => _step = ReservationStep.date),
                  child: const Text('이전'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton(
                  onPressed: _selectedSlotId == null
                      ? null
                      : () => setState(() => _step = ReservationStep.confirm),
                  child: const Text('예약 정보 확인'),
                ),
              ),
            ],
          ),
        ],
      );

  Widget _buildConfirmStep() {
    final clinician = _selectedClinician;
    final slot = _selectedSlot;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _ReservationStepTitle(
          title: '예약 정보를 확인해 주세요.',
          description: '예약 내용을 확인한 뒤 예약하기를 눌러 주세요.',
        ),
        const SizedBox(height: 18),
        _ReservationConfirmCard(
          date: _date,
          department: clinician?.department ?? '',
          clinicianName: clinician?.name ?? '',
          time: _formatSlotTime(slot?.startAt),
        ),
        const SizedBox(height: 22),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () =>
                    setState(() => _step = ReservationStep.clinician),
                child: const Text('이전'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed:
                    _selectedSlotId == null || _submitting ? null : _submit,
                child: Text(_submitting ? '처리 중...' : '예약하기'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ReservationStepIndicator extends StatelessWidget {
  const _ReservationStepIndicator({required this.step});

  final ReservationStep step;

  @override
  Widget build(BuildContext context) {
    final activeIndex = ReservationStep.values.indexOf(step);
    const labels = ['날짜', '의료진', '확인'];

    return Row(
      children: List.generate(labels.length, (index) {
        final completed = index < activeIndex;
        final active = index == activeIndex;
        return Expanded(
          child: Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color:
                      completed || active ? _primary : const Color(0xFFE9ECF2),
                  shape: BoxShape.circle,
                ),
                child: Center(
                  child: completed
                      ? const Icon(Icons.check_rounded,
                          size: 17, color: Colors.white)
                      : Text(
                          '${index + 1}',
                          style: TextStyle(
                            color: active ? Colors.white : _muted,
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                ),
              ),
              const SizedBox(width: 5),
              Flexible(
                child: Text(
                  labels[index],
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: active || completed ? _primary : _muted,
                    fontSize: 12,
                    fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                  ),
                ),
              ),
              if (index != labels.length - 1)
                const Expanded(
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: 5),
                    child: Divider(color: _border, thickness: 1),
                  ),
                ),
            ],
          ),
        );
      }),
    );
  }
}

class _ReservationStepTitle extends StatelessWidget {
  const _ReservationStepTitle({required this.title, required this.description});

  final String title;
  final String description;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
                color: _text, fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(description, style: const TextStyle(color: _muted, height: 1.4)),
        ],
      );
}

class _ClinicianSelectionCard extends StatelessWidget {
  const _ClinicianSelectionCard({
    required this.clinician,
    required this.selected,
    required this.onTap,
  });

  final ClinicianOption clinician;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Ink(
            padding: const EdgeInsets.all(15),
            decoration: BoxDecoration(
              color: selected ? _soft : Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: selected ? const Color(0xFF8B96E8) : _border),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                      color: _soft, borderRadius: BorderRadius.circular(13)),
                  child: const Icon(Icons.medical_services_outlined,
                      color: _primary),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        clinician.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: _text, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        clinician.department,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: _muted, fontSize: 13),
                      ),
                    ],
                  ),
                ),
                Icon(
                  selected
                      ? Icons.check_circle_rounded
                      : Icons.radio_button_unchecked_rounded,
                  color: selected ? _primary : _muted,
                ),
              ],
            ),
          ),
        ),
      );
}

class _SlotTimeButton extends StatelessWidget {
  const _SlotTimeButton(
      {required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Ink(
          width: 78,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
          decoration: BoxDecoration(
            color: selected ? _soft : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border:
                Border.all(color: selected ? const Color(0xFF8B96E8) : _border),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: selected ? _primary : _text,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      );
}

class _ReservationConfirmCard extends StatelessWidget {
  const _ReservationConfirmCard({
    required this.date,
    required this.department,
    required this.clinicianName,
    required this.time,
  });

  final DateTime date;
  final String department;
  final String clinicianName;
  final String time;

  @override
  Widget build(BuildContext context) {
    final rows = <(String, String)>[
      ('예약 날짜', _formatSelectedDate(date)),
      if (department.isNotEmpty) ('진료과', department),
      if (clinicianName.isNotEmpty) ('의료진', clinicianName),
      ('예약 시간', time),
    ];

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _border),
      ),
      child: Column(
        children: rows
            .map((row) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 74,
                        child:
                            Text(row.$1, style: const TextStyle(color: _muted)),
                      ),
                      Expanded(
                        child: Text(
                          row.$2,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              color: _text, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ),
                ))
            .toList(),
      ),
    );
  }
}

class _SelectedReservationDateCard extends StatelessWidget {
  const _SelectedReservationDateCard({required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: const BoxDecoration(
                  color: Colors.white, shape: BoxShape.circle),
              child: const Icon(Icons.calendar_month_rounded, color: _primary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '선택한 날짜',
                    style: TextStyle(
                        color: _muted,
                        fontSize: 12,
                        fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    _formatSelectedDate(date),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: _text,
                        fontSize: 16,
                        fontWeight: FontWeight.w800),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.title, required this.rows});
  final String title;
  final Map<String, String> rows;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: _border),
            borderRadius: BorderRadius.circular(18)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title,
              style: const TextStyle(
                  color: _text, fontSize: 18, fontWeight: FontWeight.w800)),
          const Divider(height: 28),
          ...rows.entries.map((row) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child:
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(
                    width: 88,
                    child:
                        Text(row.key, style: const TextStyle(color: _muted))),
                Expanded(
                    child: Text(row.value,
                        style: const TextStyle(
                            color: _text, fontWeight: FontWeight.w600))),
              ]))),
        ]),
      );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Row(
        children: [
          Container(
            width: 4,
            height: 20,
            decoration: BoxDecoration(
              color: _primary,
              borderRadius: BorderRadius.circular(99),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            text,
            style: const TextStyle(
              color: _text,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      );
}

class _AppointmentStatusBadge extends StatelessWidget {
  const _AppointmentStatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final colors = switch (status) {
      'REQUESTED' => (const Color(0xFFFFF1DC), const Color(0xFFC07A1D)),
      'CONFIRMED' => (const Color(0xFFE5E8FF), const Color(0xFF5665B8)),
      'COMPLETED' => (const Color(0xFFEAF0FF), const Color(0xFF4F76B9)),
      'CANCELLED' || 'REJECTED' => (
          const Color(0xFFFFE9EC),
          const Color(0xFFC75A6A)
        ),
      _ => (const Color(0xFFF0F2F7), _muted),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: colors.$1,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        _statusLabel(status),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: colors.$2,
          fontSize: 11,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _StateCard extends StatelessWidget {
  const _StateCard.empty(
      {required this.icon, required this.title, required this.description})
      : loading = false,
        message = null,
        onRetry = null;
  const _StateCard.loading()
      : loading = true,
        icon = Icons.hourglass_empty,
        title = '',
        description = '',
        message = null,
        onRetry = null;
  const _StateCard.error({required this.message, required this.onRetry})
      : loading = false,
        icon = Icons.error_outline,
        title = '',
        description = '';
  final bool loading;
  final IconData icon;
  final String title;
  final String description;
  final String? message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.all(20),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
        decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: _border),
            borderRadius: BorderRadius.circular(18)),
        child: loading
            ? const Center(child: CircularProgressIndicator())
            : Column(children: [
                Icon(icon, color: _primary, size: 34),
                const SizedBox(height: 12),
                Text(message ?? title,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        color: _text, fontWeight: FontWeight.w700)),
                if (message == null) ...[
                  const SizedBox(height: 6),
                  Text(description,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: _muted, height: 1.4))
                ],
                if (onRetry != null) ...[
                  const SizedBox(height: 14),
                  OutlinedButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.refresh),
                      label: const Text('다시 시도'))
                ],
              ]),
      );
}

String _formatDate(DateTime value) {
  final month = value.month.toString().padLeft(2, '0');
  final day = value.day.toString().padLeft(2, '0');
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${value.year}.$month.$day  $hour:$minute';
}

DateTime _monthStart(DateTime value) => DateTime(value.year, value.month);

DateTime _dateOnly(DateTime value) =>
    DateTime(value.year, value.month, value.day);

bool _isSameDay(DateTime? left, DateTime? right) =>
    left != null &&
    right != null &&
    left.year == right.year &&
    left.month == right.month &&
    left.day == right.day;

String _formatSelectedDate(DateTime value) {
  const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
  return '${value.year}년 ${value.month}월 ${value.day}일 (${weekdays[value.weekday - 1]})';
}

String _formatSlotTime(DateTime? value) {
  if (value == null) return '-';
  final local = value.toLocal();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

String _formatAppointmentDate(DateTime value) {
  const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
  final month = value.month.toString().padLeft(2, '0');
  final day = value.day.toString().padLeft(2, '0');
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${value.year}.$month.$day (${weekdays[value.weekday - 1]}) $hour:$minute';
}

String _statusLabel(String status) =>
    {
      'REQUESTED': '예약 요청',
      'CONFIRMED': '예약 확정',
      'IN_PROGRESS': '진료 중',
      'COMPLETED': '진료 완료',
      'CANCELLED': '취소',
      'REJECTED': '예약 거절',
    }[status] ??
    (status.isEmpty ? '상태 정보 없음' : status);
