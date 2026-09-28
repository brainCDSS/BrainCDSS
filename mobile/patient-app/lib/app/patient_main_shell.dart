import 'package:flutter/material.dart';

import '../core/api/api_client.dart';
import '../features/appointments/appointments_page.dart';
import '../features/auth/auth_session.dart';
import '../features/assistant/assistant_page.dart';
import '../features/emergency/fast_emergency_page.dart';
import '../features/home/home_page.dart';
import '../features/home/home_api.dart';
import '../features/medications/medications_page.dart';
import '../features/notifications/notifications_page.dart';
import '../features/notifications/notifications_api.dart';
import '../features/policies/patient_policy_center_page.dart';
import '../features/profile/profile_page.dart';
import '../features/test-results/test_results_page.dart';

class PatientMainShell extends StatefulWidget {
  const PatientMainShell({
    super.key,
    required this.apiClient,
    required this.session,
    required this.onLogout,
    required this.onOpenMedicationReminder,
    required this.onOpenAppointmentReminder,
  });

  final ApiClient apiClient;
  final AuthSession session;
  final Future<void> Function() onLogout;
  final Future<void> Function([DateTime? scheduledAt]) onOpenMedicationReminder;
  final Future<void> Function() onOpenAppointmentReminder;

  @override
  State<PatientMainShell> createState() => PatientMainShellState();
}

class PatientMainShellState extends State<PatientMainShell> {
  int _selectedIndex = 2;
  bool _isReservationFlow = false;
  bool _isProfileNotificationSettings = false;
  String? _clinicalHistoryEncounterId;
  final _homeKey = GlobalKey<HomePageState>();
  final _appointmentsKey = GlobalKey<AppointmentsPageState>();
  final _medicationsKey = GlobalKey<MedicationsPageState>();

  late final List<Widget> _pages;
  late final NotificationsApi _notificationsApi =
      NotificationsApi(widget.apiClient);
  int _unreadNotificationCount = 0;

  static const List<String> _titles = [
    '예약',
    '진료내역',
    '호닥',
    '복약관리',
    '마이페이지',
  ];

  @override
  void initState() {
    super.initState();
    notificationRefreshNotifier.addListener(_refreshUnreadNotificationCount);
    _refreshUnreadNotificationCount();

    _pages = [
      AppointmentsPage(
        key: _appointmentsKey,
        apiClient: widget.apiClient,
        onOpenReservation: _openReservation,
      ),
      _testResultsPage(),
      HomePage(
        key: _homeKey,
        apiClient: widget.apiClient,
        session: widget.session,
        onOpenAppointments: () => _selectTab(0),
        onOpenClinicalHistory: () => _selectTab(1),
        onOpenMedications: () => _selectTab(3),
        onOpenAppointmentDetail: _openAppointmentDetail,
        onOpenNotifications: _openNotifications,
      ),
      MedicationsPage(key: _medicationsKey, apiClient: widget.apiClient),
      ProfilePage(
        session: widget.session,
        onLogout: widget.onLogout,
        apiClient: widget.apiClient,
        onOpenNotificationSettings: _openProfileNotificationSettings,
        onOpenChatbot: _openChatbot,
      ),
    ];
  }

  @override
  void dispose() {
    notificationRefreshNotifier.removeListener(_refreshUnreadNotificationCount);
    super.dispose();
  }

  Future<void> _refreshUnreadNotificationCount() async {
    try {
      final response = await _notificationsApi.list();
      if (mounted) {
        setState(() => _unreadNotificationCount = response.unreadCount);
      }
    } catch (_) {
      // Keep the last successfully loaded count when a refresh fails.
    }
  }

  Widget _testResultsPage() => TestResultsPage(
        key: ValueKey(_clinicalHistoryEncounterId),
        apiClient: widget.apiClient,
        selectedEncounterId: _clinicalHistoryEncounterId,
        onOpenDetail: (encounterId) {
          setState(() {
            _clinicalHistoryEncounterId = encounterId;
            _pages[1] = _testResultsPage();
          });
        },
        onCloseDetail: () {
          setState(() {
            _clinicalHistoryEncounterId = null;
            _pages[1] = _testResultsPage();
          });
        },
        onOpenMedications: () => _selectTab(3),
      );

  void _selectTab(int index) {
    if (index == 3) {
      _medicationsKey.currentState?.clearReminderFocus();
    }
    setState(() {
      _selectedIndex = index;
      _isReservationFlow = false;
      _isProfileNotificationSettings = false;
      _clinicalHistoryEncounterId = null;
      _pages[1] = _testResultsPage();
    });
    if (index == 2) {
      _homeKey.currentState?.refreshAppointments();
    }
  }

  void _refreshAppointmentViews() {
    _appointmentsKey.currentState?.reload();
    _homeKey.currentState?.refreshAppointments();
  }

  void _openReservation() {
    setState(() {
      _selectedIndex = 0;
      _isReservationFlow = true;
    });
  }

  void _closeReservation() {
    setState(() => _isReservationFlow = false);
    _refreshAppointmentViews();
  }

  void _openProfileNotificationSettings() {
    setState(() {
      _selectedIndex = 4;
      _isReservationFlow = false;
      _isProfileNotificationSettings = true;
    });
  }

  void _closeProfileNotificationSettings() {
    setState(() => _isProfileNotificationSettings = false);
  }

  Future<void> _openAppointmentDetail(HomeAppointment appointment) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AppointmentDetailPage(
          appointment: appointment,
          apiClient: widget.apiClient,
        ),
      ),
    );
    _refreshAppointmentViews();
  }

  Future<void> _openNotifications() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => NotificationsPage(
          apiClient: widget.apiClient,
          onOpenMedicationReminder: widget.onOpenMedicationReminder,
          onOpenAppointmentReminder: widget.onOpenAppointmentReminder,
        ),
      ),
    );
    _homeKey.currentState?.refreshNotifications();
    await _refreshUnreadNotificationCount();
  }

  void openMedicationReminder([DateTime? scheduledAt]) {
    _selectTab(3);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _medicationsKey.currentState?.reload(focusAt: scheduledAt);
    });
  }

  void openAppointmentReminder() {
    _selectTab(0);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _appointmentsKey.currentState?.reload();
    });
  }

  Future<void> _openChatbot() => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => AssistantPage(
            apiClient: widget.apiClient,
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: _isReservationFlow ||
                _isProfileNotificationSettings ||
                _clinicalHistoryEncounterId != null
            ? IconButton(
                tooltip: '뒤로가기',
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: _isReservationFlow
                    ? _closeReservation
                    : _isProfileNotificationSettings
                        ? _closeProfileNotificationSettings
                        : () {
                            setState(() {
                              _clinicalHistoryEncounterId = null;
                              _pages[1] = _testResultsPage();
                            });
                          },
              )
            : Builder(
                builder: (context) => IconButton(
                  tooltip: '메뉴',
                  icon: const Icon(Icons.menu_rounded),
                  onPressed: () => Scaffold.of(context).openDrawer(),
                ),
              ),
        title: Text(
          _isReservationFlow
              ? '진료 예약'
              : _isProfileNotificationSettings
                  ? '알림 설정'
                  : _clinicalHistoryEncounterId != null
                      ? '진료내역 상세'
                      : _titles[_selectedIndex],
        ),
        actions: [
          if (_isReservationFlow)
            Builder(
              builder: (context) => IconButton(
                tooltip: '메뉴',
                icon: const Icon(Icons.menu_rounded),
                onPressed: () => Scaffold.of(context).openDrawer(),
              ),
            ),
          IconButton(
            onPressed: _openNotifications,
            tooltip: '알림센터',
            icon: _NotificationBellBadge(count: _unreadNotificationCount),
          ),
        ],
      ),
      drawer: _PatientDrawer(
        session: widget.session,
        selectedIndex: _selectedIndex,
        onSelectTab: (index) {
          Navigator.of(context).pop();
          _selectTab(index);
        },
        onOpenPage: (openPage) {
          Navigator.of(context).pop();
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) openPage(context);
          });
        },
        onOpenChatbot: _openChatbot,
        onLogout: widget.onLogout,
      ),
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(
              child: _isReservationFlow
                  ? AppointmentReservationFlow(
                      apiClient: widget.apiClient,
                      embedded: true,
                      onComplete: _closeReservation,
                    )
                  : _isProfileNotificationSettings
                      ? NotificationSettingsContent(apiClient: widget.apiClient)
                      : IndexedStack(
                          index: _selectedIndex,
                          children: _pages,
                        ),
            ),
            if (_selectedIndex != 4)
              Positioned(
                right: 16,
                bottom: 20,
                child: GestureDetector(
                  onTap: _openChatbot,
                  child: const _FloatingHojjangBadge(),
                ),
              ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          _selectTab(index);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(
              Icons.calendar_month_outlined,
            ),
            selectedIcon: Icon(
              Icons.calendar_month,
            ),
            label: '예약',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.description_outlined,
            ),
            selectedIcon: Icon(
              Icons.description,
            ),
            label: '진료내역',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.home_outlined,
            ),
            selectedIcon: Icon(
              Icons.home,
            ),
            label: '홈',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.medication_outlined,
            ),
            selectedIcon: Icon(
              Icons.medication,
            ),
            label: '복약',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.person_outline,
            ),
            selectedIcon: Icon(
              Icons.person,
            ),
            label: '마이페이지',
          ),
        ],
      ),
    );
  }
}

class _NotificationBellBadge extends StatelessWidget {
  const _NotificationBellBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final visible = count > 0;
    final label = count >= 10 ? '9+' : '$count';
    return Stack(
      clipBehavior: Clip.none,
      children: [
        const Icon(Icons.notifications_outlined),
        if (visible)
          Positioned(
            top: -5,
            right: -7,
            child: Container(
              constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
              padding: const EdgeInsets.symmetric(horizontal: 4),
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                color: Color(0xFFE34B4B),
                borderRadius: BorderRadius.all(Radius.circular(10)),
              ),
              child: Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  height: 1,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _FloatingHojjangBadge extends StatelessWidget {
  const _FloatingHojjangBadge();

  @override
  Widget build(BuildContext context) => Image.asset(
        'assets/images/floating.png',
        width: 68,
        height: 68,
        fit: BoxFit.contain,
      );
}

class _PatientDrawer extends StatelessWidget {
  const _PatientDrawer({
    required this.session,
    required this.selectedIndex,
    required this.onSelectTab,
    required this.onOpenPage,
    required this.onOpenChatbot,
    required this.onLogout,
  });

  final AuthSession session;
  final int selectedIndex;
  final ValueChanged<int> onSelectTab;
  final ValueChanged<void Function(BuildContext)> onOpenPage;
  final VoidCallback onOpenChatbot;
  final Future<void> Function() onLogout;

  static const _primaryDark = Color(0xFF5665B8);
  static const _text = Color(0xFF263A5A);
  static const _secondary = Color(0xFF65758D);

  @override
  Widget build(BuildContext context) => Drawer(
        backgroundColor: Colors.white,
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 28, 14, 18),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const CircleAvatar(
                      radius: 28,
                      backgroundColor: Color(0xFFF0F2FF),
                      child: ClipOval(
                        child: Image(
                          image: AssetImage('assets/images/image1.png'),
                          width: 56,
                          height: 56,
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            session.user.name,
                            style: const TextStyle(
                              color: _text,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            session.user.loginId,
                            style: const TextStyle(
                              color: _secondary,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: '닫기',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  children: [
                    _topLevelTile(
                        icon: Icons.home_outlined, title: '홈', index: 2),
                    _topLevelTile(
                      icon: Icons.calendar_month_outlined,
                      title: '예약',
                      index: 0,
                    ),
                    _topLevelTile(
                      icon: Icons.health_and_safety_outlined,
                      title: '진료내역',
                      index: 1,
                    ),
                    _topLevelTile(
                      icon: Icons.medication_outlined,
                      title: '복약관리',
                      index: 3,
                    ),
                    _actionTile(
                      icon: Icons.smart_toy_outlined,
                      title: 'AI 건강도우미',
                      onTap: () {
                        Navigator.of(context).pop();
                        WidgetsBinding.instance.addPostFrameCallback((_) {
                          onOpenChatbot();
                        });
                      },
                    ),
                    _topLevelTile(
                      icon: Icons.person_outline_rounded,
                      title: '마이페이지',
                      index: 4,
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 22, vertical: 2),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
                tileColor: const Color(0xFFFFF1F3),
                leading: const Icon(Icons.emergency_outlined,
                    color: Color(0xFFE94E4E)),
                title: const Text('FAST 응급안내',
                    style: TextStyle(
                        color: Color(0xFFE94E4E), fontWeight: FontWeight.w800)),
                trailing: const Icon(Icons.chevron_right_rounded,
                    color: Color(0xFFE94E4E)),
                onTap: () => onOpenPage(FastEmergencyPage.open),
              ),
              ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 22),
                leading: const Icon(Icons.logout_rounded, color: _secondary),
                title: const Text('로그아웃',
                    style:
                        TextStyle(color: _text, fontWeight: FontWeight.w700)),
                trailing: const Icon(Icons.chevron_right_rounded,
                    color: _secondary, size: 18),
                onTap: () => _confirmLogout(context),
              ),
              InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: () => onOpenPage(PatientPolicyCenterPage.open),
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 22, vertical: 9),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          '약관 및 정책',
                          style: TextStyle(
                            color: _secondary,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Icon(Icons.chevron_right_rounded,
                          color: _secondary, size: 18),
                    ],
                  ),
                ),
              ),
              const Divider(height: 1),
              const SizedBox(height: 8),
            ],
          ),
        ),
      );

  Widget _topLevelTile(
          {required IconData icon,
          required String title,
          required int index}) =>
      ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 1),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        selected: selectedIndex == index,
        selectedTileColor: const Color(0xFFF0F2FF),
        selectedColor: _primaryDark,
        leading: Icon(icon),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        trailing: const Icon(Icons.chevron_right_rounded, color: _secondary),
        onTap: () => onSelectTab(index),
      );

  Widget _actionTile({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 1),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          leading: Icon(icon, color: _secondary),
          title: Text(title,
              style:
                  const TextStyle(color: _text, fontWeight: FontWeight.w700)),
          trailing: const Icon(Icons.chevron_right_rounded, color: _secondary),
          onTap: onTap,
        ),
      );

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('로그아웃할까요?'),
        content: const Text('로그인 화면으로 이동합니다.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('취소')),
          FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('로그아웃')),
        ],
      ),
    );
    if (confirmed == true) await onLogout();
  }
}
