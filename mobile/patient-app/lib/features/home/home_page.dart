import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/hospital_time.dart';
import '../auth/auth_session.dart';
import '../medications/patient_prescriptions_api.dart';
import '../notifications/notifications_api.dart';
import '../test-results/test_results_api.dart';
import 'home_api.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.apiClient,
    required this.session,
    required this.onOpenAppointments,
    required this.onOpenAppointmentDetail,
    required this.onOpenNotifications,
  });

  final ApiClient apiClient;
  final AuthSession session;
  final VoidCallback onOpenAppointments;
  final ValueChanged<HomeAppointment> onOpenAppointmentDetail;
  final VoidCallback onOpenNotifications;

  @override
  State<HomePage> createState() => HomePageState();
}

class HomePageState extends State<HomePage> {
  static const Color _surface = Color(0xFFFFFFFF);
  static const Color _border = Color(0xFFCFD7E8);
  static const Color _textPrimary = Color(0xFF263A5A);
  static const Color _textSecondary = Color(0xFF65758D);

  late final HomeApi _homeApi;
  late final NotificationsApi _notificationsApi;
  late final MedicationSchedulesApi _medicationSchedulesApi;
  late final TestResultsApi _testResultsApi;

  bool _isLoadingAppointments = true;
  String? _appointmentError;

  List<HomeAppointment> _appointments = const [];
  List<MedicationScheduleSummary> _todaySchedules = const [];
  List<TestResultSummary> _testResults = const [];
  bool _showTodaySchedule = true;
  int _healthTipPage = 0;
  final PageController _healthTipController = PageController();
  Timer? _healthTipTimer;

  @override
  void initState() {
    super.initState();

    _homeApi = HomeApi(
      widget.apiClient,
    );
    _notificationsApi = NotificationsApi(widget.apiClient);
    _medicationSchedulesApi = MedicationSchedulesApi(widget.apiClient);
    _testResultsApi = TestResultsApi(widget.apiClient);

    _loadAppointments();
    _loadNotifications();
    _loadHomeSummaries();
    _startHealthTipAutoSlide();
  }

  void _startHealthTipAutoSlide() {
    _healthTipTimer?.cancel();
    _healthTipTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) {
        if (!mounted || !_healthTipController.hasClients) {
          return;
        }

        const pageCount = 3;
        final nextPage = (_healthTipPage + 1) % pageCount;

        _healthTipController.animateToPage(
          nextPage,
          duration: const Duration(milliseconds: 420),
          curve: Curves.easeInOut,
        );
      },
    );
  }

  @override
  void dispose() {
    _healthTipTimer?.cancel();
    _healthTipController.dispose();
    super.dispose();
  }

  Future<void> _loadHomeSummaries() async {
    final results = await Future.wait([
      _medicationSchedulesApi
          .listForDate(DateTime.now())
          .catchError((_) => <MedicationScheduleSummary>[]),
      _testResultsApi.list().catchError((_) => <TestResultSummary>[]),
    ]);
    if (!mounted) {
      return;
    }
    setState(() {
      _todaySchedules = results[0] as List<MedicationScheduleSummary>;
      _testResults = results[1] as List<TestResultSummary>;
    });
  }

  Future<void> _loadNotifications() async {
    try {
      await _notificationsApi.list(unreadOnly: true);
    } catch (_) {}
  }

  Future<void> _loadAppointments() async {
    setState(() {
      _isLoadingAppointments = true;
      _appointmentError = null;
    });

    try {
      final appointments = await _homeApi.getMyAppointments();

      if (!mounted) {
        return;
      }

      setState(() {
        _appointments = appointments;
        _isLoadingAppointments = false;
      });
    } on ApiException {
      if (!mounted) {
        return;
      }

      setState(() {
        _appointmentError = '예약 정보를 불러오지 못했습니다.';
        _isLoadingAppointments = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _appointmentError = '예약 정보를 불러오지 못했습니다.';
        _isLoadingAppointments = false;
      });
    }
  }

  Future<void> refreshAppointments() => _loadAppointments();

  Future<void> refreshNotifications() => _loadNotifications();

  List<HomeAppointment> get _todayAppointments {
    final now = DateTime.now();

    final appointments = _appointments.where(
      (appointment) {
        final scheduledAt = hospitalTime(appointment.scheduledAt);

        if (scheduledAt == null) {
          return false;
        }

        return scheduledAt.year == now.year &&
            scheduledAt.month == now.month &&
            scheduledAt.day == now.day;
      },
    ).toList();

    appointments.sort(
      (a, b) {
        final aTime = a.scheduledAt;
        final bTime = b.scheduledAt;

        if (aTime == null && bTime == null) {
          return 0;
        }

        if (aTime == null) {
          return 1;
        }

        if (bTime == null) {
          return -1;
        }

        return aTime.compareTo(bTime);
      },
    );

    return appointments;
  }

  String get _patientName {
    final name = widget.session.user.name.trim();

    if (name.isEmpty) {
      return '';
    }

    return name;
  }

  @override
  Widget build(BuildContext context) {
    final today = _todayAppointments;
    final upcoming = _appointments
        .where(
          (item) =>
              item.scheduledAt?.isAfter(DateTime.now().toUtc()) ?? false,
        )
        .toList()
      ..sort((a, b) => a.scheduledAt!.compareTo(b.scheduledAt!));
    final appointments = _showTodaySchedule ? today : upcoming.take(1).toList();

    return RefreshIndicator(
      onRefresh: () async {
        await Future.wait([
          _loadAppointments(),
          _loadNotifications(),
          _loadHomeSummaries(),
        ]);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          _buildGreeting(),
          const SizedBox(height: 16),
          _buildScheduleTabs(),
          const SizedBox(height: 14),
          _buildScheduleHeading(),
          const SizedBox(height: 10),
          _buildAppointmentSection(appointments),
          const SizedBox(height: 14),
          _buildTodayMedicationCard(),
          const SizedBox(height: 22),
          _buildHomeHealthSummary(todayAppointmentCount: today.length),
          const SizedBox(height: 18),
          _buildHealthTip(),
        ],
      ),
    );
  }

  Widget _buildScheduleTabs() => Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
            color: const Color(0xFFEFF1FF),
            borderRadius: BorderRadius.circular(24)),
        child: Row(children: [
          _scheduleTab('오늘 일정', _showTodaySchedule),
          _scheduleTab('다음 진료', !_showTodaySchedule),
        ]),
      );

  Widget _scheduleTab(String label, bool selected) => Expanded(
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            onTap: () => setState(() => _showTodaySchedule = label == '오늘 일정'),
            borderRadius: BorderRadius.circular(21),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                  color:
                      selected ? const Color(0xFF5665B8) : Colors.transparent,
                  borderRadius: BorderRadius.circular(21)),
              child:
                  Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(Icons.calendar_month_outlined,
                    size: 19, color: selected ? Colors.white : _textSecondary),
                const SizedBox(width: 7),
                Text(label,
                    style: TextStyle(
                        color: selected ? Colors.white : _textSecondary,
                        fontWeight: FontWeight.w800)),
              ]),
            ),
          ),
        ),
      );

  Widget _buildScheduleHeading() => Text(
        _showTodaySchedule ? '오늘의 진료 일정' : '다음 진료',
        style: const TextStyle(
            color: _textPrimary, fontSize: 20, fontWeight: FontWeight.w800),
      );

  Widget _buildHomeHealthSummary({required int todayAppointmentCount}) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('건강 요약',
              style: TextStyle(
                  color: _textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
                child: _HomeSummaryTile(
                    icon: Icons.calendar_month_outlined,
                    label: '예약',
                    value: todayAppointmentCount == 0
                        ? '오늘 없음'
                        : '$todayAppointmentCount건',
                    color: const Color(0xFFE8EBFF))),
            const SizedBox(width: 9),
            Expanded(
                child: _HomeSummaryTile(
                    icon: Icons.medication_outlined,
                    label: '복약',
                    value: _todaySchedules.isEmpty
                        ? '오늘 없음'
                        : '${_todaySchedules.length}건',
                    color: const Color(0xFFF0F1FF))),
            const SizedBox(width: 9),
            Expanded(
                child: _HomeSummaryTile(
                    icon: Icons.assignment_outlined,
                    label: '검사·결과',
                    value: _testResults.isEmpty
                        ? '새 결과 없음'
                        : '${_testResults.length}건',
                    color: const Color(0xFFEDE8FF))),
          ]),
        ],
      );

  Widget _buildTodayMedicationCard() {
    final schedule = _todaySchedules.isEmpty ? null : _todaySchedules.first;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _cardDecoration(),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.medication_outlined,
              color: Color(0xFFF5F6FD), size: 25),
          const SizedBox(width: 9),
          const Expanded(
              child: Text('오늘 복약',
                  style: TextStyle(
                      color: _textPrimary,
                      fontSize: 19,
                      fontWeight: FontWeight.w800))),
          Text(
              _todaySchedules.isEmpty
                  ? '일정 없음'
                  : '오늘 ${_todaySchedules.length}건',
              style: const TextStyle(color: _textSecondary, fontSize: 12)),
        ]),
        const SizedBox(height: 14),
        if (schedule == null)
          const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('오늘 복약할 약이 없습니다.',
                style: TextStyle(
                    color: _textPrimary, fontWeight: FontWeight.w700)),
            SizedBox(height: 4),
            Text('등록된 복약 일정이 없어요.',
                style: TextStyle(color: _textSecondary, fontSize: 13)),
          ])
        else
          Row(children: [
            Container(
                width: 46,
                height: 46,
                decoration: const BoxDecoration(
                    color: Color(0xFFE5F5F5), shape: BoxShape.circle),
                child: const Icon(Icons.medication_outlined,
                    color: Color.fromARGB(255, 172, 196, 241))),
            const SizedBox(width: 12),
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
                          color: _textPrimary, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(_homeScheduleTime(schedule),
                      style:
                          const TextStyle(color: _textSecondary, fontSize: 13)),
                ])),
            if (schedule.status?.trim().isNotEmpty == true)
              Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(
                      color: const Color(0xFFE5F5F5),
                      borderRadius: BorderRadius.circular(16)),
                  child: Text(schedule.status!,
                      style: const TextStyle(
                          color: Color(0xFFF5F5FF),
                          fontSize: 12,
                          fontWeight: FontWeight.w700))),
          ]),
      ]),
    );
  }

  Widget _buildHealthTip() {
    const tips = <Map<String, dynamic>>[
      {
        'title': '충분한 수분 섭취가 건강의 작은 시작이에요.',
        'description': '하루 6~8잔의 물로, 더 가벼운 하루를 만들어보세요!',
        'icon': Icons.water_drop_rounded,
        'iconColor': Color(0xFF35B7D5),
      },
      {
        'title': '가벼운 스트레칭으로 하루를 시작해보세요.',
        'description': '잠깐의 움직임도 몸에 활력을 더해줄 수 있어요.',
        'icon': Icons.self_improvement_rounded,
        'iconColor': Color(0xFF8B96E8),
      },
      {
        'title': '규칙적인 휴식도 건강 관리의 한 부분이에요.',
        'description': '바쁜 하루에도 잠시 숨을 고르는 시간을 가져보세요.',
        'icon': Icons.nightlight_round,
        'iconColor': Color(0xFF7C8BB8),
      },
    ];

    final todayIndex = DateTime.now().day % tips.length;
    final orderedTips = [
      tips[todayIndex],
      ...List.generate(
        tips.length - 1,
        (index) => tips[(todayIndex + index + 1) % tips.length],
      ),
    ];

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF0F1FF),
        borderRadius: BorderRadius.circular(22),
      ),
      child: SizedBox(
        height: 154,
        child: Stack(
          children: [
            PageView.builder(
              controller: _healthTipController,
              itemCount: orderedTips.length,
              onPageChanged: (index) {
                setState(() => _healthTipPage = index);
              },
              itemBuilder: (context, index) {
                final tip = orderedTips[index];

                return Padding(
                  padding: const EdgeInsets.fromLTRB(18, 14, 18, 18),
                  child: Stack(
                    children: [
                      Positioned.fill(
                        right: 54,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              '오늘의 건강 한마디',
                              style: TextStyle(
                                color: Color(0xFF8B96E8),
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              tip['title'] as String,
                              style: const TextStyle(
                                color: _textPrimary,
                                fontSize: 16, //하단 배너 큰글씨
                                height: 1.35, //하단 배너 작은글씨(설명)
                                fontWeight: FontWeight.w800,
                                letterSpacing: -0.5,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              tip['description'] as String,
                              style: const TextStyle(
                                color: _textSecondary,
                                fontSize: 12,
                                height: 1.45,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Positioned(
                        right: 2,
                        top: 40,
                        child: Icon(
                          tip['icon'] as IconData,
                          color: tip['iconColor'] as Color,
                          size: 42,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
            Positioned(
              bottom: 8,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(
                  orderedTips.length,
                  (index) => Container(
                    width: index == _healthTipPage ? 14 : 5,
                    height: 5,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      color: index == _healthTipPage
                          ? const Color(0xFF8B96E8)
                          : const Color(0xFFD0D4ED),
                      borderRadius: BorderRadius.circular(99),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

/*상단 인사말 카드섹션*/
  Widget _buildGreeting() {
    return Container(
      height: 164,
      padding: const EdgeInsets.fromLTRB(18, 18, 10, 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF0F1FF),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Stack(
        children: [
          Positioned.fill(
            right: 112,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _patientName.isEmpty
                        ? '오늘도 건강한 하루 되세요!'
                        : '$_patientName님,\n오늘도 건강한 하루 되세요!',
                    maxLines: 2,
                    overflow: TextOverflow.visible,
                    style: const TextStyle(
                      color: _textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      height: 1.25,
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    '호짱이 함께할게요.',
                    style: TextStyle(
                      color: _textSecondary,
                      fontSize: 14,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            right: 0,
            bottom: 0,
            child: Image.asset(
              'assets/images/hojjang_main.png',
              width: 118,
              height: 128,
              fit: BoxFit.contain,
              alignment: Alignment.bottomCenter,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppointmentSection(
    List<HomeAppointment> appointments,
  ) {
    if (_isLoadingAppointments) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: _cardDecoration(),
        child: const Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_appointmentError != null) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: _cardDecoration(),
        child: Column(
          children: [
            const Icon(
              Icons.error_outline_rounded,
              color: _textSecondary,
              size: 32,
            ),
            const SizedBox(height: 12),
            Text(
              _appointmentError!,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: _textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: _loadAppointments,
              icon: const Icon(
                Icons.refresh_rounded,
              ),
              label: const Text(
                '다시 시도',
              ),
            ),
          ],
        ),
      );
    }

    if (appointments.isEmpty) {
      return const _EmptyCard(
        icon: Icons.event_available_outlined,
        title: '오늘 예약 일정이 없습니다.',
        description: '예약된 진료가 있으면 이곳에 표시됩니다.',
      );
    }

    return Column(
      children: appointments
          .map(
            (appointment) => Padding(
              padding: const EdgeInsets.only(
                bottom: 10,
              ),
              child: _AppointmentCard(
                appointment: appointment,
                onTap: () => widget.onOpenAppointmentDetail(appointment),
              ),
            ),
          )
          .toList(),
    );
  }

  BoxDecoration _cardDecoration() {
    return BoxDecoration(
      color: _surface,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(
        color: _border,
      ),
    );
  }
}

class _HomeSummaryTile extends StatelessWidget {
  const _HomeSummaryTile(
      {required this.icon,
      required this.label,
      required this.value,
      required this.color});

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        height: 112,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: color),
            borderRadius: BorderRadius.circular(18)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                  color: color, borderRadius: BorderRadius.circular(11)),
              child: Icon(icon, color: const Color(0xFF5665B8), size: 19)),
          const Spacer(),
          Text(label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Color(0xFF65758D), fontSize: 11)),
          const SizedBox(height: 3),
          Text(value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                  color: Color(0XFF263A5A),
                  fontSize: 13,
                  fontWeight: FontWeight.w800)),
        ]),
      );
}

class _AppointmentCard extends StatelessWidget {
  const _AppointmentCard({
    required this.appointment,
    required this.onTap,
  });

  final HomeAppointment appointment;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheduledAt = hospitalTime(appointment.scheduledAt);

    final info = <String>[
      if (appointment.hospitalName.isNotEmpty) appointment.hospitalName,
      if (appointment.departmentName.isNotEmpty) appointment.departmentName,
      if (appointment.clinicianName.isNotEmpty) appointment.clinicianName,
    ];

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Ink(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFFFFFFFF),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: const Color(0xFFCFD7E8),
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: const Color(0xFFE5E8FF),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.calendar_today_outlined,
                color: Color(0xFF5665B8),
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
                          scheduledAt == null
                              ? '예약 시간 정보 없음'
                              : _formatTime(
                                  scheduledAt,
                                ),
                          style: const TextStyle(
                            color: Color(
                              0xFF263A5A,
                            ),
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      const SizedBox(
                        width: 8,
                      ),
                      _StatusBadge(
                        status: appointment.status,
                      ),
                    ],
                  ),
                  if (info.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      info.join(' · '),
                      style: const TextStyle(
                        color: Color(
                          0xFF65758D,
                        ),
                        fontSize: 13,
                        height: 1.4,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _formatTime(
    DateTime dateTime,
  ) {
    final hour = dateTime.hour.toString().padLeft(2, '0');

    final minute = dateTime.minute.toString().padLeft(2, '0');

    return '$hour:$minute';
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.status,
  });

  final String status;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 10,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFE5E8FF),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        _statusLabel(status),
        style: const TextStyle(
          color: Color(0xFF5665B8),
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  static String _statusLabel(
    String status,
  ) {
    switch (status) {
      case 'REQUESTED':
        return '예약 요청';
      case 'CONFIRMED':
        return '예약 확정';
      case 'IN_PROGRESS':
        return '진료 중';
      case 'COMPLETED':
        return '진료 완료';
      case 'CANCELLED':
        return '취소';
      case 'REJECTED':
        return '예약 거절';
      default:
        return status.isEmpty ? '상태 정보 없음' : status;
    }
  }
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: 20,
        vertical: 24,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFFFF),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFCFD7E8),
        ),
      ),
      child: Column(
        children: [
          Icon(
            icon,
            size: 32,
            color: const Color(0xFF8B96E8),
          ),
          const SizedBox(height: 12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF263A5A),
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            description,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF65758D),
              fontSize: 13,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

String _homeScheduleTime(MedicationScheduleSummary schedule) {
  final scheduledAt = schedule.scheduledAt;
  if (scheduledAt == null) {
    return schedule.timeSlot?.trim().isNotEmpty == true
        ? schedule.timeSlot!.trim()
        : '-';
  }
  final time =
      '${scheduledAt.hour.toString().padLeft(2, '0')}:${scheduledAt.minute.toString().padLeft(2, '0')}';
  final slot = schedule.timeSlot?.trim();
  return slot == null || slot.isEmpty ? time : '$time · $slot';
}
