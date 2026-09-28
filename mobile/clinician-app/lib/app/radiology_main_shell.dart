import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../core/notifications/clinician_fcm_service.dart';
import '../features/analysis/radiology_analysis_detail_page.dart';
import '../features/analysis/radiology_analysis_requests_page.dart';
import '../features/assistant/clinician_ai_assistant_page.dart';
import '../features/assistant/draggable_assistant_button.dart';
import '../features/auth/clinician_session.dart';
import '../features/consultations/radiology_consultation_detail_page.dart';
import '../features/consultations/radiology_consultation_messages_page.dart';
import '../features/consultations/radiology_consultations_page.dart';
import '../features/home/radiology_home_page.dart';
import '../features/notifications/radiology_notifications_page.dart';
import '../features/patients/radiology_patient_detail_page.dart';
import '../features/patients/radiology_imaging_study_detail_page.dart';
import '../features/patients/radiology_patients_page.dart';
import '../features/profile/clinician_profile_pages.dart';
import '../features/radiology/widgets/radiology_navigation_drawer.dart';

class RadiologyMainShell extends StatefulWidget {
  const RadiologyMainShell({
    super.key,
    required this.apiClient,
    required this.user,
    required this.onLogout,
  });

  final ClinicianApiClient apiClient;
  final ClinicianUser user;
  final VoidCallback onLogout;

  @override
  State<RadiologyMainShell> createState() => _RadiologyMainShellState();
}

class _RadiologyMainShellState extends State<RadiologyMainShell> {
  int _selectedIndex = 2;

  Widget? _detailPage;
  Widget? _detailBackPage;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();

    _pages = [
      RadiologyPatientsPage(
        apiClient: widget.apiClient,
      ),
      RadiologyConsultationsPage(
        apiClient: widget.apiClient,
      ),
      RadiologyHomePage(
        apiClient: widget.apiClient,
        userName: widget.user.name,
      ),
      RadiologyAnalysisRequestsPage(
        apiClient: widget.apiClient,
      ),
      ClinicianProfilePage(
        user: widget.user,
        onLogout: widget.onLogout,
        onOpenNotificationSettings: _openNotificationSettings,
        onOpenProfileDetails: _openProfileDetails,
      ),
    ];

    RadiologyNavigation.configure(
      onSelectTab: _selectTab,
      onOpenPatient: _openPatientDetail,
      onOpenStudy: _openStudyDetail,
      onOpenConsultation: _openConsultationDetail,
      onOpenConsultationMessages: _openConsultationMessages,
      onOpenAnalysis: (request) {
        _openAnalysisDetail(
          request as RadiologyAnalysisRequest,
        );
      },
      onOpenAssistant: _openAssistant,
      onCloseDetail: _closeDetail,
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

  // ==========================================================================
  // 하단 탭 이동
  // ==========================================================================

  void _selectTab(int index) {
    setState(() {
      _detailPage = null;
      _detailBackPage = null;
      _selectedIndex = index;
    });
  }

  // ==========================================================================
  // 환자 상세
  // ==========================================================================

  void _openPatientDetail(String patientId) {
    if (patientId.isEmpty) {
      return;
    }

    setState(() {
      _selectedIndex = 0;
      _detailBackPage = null;

      _detailPage = RadiologyPatientDetailPage(
        key: ValueKey(
          'patient-$patientId',
        ),
        apiClient: widget.apiClient,
        patientId: patientId,
        user: widget.user,
        selectedIndex: _selectedIndex,
      );
    });
  }

  void _openStudyDetail(String studyId) {
    if (studyId.isEmpty) {
      return;
    }

    setState(() {
      _selectedIndex = 0;
      _detailBackPage = _detailPage;
      _detailPage = RadiologyImagingStudyDetailPage(
        key: ValueKey('study-$studyId'),
        apiClient: widget.apiClient,
        studyId: studyId,
      );
    });
  }

  // ==========================================================================
  // 협진 상세
  // ==========================================================================

  void _openConsultationDetail(
    String consultationId,
  ) {
    if (consultationId.isEmpty) {
      return;
    }

    setState(() {
      _selectedIndex = 1;
      _detailBackPage = null;

      _detailPage = RadiologyConsultationDetailPage(
        key: ValueKey(
          'consultation-$consultationId',
        ),
        apiClient: widget.apiClient,
        consultationId: consultationId,
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
      _selectedIndex = 1;
      _detailBackPage = _detailPage;
      _detailPage = RadiologyConsultationMessagesPage(
        key: ValueKey('consultation-messages-$consultationId'),
        apiClient: widget.apiClient,
        consultationId: consultationId,
        patientName: patientName,
        patientNo: patientNo,
        consultationStatus: consultationStatus,
      );
    });
  }

  // ==========================================================================
  // 분석 상세
  // ==========================================================================

  void _openAnalysisDetail(
    RadiologyAnalysisRequest request,
  ) {
    if (request.analysisId.isEmpty) {
      return;
    }

    setState(() {
      _selectedIndex = 3;
      _detailBackPage = null;

      _detailPage = RadiologyAnalysisDetailPage(
        key: ValueKey(
          'analysis-${request.analysisId}',
        ),
        apiClient: widget.apiClient,
        request: request,
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
      _openAnalysisDetail(request);
    } on ClinicianApiException {
      if (mounted) _openAnalysisRequests();
    } catch (_) {
      if (mounted) _openAnalysisRequests();
    }
  }

  void _openAnalysisRequests() {
    setState(() {
      _selectedIndex = 3;
      _detailBackPage = null;
      _detailPage = null;
    });
  }

  // ==========================================================================
  // 상세 닫기
  // ==========================================================================

  void _closeDetail() {
    if (_detailPage == null) {
      return;
    }

    setState(() {
      _detailPage = _detailBackPage;
      _detailBackPage = null;
    });
  }

  // ==========================================================================
  // AI 도우미
  // ==========================================================================

  void _openAssistant() {
    setState(() {
      _detailBackPage = null;
      _detailPage = ClinicianAiAssistantPage(
        apiClient: widget.apiClient,
      );
    });
  }

  // ==========================================================================
  // 알림
  // ==========================================================================

  void _openNotifications() {
    setState(() {
      _detailBackPage = _detailPage;
      _detailPage = RadiologyNotificationsPage(
        apiClient: widget.apiClient,
        onOpenConsultation: _openConsultationDetail,
        onOpenAnalysis: _openAnalysisDetailById,
      );
    });
  }

  void _openNotificationSettings() {
    setState(() {
      _detailBackPage = null;
      _detailPage = ClinicianNotificationSettingsPage(
        apiClient: widget.apiClient,
      );
    });
  }

  void _openProfileDetails() {
    setState(() {
      _detailBackPage = null;
      _detailPage = ClinicianProfileDetailsPage(
        user: widget.user,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDetail = _detailPage != null;
    final isAssistant = _detailPage is ClinicianAiAssistantPage;
    final messagePage = _detailPage is RadiologyConsultationMessagesPage
        ? _detailPage! as RadiologyConsultationMessagesPage
        : null;

    return PopScope(
      canPop: !isDetail,
      onPopInvoked: (didPop) {
        if (!didPop && isDetail) {
          _closeDetail();
        }
      },
      child: Scaffold(
        drawer: RadiologyNavigationDrawer(
          user: widget.user,
          selectedIndex: _selectedIndex,
        ),

        // ======================================================================
        // AppBar
        // ======================================================================

        appBar: AppBar(
          leading: isDetail
              ? IconButton(
                  tooltip: '뒤로가기',
                  icon: const Icon(
                    Icons.arrow_back_rounded,
                  ),
                  onPressed: _closeDetail,
                )
              : null,
          titleSpacing: isDetail ? 0 : 20,
          title: messagePage == null
              ? const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Brain On',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 1),
                    Text(
                      '영상의학과',
                      style: TextStyle(
                        color: Color.fromARGB(255, 137, 171, 223),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '협진 메시지',
                      style:
                          TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                    ),
                    if (messagePage.patientName.trim().isNotEmpty ||
                        messagePage.patientNo.trim().isNotEmpty)
                      Text(
                        [
                          if (messagePage.patientName.trim().isNotEmpty)
                            messagePage.patientName.trim(),
                          if (messagePage.patientNo.trim().isNotEmpty)
                            '(${messagePage.patientNo.trim()})',
                        ].join(' '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFF60718A),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
          actions: [
            if (isDetail) const RadiologyDrawerButton(),
            IconButton(
              tooltip: '알림',
              onPressed: _openNotifications,
              icon: const Icon(
                Icons.notifications_none_rounded,
              ),
            ),
            const SizedBox(width: 4),
          ],
        ),

        // ======================================================================
        // Body
        // ======================================================================

        body: Stack(
          children: [
            Positioned.fill(
              child: isDetail
                  ? Stack(
                      children: [
                        Positioned.fill(
                          child: Offstage(
                            offstage: _detailBackPage != null,
                            child: _detailBackPage ?? _detailPage!,
                          ),
                        ),
                        if (_detailBackPage != null)
                          Positioned.fill(child: _detailPage!),
                      ],
                    )
                  : IndexedStack(
                      index: _selectedIndex,
                      children: _pages,
                    ),
            ),
            if (!isAssistant)
              Positioned.fill(
                child: DraggableAssistantButton(
                  onTap: _openAssistant,
                  child: Image.asset(
                    'asset/images/floating.png',
                    width: 72,
                    height: 72,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        decoration: const BoxDecoration(
                          color: Color(0xFF4F8FE8),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.chat_bubble_rounded,
                          color: Colors.white,
                          size: 30,
                        ),
                      );
                    },
                  ),
                ),
              ),
          ],
        ),

        // ======================================================================
        // ======================================================================
        // 하단 네비게이션
        // ======================================================================

        bottomNavigationBar: SafeArea(
          top: false,
          child: Container(
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(
                top: BorderSide(
                  color: Color(0xFFE4EBF3),
                ),
              ),
            ),
            padding: const EdgeInsets.fromLTRB(
              8,
              8,
              8,
              6,
            ),
            child: Row(
              children: [
                _BottomNavItem(
                  icon: Icons.people_outline_rounded,
                  selectedIcon: Icons.people_rounded,
                  label: '환자',
                  selected: _selectedIndex == 0,
                  onTap: () => _selectTab(0),
                ),
                _BottomNavItem(
                  icon: Icons.forum_outlined,
                  selectedIcon: Icons.forum_rounded,
                  label: '협진',
                  selected: _selectedIndex == 1,
                  onTap: () => _selectTab(1),
                ),
                _BottomNavItem(
                  icon: Icons.home_outlined,
                  selectedIcon: Icons.home_rounded,
                  label: '홈',
                  selected: _selectedIndex == 2,
                  emphasize: true,
                  onTap: () => _selectTab(2),
                ),
                _BottomNavItem(
                  icon: Icons.analytics_outlined,
                  selectedIcon: Icons.analytics_rounded,
                  label: '분석요청',
                  selected: _selectedIndex == 3,
                  onTap: () => _selectTab(3),
                ),
                _BottomNavItem(
                  icon: Icons.person_outline_rounded,
                  selectedIcon: Icons.person_rounded,
                  label: '마이',
                  selected: _selectedIndex == 4,
                  onTap: () => _selectTab(4),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 하단 네비게이션 아이템
// ============================================================================

class _BottomNavItem extends StatelessWidget {
  const _BottomNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.selected,
    required this.onTap,
    this.emphasize = false,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: 4,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(
                  milliseconds: 180,
                ),
                width: emphasize && selected ? 54 : 42,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: selected
                      ? const Color(
                          0xFFEAF2FF,
                        )
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(
                    18,
                  ),
                ),
                child: Icon(
                  selected ? selectedIcon : icon,
                  size: emphasize ? 23 : 21,
                  color: selected
                      ? const Color(
                          0xFF4F8FE8,
                        )
                      : const Color(
                          0xFF667085,
                        ),
                ),
              ),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  color: selected
                      ? const Color(
                          0xFF4F8FE8,
                        )
                      : const Color(
                          0xFF263247,
                        ),
                  fontSize: 11,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
