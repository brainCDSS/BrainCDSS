import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../auth/auth_session.dart';
import '../emergency/fast_emergency_page.dart';
import '../notifications/notifications_api.dart';
import 'home_api.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.apiClient,
    required this.session,
  });

  final ApiClient apiClient;
  final AuthSession session;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const Color _primary = Color(0xFF8B96E8);
  static const Color _primaryDark = Color(0xFF5665B8);
  static const Color _primarySoft = Color(0xFFE5E8FF);
  static const Color _surface = Color(0xFFFFFFFF);
  static const Color _border = Color(0xFFCFD7E8);
  static const Color _textPrimary = Color(0xFF263A5A);
  static const Color _textSecondary = Color(0xFF65758D);
  static const Color _emergency = Color(0xFFE94E4E);

  late final HomeApi _homeApi;
  late final NotificationsApi _notificationsApi;

  bool _isLoadingAppointments = true;
  String? _appointmentError;

  List<HomeAppointment> _appointments = const [];
  List<PatientNotification> _notifications = const [];

  @override
  void initState() {
    super.initState();

    _homeApi = HomeApi(
      widget.apiClient,
    );
    _notificationsApi = NotificationsApi(widget.apiClient);

    _loadAppointments();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    try {
      final response = await _notificationsApi.list(unreadOnly: true);
      if (mounted) setState(() => _notifications = response.items.where((item) => !item.isRead).toList());
    } catch (_) {
      if (mounted) setState(() => _notifications = const []);
    }
  }

  Future<void> _loadAppointments() async {
    setState(() {
      _isLoadingAppointments = true;
      _appointmentError = null;
    });

    try {
      final appointments = await _homeApi.getMyAppointments();

      if (!mounted) return;

      setState(() {
        _appointments = appointments;
        _isLoadingAppointments = false;
      });
    } on ApiException {
      if (!mounted) return;

      setState(() {
        _appointmentError = '예약 정보를 불러오지 못했습니다.';
        _isLoadingAppointments = false;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _appointmentError = '예약 정보를 불러오지 못했습니다.';
        _isLoadingAppointments = false;
      });
    }
  }

  List<HomeAppointment> get _todayAppointments {
    final now = DateTime.now();

    final appointments = _appointments.where(
      (appointment) {
        final scheduledAt = appointment.scheduledAt?.toLocal();

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
    final todayAppointments = _todayAppointments;

    return RefreshIndicator(
      onRefresh: () async { await Future.wait([_loadAppointments(), _loadNotifications()]); },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(
          20,
          20,
          20,
          32,
        ),
        children: [
          _buildGreeting(),
          const SizedBox(height: 28),
          _buildSectionTitle(
            title: '건강 요약',
            subtitle: '오늘 확인할 건강 정보를 한눈에 확인하세요.',
          ),
          const SizedBox(height: 12),
          _buildHealthSummary(
            todayAppointmentCount: todayAppointments.length,
          ),
          const SizedBox(height: 28),
          _buildSectionTitle(
            title: '오늘 일정',
            subtitle: '오늘 예정된 진료 일정을 확인하세요.',
          ),
          const SizedBox(height: 12),
          _buildAppointmentSection(
            todayAppointments,
          ),
          const SizedBox(height: 28),
          _buildSectionTitle(
            title: '주요 알림',
            subtitle: '확인이 필요한 알림을 확인하세요.',
          ),
          const SizedBox(height: 12),
          if (_notifications.isEmpty) const _EmptyCard(
            icon: Icons.notifications_none_rounded,
            title: '확인할 알림이 없습니다.',
            description: '새로운 알림이 등록되면 이곳에 표시됩니다.',
          ) else ..._notifications.take(3).map((item) => Card(child: ListTile(
            leading: Icon(Icons.notifications_active_outlined, color: item.severity == 'CRITICAL' ? _emergency : _primaryDark),
            title: Text(item.title), subtitle: Text(item.body),
            onTap: () async { await _notificationsApi.markRead(item.id); await _loadNotifications(); },
          ))),
          const SizedBox(height: 28),
          _buildSectionTitle(
            title: '오늘 복약',
            subtitle: '오늘의 복약 일정을 확인하세요.',
          ),
          const SizedBox(height: 12),
          const _EmptyCard(
            icon: Icons.medication_outlined,
            title: '복약 정보가 없습니다.',
            description: '복약 일정이 등록되면 이곳에 표시됩니다.',
          ),
          const SizedBox(height: 28),
          _buildEmergencySection(),
        ],
      ),
    );
  }

  Widget _buildGreeting() {
    final greeting = _patientName.isEmpty ? '안녕하세요' : '$_patientName님, 안녕하세요';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _primarySoft,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: _surface,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(
              Icons.favorite_outline_rounded,
              color: _primaryDark,
              size: 28,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  greeting,
                  style: const TextStyle(
                    color: _textPrimary,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  '오늘도 건강 정보를 확인해 보세요.',
                  style: TextStyle(
                    color: _textSecondary,
                    fontSize: 14,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle({
    required String title,
    required String subtitle,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: _textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: const TextStyle(
            color: _textSecondary,
            fontSize: 13,
          ),
        ),
      ],
    );
  }

  Widget _buildHealthSummary({
    required int todayAppointmentCount,
  }) {
    return Row(
      children: [
        Expanded(
          child: _SummaryCard(
            icon: Icons.calendar_month_outlined,
            label: '예약',
            value: _isLoadingAppointments
                ? '확인 중'
                : _appointmentError != null
                    ? '확인 필요'
                    : todayAppointmentCount == 0
                        ? '오늘 없음'
                        : '오늘 $todayAppointmentCount건',
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(
          child: _SummaryCard(
            icon: Icons.medication_outlined,
            label: '복약',
            value: '정보 없음',
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(
          child: _SummaryCard(
            icon: Icons.assignment_outlined,
            label: '검사 결과',
            value: '정보 없음',
          ),
        ),
      ],
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
              ),
            ),
          )
          .toList(),
    );
  }

  Widget _buildEmergencySection() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: _border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '응급 상황',
            style: TextStyle(
              color: _textPrimary,
              fontSize: 17,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            '뇌졸중 의심 증상이 있다면 신속하게 대응하세요.',
            style: TextStyle(
              color: _textSecondary,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => FastEmergencyPage.open(context),
                  icon: const Icon(
                    Icons.health_and_safety_outlined,
                  ),
                  label: const Padding(
                    padding: EdgeInsets.symmetric(
                      vertical: 14,
                    ),
                    child: Text(
                      'FAST 안내',
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: _emergency,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () {
                    ScaffoldMessenger.of(
                      context,
                    ).showSnackBar(
                      const SnackBar(
                        content: Text(
                          '119 전화 연결 기능은 연결 예정입니다.',
                        ),
                      ),
                    );
                  },
                  icon: const Icon(
                    Icons.call_outlined,
                  ),
                  label: const Padding(
                    padding: EdgeInsets.symmetric(
                      vertical: 14,
                    ),
                    child: Text(
                      '119 연락',
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
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

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(
        minHeight: 120,
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: 12,
        vertical: 16,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFFFF),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFCFD7E8),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFFE5E8FF),
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(
              icon,
              size: 20,
              color: const Color(0xFF5665B8),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF65758D),
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Color(0xFF263A5A),
              fontSize: 14,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _AppointmentCard extends StatelessWidget {
  const _AppointmentCard({
    required this.appointment,
  });

  final HomeAppointment appointment;

  @override
  Widget build(BuildContext context) {
    final scheduledAt = appointment.scheduledAt?.toLocal();

    final info = <String>[
      if (appointment.hospitalName.isNotEmpty) appointment.hospitalName,
      if (appointment.departmentName.isNotEmpty) appointment.departmentName,
      if (appointment.clinicianName.isNotEmpty) appointment.clinicianName,
    ];

    return Container(
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
