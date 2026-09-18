import 'package:flutter/material.dart';

import '../core/api/api_client.dart';
import '../features/appointments/appointments_page.dart';
import '../features/auth/auth_session.dart';
import '../features/emergency/fast_emergency_page.dart';
import '../features/home/home_page.dart';
import '../features/home/home_api.dart';
import '../features/medications/medications_page.dart';
import '../features/notifications/notifications_page.dart';
import '../features/profile/profile_page.dart';
import '../features/test-results/test_results_page.dart';

class PatientMainShell extends StatefulWidget {
  const PatientMainShell({
    super.key,
    required this.apiClient,
    required this.session,
    required this.onLogout,
  });

  final ApiClient apiClient;
  final AuthSession session;
  final Future<void> Function() onLogout;

  @override
  State<PatientMainShell> createState() => _PatientMainShellState();
}

class _PatientMainShellState extends State<PatientMainShell> {
  int _selectedIndex = 0;
  bool _isReservationFlow = false;
  bool _isProfileNotificationSettings = false;
  final _homeKey = GlobalKey<HomePageState>();
  final _appointmentsKey = GlobalKey<AppointmentsPageState>();

  late final List<Widget> _pages;

  static const List<String> _titles = [
    '호닥',
    '예약',
    '검사 · 결과',
    '복약관리',
    '마이페이지',
  ];

  @override
  void initState() {
    super.initState();

    _pages = [
      HomePage(
        key: _homeKey,
        apiClient: widget.apiClient,
        session: widget.session,
        onOpenAppointments: () => _selectTab(1),
        onOpenAppointmentDetail: _openAppointmentDetail,
        onOpenNotifications: _openNotifications,
      ),
      AppointmentsPage(
        key: _appointmentsKey,
        apiClient: widget.apiClient,
        onOpenReservation: _openReservation,
      ),
      TestResultsPage(apiClient: widget.apiClient),
      MedicationsPage(apiClient: widget.apiClient),
      ProfilePage(
        session: widget.session,
        onLogout: widget.onLogout,
        apiClient: widget.apiClient,
        onOpenNotificationSettings: _openProfileNotificationSettings,
      ),
    ];
  }

  void _selectTab(int index) {
    setState(() {
      _selectedIndex = index;
      _isReservationFlow = false;
      _isProfileNotificationSettings = false;
    });
    if (index == 0) {
      _homeKey.currentState?.refreshAppointments();
    }
  }

  void _refreshAppointmentViews() {
    _appointmentsKey.currentState?.reload();
    _homeKey.currentState?.refreshAppointments();
  }

  void _openReservation() {
    setState(() {
      _selectedIndex = 1;
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
        builder: (_) => NotificationsPage(apiClient: widget.apiClient),
      ),
    );
    _homeKey.currentState?.refreshNotifications();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: _isReservationFlow || _isProfileNotificationSettings
            ? IconButton(
                tooltip: '뒤로가기',
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: _isReservationFlow
                    ? _closeReservation
                    : _closeProfileNotificationSettings,
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
                  : _titles[_selectedIndex],
        ),
        actions: _isReservationFlow
            ? [
                Builder(
                  builder: (context) => IconButton(
                    tooltip: '메뉴',
                    icon: const Icon(Icons.menu_rounded),
                    onPressed: () => Scaffold.of(context).openDrawer(),
                  ),
                ),
              ]
            : _selectedIndex == 0
                ? [
                    IconButton(
                      onPressed: _openNotifications,
                      tooltip: '알림센터',
                      icon: const Icon(
                        Icons.notifications_outlined,
                      ),
                    ),
                  ]
                : null,
      ),
      drawer: _PatientDrawer(
        apiClient: widget.apiClient,
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
        onOpenReservation: () {
          Navigator.of(context).pop();
          _openReservation();
        },
        onShowAppointmentSection: (showPast) {
          Navigator.of(context).pop();
          _selectTab(1);
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (showPast) {
              _appointmentsKey.currentState?.showPast();
            } else {
              _appointmentsKey.currentState?.showUpcoming();
            }
          });
        },
        onAppointmentsChanged: _refreshAppointmentViews,
        onOpenProfileNotificationSettings: () {
          Navigator.of(context).pop();
          _openProfileNotificationSettings();
        },
        onLogout: widget.onLogout,
      ),
      body: SafeArea(
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
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          _selectTab(index);
        },
        destinations: const [
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
              Icons.calendar_month_outlined,
            ),
            selectedIcon: Icon(
              Icons.calendar_month,
            ),
            label: '예약',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.assignment_outlined,
            ),
            selectedIcon: Icon(
              Icons.assignment,
            ),
            label: '검사 · 결과',
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

class _PatientDrawer extends StatelessWidget {
  const _PatientDrawer({
    required this.apiClient,
    required this.session,
    required this.selectedIndex,
    required this.onSelectTab,
    required this.onOpenPage,
    required this.onOpenReservation,
    required this.onShowAppointmentSection,
    required this.onAppointmentsChanged,
    required this.onOpenProfileNotificationSettings,
    required this.onLogout,
  });

  final AuthSession session;
  final ApiClient apiClient;
  final int selectedIndex;
  final ValueChanged<int> onSelectTab;
  final ValueChanged<void Function(BuildContext)> onOpenPage;
  final VoidCallback onOpenReservation;
  final ValueChanged<bool> onShowAppointmentSection;
  final VoidCallback onAppointmentsChanged;
  final VoidCallback onOpenProfileNotificationSettings;
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
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                child: Container(
                  padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0F2FF),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const CircleAvatar(
                      radius: 22,
                      backgroundColor: Colors.white,
                      child: ClipOval(
                        child: Image(
                          image: AssetImage('assets/images/image1.png'),
                          width: 44,
                          height: 44,
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('호닥',
                              style: TextStyle(
                                  color: _text,
                                  fontSize: 19,
                                  fontWeight: FontWeight.w900)),
                          const SizedBox(height: 6),
                          Text(session.user.name,
                              style: const TextStyle(
                                  color: _text, fontWeight: FontWeight.w800)),
                          const SizedBox(height: 2),
                          Text(session.user.loginId,
                              style: const TextStyle(
                                  color: _secondary, fontSize: 12)),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: '닫기',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                )),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  children: [
                    _topLevelTile(
                        icon: Icons.home_outlined, title: '홈', index: 0),
                    _section(
                      icon: Icons.calendar_month_outlined,
                      title: '예약',
                      index: 1,
                      children: [
                        _subTile('진료 예약하기', onOpenReservation),
                        _subTile(
                            '예정된 예약', () => onShowAppointmentSection(false)),
                        _subTile('지난 예약', () => onShowAppointmentSection(true)),
                      ],
                    ),
                    _section(
                      icon: Icons.health_and_safety_outlined,
                      title: '건강정보',
                      index: 2,
                      children: [
                        _subTile(
                            '검사 결과',
                            () => onOpenPage((context) =>
                                TestResultsPage.openResults(
                                    context, apiClient))),
                        _subTile('진료 내역',
                            () => onOpenPage(TestResultsPage.openVisits)),
                        _subTile(
                            '처방 정보',
                            () => onOpenPage((context) =>
                                TestResultsPage.openPrescriptions(
                                    context, apiClient))),
                      ],
                    ),
                    _section(
                      icon: Icons.medication_outlined,
                      title: '복약관리',
                      index: 3,
                      children: [
                        _subTile('오늘의 복약', () => onSelectTab(3)),
                        _subTile(
                            '복약 일정',
                            () => onOpenPage((context) =>
                                MedicationsPage.openSchedule(
                                    context, apiClient))),
                        _subTile(
                            '복약 기록',
                            () => onOpenPage((context) =>
                                MedicationsPage.openHistory(
                                    context, apiClient))),
                        _subTile(
                            '복약 알림 설정',
                            () => onOpenPage(
                                MedicationsPage.openNotificationSettings)),
                      ],
                    ),
                    _actionTile(
                      icon: Icons.smart_toy_outlined,
                      title: 'AI 건강도우미',
                      onTap: () {
                        Navigator.of(context).pop();
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('AI 건강도우미 기능은 준비 중입니다.'),
                          ),
                        );
                      },
                    ),
                    _section(
                      icon: Icons.person_outline_rounded,
                      title: '내 정보',
                      index: 4,
                      children: [
                        _subTile(
                            '내 정보',
                            () => onOpenPage((context) =>
                                ProfilePage.openMyInfo(context, apiClient))),
                        _subTile('연결 설정',
                            () => onOpenPage(ProfilePage.openConnections)),
                        _subTile(
                            '알림 설정',
                            onOpenProfileNotificationSettings),
                        _subTile(
                            '동의 · 약관', () => onOpenPage(ProfilePage.openTerms)),
                      ],
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 2),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
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

  Widget _section({
    required IconData icon,
    required String title,
    required int index,
    required List<Widget> children,
  }) =>
      Container(
        margin: const EdgeInsets.only(bottom: 4),
        decoration: BoxDecoration(
          color: selectedIndex == index
              ? const Color(0xFFF4F3FF)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
        ),
        child: ExpansionTile(
          shape: const Border(),
          collapsedShape: const Border(),
          initiallyExpanded: selectedIndex == index,
          tilePadding: const EdgeInsets.symmetric(horizontal: 14),
          childrenPadding: const EdgeInsets.only(left: 32, right: 10, bottom: 7),
          iconColor: _primaryDark,
          collapsedIconColor: _secondary,
          leading: Icon(icon,
              color: selectedIndex == index ? _primaryDark : _secondary),
          title: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => onSelectTab(index),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Text(title,
                  style: TextStyle(
                      color: selectedIndex == index ? _primaryDark : _text,
                      fontWeight: FontWeight.w800)),
            ),
          ),
          children: children,
        ),
      );

  Widget _actionTile({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 1),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          leading: Icon(icon, color: _secondary),
          title: Text(title,
              style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
          trailing: const Icon(Icons.chevron_right_rounded, color: _secondary),
          onTap: onTap,
        ),
      );

  Widget _subTile(String title, VoidCallback onTap) => ListTile(
        dense: true,
        visualDensity: VisualDensity.compact,
        contentPadding: const EdgeInsets.symmetric(horizontal: 10),
        leading: const Icon(Icons.circle, size: 6, color: _primaryDark),
        title: Text(title,
            style: const TextStyle(
                color: _secondary, fontSize: 13, fontWeight: FontWeight.w600)),
        trailing: const Icon(Icons.chevron_right_rounded, size: 18, color: _secondary),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        onTap: onTap,
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
