import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../features/analysis/radiology_analysis_requests_page.dart';
import '../features/auth/clinician_session.dart';
import '../features/consultations/radiology_consultations_page.dart';
import '../features/patients/radiology_patients_page.dart';
import '../features/profile/radiology_profile_page.dart';
import '../features/notifications/radiology_notifications_page.dart';
import '../features/imaging/imaging_studies_page.dart';

class RadiologyMainShell extends StatefulWidget {
  const RadiologyMainShell({
    super.key,
    required this.apiClient,
    required this.user,
    required this.onLogout,
  });

  final ClinicianApiClient apiClient;
  final ClinicianUser user;
  final Future<void> Function() onLogout;

  @override
  State<RadiologyMainShell> createState() => _RadiologyMainShellState();
}

class _RadiologyMainShellState extends State<RadiologyMainShell> {
  int _selectedIndex = 2;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      RadiologyPatientsPage(
        apiClient: widget.apiClient,
        roleCode: 'RADIOLOGY',
      ),
      RadiologyConsultationsPage(apiClient: widget.apiClient),
      ImagingStudiesPage(apiClient: widget.apiClient),
      RadiologyAnalysisRequestsPage(apiClient: widget.apiClient),
      RadiologyProfilePage(user: widget.user, onLogout: widget.onLogout),
    ];
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          titleSpacing: 20,
          title: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Brain On',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
              ),
              SizedBox(height: 1),
              Text(
                '영상의학과',
                style: TextStyle(
                  color: Color(0xFF60718A),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          actions: [
            IconButton(
              tooltip: '알림',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) =>
                      RadiologyNotificationsPage(apiClient: widget.apiClient),
                ),
              ),
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
              icon: Icon(Icons.people_outline_rounded),
              selectedIcon: Icon(Icons.people_rounded),
              label: '환자',
            ),
            NavigationDestination(
              icon: Icon(Icons.forum_outlined),
              selectedIcon: Icon(Icons.forum_rounded),
              label: '협진',
            ),
            NavigationDestination(
              icon: Icon(Icons.image_search_outlined),
              selectedIcon: Icon(Icons.image_search_rounded),
              label: '영상',
            ),
            NavigationDestination(
              icon: Icon(Icons.analytics_outlined),
              selectedIcon: Icon(Icons.analytics_rounded),
              label: '분석요청',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              selectedIcon: Icon(Icons.person_rounded),
              label: '마이',
            ),
          ],
        ),
      );
}
