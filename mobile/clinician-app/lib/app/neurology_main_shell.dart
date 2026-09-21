import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../features/auth/clinician_session.dart';
import '../features/emergency/neurology_emergency_worklist_page.dart';
import '../features/notifications/radiology_notifications_page.dart';
import '../features/assistant/clinician_ai_assistant_page.dart';
import '../features/assistant/draggable_assistant_button.dart';
import '../features/consultations/radiology_consultation_messages_page.dart';
import '../features/neurology/neurology_consultations_page.dart';
import '../features/neurology/neurology_pages.dart';
import '../features/neurology/neurology_patients_page.dart';
import '../features/neurology/widgets/neurology_navigation_drawer.dart';

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
  Widget? _assistantPage;
  Widget? _detailPage;
  Widget? _detailBackPage;
  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      NeurologyEmergencyWorklistPage(
        apiClient: widget.apiClient,
      ),
      NeurologyPatientsPage(apiClient: widget.apiClient),
      NeurologyHomePage(
        apiClient: widget.apiClient,
        onSelectTab: _selectTab,
        onOpenClinicalRecords: _openClinicalRecords,
      ),
      NeurologyConsultationsPage(
        apiClient: widget.apiClient,
        onOpenDetail: _openConsultationDetail,
      ),
      NeurologyProfilePage(user: widget.user, onLogout: widget.onLogout),
    ];
    NeurologyNavigation.configure(
      onSelectTab: _selectTab,
      onOpenClinicalRecords: _openClinicalRecords,
      onOpenAssistant: _openAssistant,
      onLogout: widget.onLogout,
    );
  }

  void _selectTab(int index) {
    setState(() {
      _assistantPage = null;
      _detailPage = null;
      _detailBackPage = null;
      _selectedIndex = index;
    });
  }

  void _openClinicalRecords() {
    setState(() {
      _assistantPage = null;
      _detailBackPage = null;
      _detailPage = const NeurologyClinicalRecordsPage();
    });
  }

  void _openConsultationDetail(String consultationId) {
    if (consultationId.isEmpty) {
      return;
    }
    setState(() {
      _assistantPage = null;
      _selectedIndex = 3;
      _detailBackPage = null;
      _detailPage = NeurologyConsultationDetailPage(
        key: ValueKey('neurology-consultation-$consultationId'),
        apiClient: widget.apiClient,
        consultationId: consultationId,
        onOpenMessages: _openConsultationMessages,
      );
    });
  }

  void _openConsultationMessages({
    required String consultationId,
    required String patientName,
    required String patientNo,
    required String consultationStatus,
  }) {
    if (consultationId.isEmpty) {
      return;
    }
    setState(() {
      _assistantPage = null;
      _selectedIndex = 3;
      _detailBackPage = _detailPage;
      _detailPage = RadiologyConsultationMessagesPage(
        key: ValueKey('neurology-consultation-messages-$consultationId'),
        apiClient: widget.apiClient,
        consultationId: consultationId,
        patientName: patientName,
        patientNo: patientNo,
        consultationStatus: consultationStatus,
      );
    });
  }

  void _openAssistant() {
    setState(() => _assistantPage = const ClinicianAiAssistantPage());
  }

  void _closeAssistant() {
    setState(() => _assistantPage = null);
  }

  void _closeDetail() {
    setState(() {
      _detailPage = _detailBackPage;
      _detailBackPage = null;
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        drawer: const NeurologyNavigationDrawer(),
        appBar: AppBar(
          leading: _assistantPage == null && _detailPage == null
              ? null
              : IconButton(
                  tooltip: '뒤로가기',
                  icon: const Icon(Icons.arrow_back_rounded),
                  onPressed: _assistantPage != null
                      ? _closeAssistant
                      : _closeDetail,
                ),
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
            if (_assistantPage != null || _detailPage != null)
              const NeurologyDrawerButton(),
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
            const SizedBox(width: 4),
          ],
        ),
        body: Stack(
          children: [
            Positioned.fill(
              child: _assistantPage ??
                  _detailPage ??
                  IndexedStack(index: _selectedIndex, children: _pages),
            ),
            if (_assistantPage == null)
              Positioned.fill(
                child: DraggableAssistantButton(
                  onTap: _openAssistant,
                  child: Image.asset(
                    'asset/images/floating.png',
                    width: 72,
                    height: 72,
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                  ),
                ),
              ),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: _selectTab,
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
                icon: Icon(Icons.forum_outlined),
                selectedIcon: Icon(Icons.forum_rounded),
                label: '협진'),
            NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: '마이'),
          ],
        ),
      );
}
