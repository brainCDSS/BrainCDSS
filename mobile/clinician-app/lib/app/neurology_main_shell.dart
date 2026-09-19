import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../features/auth/clinician_session.dart';
import '../features/neurology/neurology_pages.dart';
import '../features/patients/radiology_patients_page.dart';

class NeurologyMainShell extends StatefulWidget {
  const NeurologyMainShell({
    super.key,
    required this.apiClient,
    required this.user,
    required this.onLogout,
  });

  final ClinicianApiClient apiClient;
  final ClinicianUser user;
  final VoidCallback onLogout;

  @override
  State<NeurologyMainShell> createState() => _NeurologyMainShellState();
}

class _NeurologyMainShellState extends State<NeurologyMainShell> {
  int _selectedIndex = 2;
  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      NeurologyEmergencyPage(apiClient: widget.apiClient),
      RadiologyPatientsPage(apiClient: widget.apiClient),
      NeurologyHomePage(apiClient: widget.apiClient),
      const NeurologyClinicalRecordsPage(),
      NeurologyProfilePage(user: widget.user, onLogout: widget.onLogout),
    ];
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          titleSpacing: 20,
          title: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Brain On',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
              SizedBox(height: 1),
              Text('신경과',
                  style: TextStyle(
                      color: Color(0xFF60718A),
                      fontSize: 12,
                      fontWeight: FontWeight.w600)),
            ],
          ),
          actions: [
            IconButton(
              tooltip: '알림',
              onPressed: () {},
              icon: const Icon(Icons.notifications_none_rounded),
            ),
            const SizedBox(width: 4),
          ],
        ),
        body: IndexedStack(index: _selectedIndex, children: _pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (index) =>
              setState(() => _selectedIndex = index),
          destinations: const [
            NavigationDestination(
                icon: Icon(Icons.emergency_outlined),
                selectedIcon: Icon(Icons.emergency_rounded),
                label: '응급'),
            NavigationDestination(
                icon: Icon(Icons.people_outline_rounded),
                selectedIcon: Icon(Icons.people_rounded),
                label: '환자'),
            NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home_rounded),
                label: '홈'),
            NavigationDestination(
                icon: Icon(Icons.description_outlined),
                selectedIcon: Icon(Icons.description_rounded),
                label: '진료기록'),
            NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: '마이'),
          ],
        ),
      );
}
