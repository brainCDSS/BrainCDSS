import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../core/notifications/clinician_fcm_service.dart';
import '../features/analysis/radiology_analysis_detail_page.dart';
import '../features/analysis/radiology_analysis_requests_page.dart';
import '../features/auth/clinician_session.dart';
import '../features/assistant/clinician_ai_assistant_page.dart';
import '../features/assistant/draggable_assistant_button.dart';
import '../features/consultations/radiology_consultation_messages_page.dart';
import '../features/neurology/neurology_clinical_records_page.dart';
import '../features/neurology/neurology_consultations_page.dart';
import '../features/neurology/neurology_pages.dart';
import '../features/neurology/neurology_patients_page.dart';
import '../features/neurology/widgets/neurology_navigation_drawer.dart';
import '../features/neurology/widgets/neurology_common_app_bar.dart';
import '../features/notifications/radiology_notifications_page.dart';
import '../features/profile/clinician_profile_pages.dart';

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
  int _emergencyRefreshVersion = 0;
  int _consultationRefreshVersion = 0;
  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      NeurologyEmergencyPage(
        key: ValueKey('neurology-emergency-$_emergencyRefreshVersion'),
        apiClient: widget.apiClient,
        onOpenDetail: _openEmergencyDetail,
      ),
      NeurologyPatientsPage(
        apiClient: widget.apiClient,
        currentUserId: widget.user.id,
        onOpenConsultationDetail: _openConsultationDetail,
      ),
      NeurologyHomePage(
        apiClient: widget.apiClient,
        userName: widget.user.name,
        currentUserId: widget.user.id,
        onSelectTab: _selectTab,
        onOpenClinicalRecords: _openClinicalRecords,
        onOpenConsultationDetail: _openConsultationDetail,
      ),
      NeurologyConsultationsPage(
        key: ValueKey('neurology-consultations-$_consultationRefreshVersion'),
        apiClient: widget.apiClient,
        onOpenDetail: _openConsultationDetail,
      ),
      ClinicianProfilePage(
        user: widget.user,
        onLogout: widget.onLogout,
        onOpenNotificationSettings: _openNotificationSettings,
        onOpenProfileDetails: _openProfileDetails,
      ),
    ];
    NeurologyNavigation.configure(
      onSelectTab: _selectTab,
      onOpenClinicalRecords: _openClinicalRecords,
      onOpenAssistant: _openAssistant,
      onOpenNotifications: _openNotifications,
      onLogout: widget.onLogout,
    );
    ClinicianFcmService.instance.bindConsultationNavigation(
      _openConsultationDetail,
    );
    ClinicianFcmService.instance.bindNotificationsNavigation(
      _openNotifications,
    );
    ClinicianFcmService.instance.bindAnalysisNavigation(
      _openAnalysisDetailById,
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
      _detailPage = NeurologyClinicalRecordsPage(
        apiClient: widget.apiClient,
        onOpenDetail: _openClinicalNoteDetail,
      );
    });
  }

  void _openClinicalNoteDetail(String noteId) {
    if (noteId.isEmpty) return;
    setState(() {
      _assistantPage = null;
      _detailBackPage = _detailPage;
      _detailPage = NeurologyClinicalNoteDetailPage(
        key: ValueKey('neurology-clinical-note-$noteId'),
        apiClient: widget.apiClient,
        noteId: noteId,
        currentUserId: widget.user.id,
      );
    });
  }

  void _openEmergencyDetail(EmergencyWorklistItem item) {
    if (item.assessmentId.isEmpty) {
      return;
    }
    setState(() {
      _assistantPage = null;
      _selectedIndex = 0;
      _detailBackPage = null;
      _detailPage = NeurologyEmergencyDetailPage(
        key: ValueKey('neurology-emergency-${item.assessmentId}'),
        apiClient: widget.apiClient,
        item: item,
        onAcknowledged: _refreshEmergencyWorklist,
      );
    });
  }

  void _refreshEmergencyWorklist() {
    setState(() {
      _emergencyRefreshVersion++;
      _pages[0] = NeurologyEmergencyPage(
        key: ValueKey('neurology-emergency-$_emergencyRefreshVersion'),
        apiClient: widget.apiClient,
        onOpenDetail: _openEmergencyDetail,
      );
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
      _consultationRefreshVersion++;
      _pages[3] = NeurologyConsultationsPage(
        key: ValueKey('neurology-consultations-$_consultationRefreshVersion'),
        apiClient: widget.apiClient,
        onOpenDetail: _openConsultationDetail,
      );
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

  Future<void> _openAnalysisDetailById(String analysisId) async {
    if (analysisId.isEmpty) return;
    try {
      final response = await widget.apiClient.get(
        '/api/v1/ai-analyses/$analysisId',
      );
      final request = RadiologyAnalysisRequest.fromJson(response);
      if (request.analysisId != analysisId || !mounted) {
        return;
      }
      setState(() {
        _assistantPage = null;
        _detailBackPage = null;
        _detailPage = RadiologyAnalysisDetailPage(
          key: ValueKey('neurology-analysis-$analysisId'),
          apiClient: widget.apiClient,
          request: request,
        );
      });
    } on ClinicianApiException {
      if (mounted) _openNotifications();
    } catch (_) {
      if (mounted) _openNotifications();
    }
  }

  void _openAssistant() {
    setState(
      () => _assistantPage = ClinicianAiAssistantPage(
        apiClient: widget.apiClient,
      ),
    );
  }

  void _closeAssistant() {
    setState(() => _assistantPage = null);
  }

  void _closeDetail() {
    setState(() {
      if (_detailPage is RadiologyNotificationsPage &&
          _detailBackPage is ClinicianAiAssistantPage) {
        _assistantPage = _detailBackPage;
        _detailPage = null;
        _detailBackPage = null;
        return;
      }
      _detailPage = _detailBackPage;
      _detailBackPage = null;
    });
  }

  void _openNotifications() {
    setState(() {
      _detailBackPage = _assistantPage ?? _detailPage;
      _assistantPage = null;
      _detailPage = RadiologyNotificationsPage(
        apiClient: widget.apiClient,
        onOpenConsultation: _openConsultationDetail,
        onOpenAnalysis: _openAnalysisDetailById,
      );
    });
  }

  void _openNotificationSettings() {
    setState(() {
      _assistantPage = null;
      _detailBackPage = null;
      _detailPage = ClinicianNotificationSettingsPage(
        apiClient: widget.apiClient,
      );
    });
  }

  void _openProfileDetails() {
    setState(() {
      _assistantPage = null;
      _detailBackPage = null;
      _detailPage = ClinicianProfileDetailsPage(
        user: widget.user,
      );
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        drawer: NeurologyNavigationDrawer(
          user: widget.user,
        ),
        appBar: NeurologyCommonAppBar(
          screenTitle: _headerTitle,
          onBack: _assistantPage != null || _detailPage != null
              ? (_assistantPage != null ? _closeAssistant : _closeDetail)
              : null,
          onNotifications: _openNotifications,
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

  String get _headerTitle {
    if (_assistantPage != null) return 'AI 어시스턴트';
    return switch (_detailPage) {
      NeurologyClinicalRecordsPage() => '진료기록',
      NeurologyClinicalNoteDetailPage() => '진료기록 상세',
      NeurologyEmergencyDetailPage() => '응급 평가 상세',
      NeurologyConsultationDetailPage() => '협진 상세',
      RadiologyConsultationMessagesPage() => '협진 메시지',
      RadiologyNotificationsPage() => '알림센터',
      ClinicianNotificationSettingsPage() => '알림 설정',
      ClinicianProfileDetailsPage() => '내 정보',
      _ => '신경과',
    };
  }
}
