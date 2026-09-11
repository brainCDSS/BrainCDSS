import 'package:flutter/material.dart';
import '../features/appointments/appointments_page.dart';
import '../features/home/home_page.dart';
import '../features/medications/medications_page.dart';
import '../features/profile/profile_page.dart';
import '../features/test-results/test_results_page.dart';

class PatientMainShell extends StatefulWidget {
  const PatientMainShell({super.key});

  @override
  State<PatientMainShell> createState() => _PatientMainShellState();
}

class _PatientMainShellState extends State<PatientMainShell> {
  int _selectedIndex = 0;

  static const _pages = <Widget>[
    HomePage(),
    AppointmentsPage(),
    TestResultsPage(),
    MedicationsPage(),
    ProfilePage(),
  ];
  static const _titles = ['BrainOn', '예약', '검사 · 결과', '복약관리', '마이페이지'];

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(_titles[_selectedIndex]),
          actions: _selectedIndex == 0
              ? [
                  IconButton(
                    onPressed: null,
                    tooltip: '알림 (준비 중)',
                    icon: const Icon(Icons.notifications_outlined),
                  ),
                ]
              : null,
        ),
        body: SafeArea(
          child: IndexedStack(index: _selectedIndex, children: _pages),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (index) => setState(() => _selectedIndex = index),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: '홈'),
            NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month), label: '예약'),
            NavigationDestination(icon: Icon(Icons.assignment_outlined), selectedIcon: Icon(Icons.assignment), label: '검사 · 결과'),
            NavigationDestination(icon: Icon(Icons.medication_outlined), selectedIcon: Icon(Icons.medication), label: '복약'),
            NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: '마이페이지'),
          ],
        ),
      );
}
