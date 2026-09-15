import 'package:flutter/material.dart';

import '../core/api/api_client.dart';
import '../features/appointments/appointments_page.dart';
import '../features/auth/auth_session.dart';
import '../features/emergency/fast_emergency_page.dart';
import '../features/home/home_page.dart';
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
  final VoidCallback onLogout;

  @override
  State<PatientMainShell> createState() =>
      _PatientMainShellState();
}

class _PatientMainShellState
    extends State<PatientMainShell> {
  int _selectedIndex = 0;
  final _appointmentsKey = GlobalKey<AppointmentsPageState>();

  late final List<Widget> _pages;

  static const List<String> _titles = [
    'BrainOn',
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
        apiClient: widget.apiClient,
        session: widget.session,
      ),
      AppointmentsPage(key: _appointmentsKey, apiClient: widget.apiClient),
      TestResultsPage(apiClient: widget.apiClient),
      MedicationsPage(apiClient: widget.apiClient),
      ProfilePage(
        session: widget.session,
        onLogout: widget.onLogout,
        apiClient: widget.apiClient,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Builder(
          builder: (context) => IconButton(
            tooltip: '메뉴',
            icon: const Icon(Icons.menu_rounded),
            onPressed: () => Scaffold.of(context).openDrawer(),
          ),
        ),
        title: Text(
          _titles[_selectedIndex],
        ),
        actions: _selectedIndex == 0
            ? [
                IconButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotificationsPage(apiClient: widget.apiClient))),
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
          setState(() => _selectedIndex = index);
        },
        onOpenPage: (openPage) {
          Navigator.of(context).pop();
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) openPage(context);
          });
        },
        onShowAppointmentSection: (showPast) {
          Navigator.of(context).pop();
          setState(() => _selectedIndex = 1);
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (showPast) {
              _appointmentsKey.currentState?.showPast();
            } else {
              _appointmentsKey.currentState?.showUpcoming();
            }
          });
        },
        onLogout: widget.onLogout,
      ),
      body: SafeArea(
        child: IndexedStack(
          index: _selectedIndex,
          children: _pages,
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
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
    required this.onShowAppointmentSection,
    required this.onLogout,
  });

  final AuthSession session;
  final ApiClient apiClient;
  final int selectedIndex;
  final ValueChanged<int> onSelectTab;
  final ValueChanged<void Function(BuildContext)> onOpenPage;
  final ValueChanged<bool> onShowAppointmentSection;
  final VoidCallback onLogout;

  static const _primaryDark = Color(0xFF5665B8);
  static const _primarySoft = Color(0xFFE5E8FF);
  static const _text = Color(0xFF263A5A);
  static const _secondary = Color(0xFF65758D);

  @override
  Widget build(BuildContext context) => Drawer(
        backgroundColor: Colors.white,
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 10, 16),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const CircleAvatar(
                      radius: 23,
                      backgroundColor: _primarySoft,
                      child: Text('B', style: TextStyle(color: _primaryDark, fontSize: 20, fontWeight: FontWeight.w900)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('BrainOn', style: TextStyle(color: _text, fontSize: 19, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 8),
                          Text(session.user.name, style: const TextStyle(color: _text, fontWeight: FontWeight.w800)),
                          const SizedBox(height: 2),
                          Text(session.user.loginId, style: const TextStyle(color: _secondary, fontSize: 12)),
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
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  children: [
                    _topLevelTile(icon: Icons.home_outlined, title: '홈', index: 0),
                    _section(
                      icon: Icons.calendar_month_outlined,
                      title: '예약',
                      index: 1,
                      children: [
                        _subTile('진료 예약하기', () => onOpenPage((context) => AppointmentsPage.openReservation(context, apiClient))),
                        _subTile('예정된 예약', () => onShowAppointmentSection(false)),
                        _subTile('지난 예약', () => onShowAppointmentSection(true)),
                      ],
                    ),
                    _section(
                      icon: Icons.health_and_safety_outlined,
                      title: '건강정보',
                      index: 2,
                      children: [
                        _subTile('검사 결과', () => onOpenPage(TestResultsPage.openResults)),
                        _subTile('진료 내역', () => onOpenPage(TestResultsPage.openVisits)),
                        _subTile('처방 정보', () => onOpenPage((context) => TestResultsPage.openPrescriptions(context, apiClient))),
                      ],
                    ),
                    _section(
                      icon: Icons.medication_outlined,
                      title: '복약관리',
                      index: 3,
                      children: [
                        _subTile('오늘의 복약', () => onSelectTab(3)),
                        _subTile('복약 일정', () => onOpenPage((context) => MedicationsPage.openSchedule(context, apiClient))),
                        _subTile('복약 기록', () => onOpenPage((context) => MedicationsPage.openHistory(context, apiClient))),
                        _subTile('복약 알림 설정', () => onOpenPage(MedicationsPage.openNotificationSettings)),
                      ],
                    ),
                    _section(
                      icon: Icons.person_outline_rounded,
                      title: '내 정보',
                      index: 4,
                      children: [
                        _subTile('내 정보', () => onOpenPage((context) => ProfilePage.openMyInfo(context, session))),
                        _subTile('연결 설정', () => onOpenPage(ProfilePage.openConnections)),
                        _subTile('알림 설정', () => onOpenPage((context) => ProfilePage.openNotifications(context, apiClient))),
                        _subTile('동의 · 약관', () => onOpenPage(ProfilePage.openTerms)),
                      ],
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.emergency_outlined, color: Color(0xFFE94E4E)),
                title: const Text('FAST 응급안내', style: TextStyle(color: Color(0xFFE94E4E), fontWeight: FontWeight.w800)),
                onTap: () => onOpenPage(FastEmergencyPage.open),
              ),
              ListTile(
                leading: const Icon(Icons.logout_rounded, color: _secondary),
                title: const Text('로그아웃', style: TextStyle(color: _text, fontWeight: FontWeight.w700)),
                onTap: () => _confirmLogout(context),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      );

  Widget _topLevelTile({required IconData icon, required String title, required int index}) =>
      ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        selected: selectedIndex == index,
        selectedTileColor: _primarySoft,
        selectedColor: _primaryDark,
        leading: Icon(icon),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        onTap: () => onSelectTab(index),
      );

  Widget _section({
    required IconData icon,
    required String title,
    required int index,
    required List<Widget> children,
  }) => Container(
        decoration: BoxDecoration(
          color: selectedIndex == index ? _primarySoft : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: ExpansionTile(
          shape: const Border(),
          collapsedShape: const Border(),
          initiallyExpanded: selectedIndex == index,
          leading: Icon(icon, color: selectedIndex == index ? _primaryDark : _secondary),
          title: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => onSelectTab(index),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Text(title, style: TextStyle(color: selectedIndex == index ? _primaryDark : _text, fontWeight: FontWeight.w800)),
            ),
          ),
          childrenPadding: const EdgeInsets.only(left: 28, bottom: 6),
          children: children,
        ),
      );

  Widget _subTile(String title, VoidCallback onTap) => ListTile(
        dense: true,
        visualDensity: VisualDensity.compact,
        leading: const Icon(Icons.circle, size: 6, color: _primaryDark),
        title: Text(title, style: const TextStyle(color: _secondary, fontSize: 13, fontWeight: FontWeight.w600)),
        onTap: onTap,
      );

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('로그아웃할까요?'),
        content: const Text('로그인 화면으로 이동합니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('로그아웃')),
        ],
      ),
    );
    if (confirmed == true) onLogout();
  }
}
