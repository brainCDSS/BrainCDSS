import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../features/analysis/radiology_analysis_requests_page.dart';
import '../features/assessments/nurse_assessment_workflow.dart';
import '../features/auth/clinician_session.dart';
import '../features/consultations/radiology_consultations_page.dart';
import '../features/imaging/imaging_studies_page.dart';
import '../features/notifications/radiology_notifications_page.dart';
import '../features/patients/radiology_patients_page.dart';
import '../features/radiology/widgets/radiology_ui.dart';

class ClinicalRoleMainShell extends StatefulWidget {
  const ClinicalRoleMainShell({
    super.key,
    required this.apiClient,
    required this.user,
    required this.onLogout,
  });

  final ClinicianApiClient apiClient;
  final ClinicianUser user;
  final Future<void> Function() onLogout;

  @override
  State<ClinicalRoleMainShell> createState() => _ClinicalRoleMainShellState();
}

class _ClinicalRoleMainShellState extends State<ClinicalRoleMainShell> {
  int _selectedIndex = 0;
  late final List<Widget> _pages;
  late final List<NavigationDestination> _destinations;

  bool get _isNurse => widget.user.role.code == 'NURSE';

  @override
  void initState() {
    super.initState();
    if (_isNurse) {
      _pages = [
        NurseAssessmentWorklistPage(apiClient: widget.apiClient),
        RadiologyPatientsPage(
          apiClient: widget.apiClient,
          roleCode: 'NURSE',
        ),
        ImagingStudiesPage(apiClient: widget.apiClient),
        _RoleProfilePage(user: widget.user, onLogout: widget.onLogout),
      ];
      _destinations = const [
        NavigationDestination(
          icon: Icon(Icons.fact_check_outlined),
          selectedIcon: Icon(Icons.fact_check_rounded),
          label: '초기평가',
        ),
        NavigationDestination(
          icon: Icon(Icons.people_outline_rounded),
          selectedIcon: Icon(Icons.people_rounded),
          label: '환자',
        ),
        NavigationDestination(
          icon: Icon(Icons.image_search_outlined),
          selectedIcon: Icon(Icons.image_search_rounded),
          label: '영상',
        ),
        NavigationDestination(
          icon: Icon(Icons.person_outline_rounded),
          selectedIcon: Icon(Icons.person_rounded),
          label: '마이',
        ),
      ];
    } else {
      _pages = [
        RadiologyPatientsPage(
          apiClient: widget.apiClient,
          roleCode: 'NEUROSURGEON',
        ),
        RadiologyConsultationsPage(
          apiClient: widget.apiClient,
          viewerRelation: 'ASSIGNED_TO',
        ),
        ImagingStudiesPage(apiClient: widget.apiClient),
        RadiologyAnalysisRequestsPage(apiClient: widget.apiClient),
        _RoleProfilePage(user: widget.user, onLogout: widget.onLogout),
      ];
      _destinations = const [
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
          label: 'AI',
        ),
        NavigationDestination(
          icon: Icon(Icons.person_outline_rounded),
          selectedIcon: Icon(Icons.person_rounded),
          label: '마이',
        ),
      ];
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          titleSpacing: 20,
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Brain On',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
              ),
              Text(
                widget.user.role.name,
                style: const TextStyle(
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
                  builder: (_) => RadiologyNotificationsPage(
                    apiClient: widget.apiClient,
                  ),
                ),
              ),
              icon: const Icon(Icons.notifications_none_rounded),
            ),
          ],
        ),
        body: IndexedStack(index: _selectedIndex, children: _pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (index) =>
              setState(() => _selectedIndex = index),
          destinations: _destinations,
        ),
      );
}

class _RoleProfilePage extends StatelessWidget {
  const _RoleProfilePage({required this.user, required this.onLogout});

  final ClinicianUser user;
  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
          RadiologyInfoCard(
            child: Column(
              children: [
                const CircleAvatar(
                  radius: 30,
                  backgroundColor: Color(0xFFEAF2FF),
                  child: Icon(Icons.person_rounded, color: radiologyBlue),
                ),
                const SizedBox(height: 12),
                Text(
                  user.name,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(user.role.name,
                    style: const TextStyle(color: radiologyBlue)),
                const SizedBox(height: 18),
                OutlinedButton.icon(
                  onPressed: onLogout,
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('로그아웃'),
                ),
              ],
            ),
          ),
        ],
      );
}
