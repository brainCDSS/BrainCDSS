import 'package:flutter/material.dart';

import '../../auth/clinician_session.dart';
import 'radiology_ui.dart';

class RadiologyNavigation {
  static ValueChanged<int>? _onSelectTab;
  static ValueChanged<String>? _onOpenPatient;
  static ValueChanged<String>? _onOpenStudy;
  static ValueChanged<String>? _onOpenConsultation;

  static void Function({
    required String consultationId,
    required String patientName,
    required String patientNo,
    required String consultationStatus,
  })? _onOpenConsultationMessages;

  static ValueChanged<Object>? _onOpenAnalysis;
  static VoidCallback? _onOpenAssistant;
  static VoidCallback? _onCloseDetail;
  static VoidCallback? _onLogout;

  static void configure({
    required ValueChanged<int> onSelectTab,
    required ValueChanged<String> onOpenPatient,
    required ValueChanged<String> onOpenStudy,
    required ValueChanged<String> onOpenConsultation,
    required void Function({
      required String consultationId,
      required String patientName,
      required String patientNo,
      required String consultationStatus,
    }) onOpenConsultationMessages,
    required ValueChanged<Object> onOpenAnalysis,
    required VoidCallback onOpenAssistant,
    required VoidCallback onCloseDetail,
    required VoidCallback onLogout,
  }) {
    _onSelectTab = onSelectTab;
    _onOpenPatient = onOpenPatient;
    _onOpenStudy = onOpenStudy;
    _onOpenConsultation = onOpenConsultation;
    _onOpenConsultationMessages = onOpenConsultationMessages;
    _onOpenAnalysis = onOpenAnalysis;
    _onOpenAssistant = onOpenAssistant;
    _onCloseDetail = onCloseDetail;
    _onLogout = onLogout;
  }

  // Drawer 안에서 탭 이동
  static void selectTab(
    BuildContext context,
    int index,
  ) {
    Navigator.of(context).pop();
    _onSelectTab?.call(index);
  }

  // 홈의 "최근 분석 > 전체보기"
  static void openAnalysisRequests() {
    _onSelectTab?.call(3);
  }

  static void openPatient(String patientId) {
    _onOpenPatient?.call(patientId);
  }

  static void openStudy(String studyId) {
    _onOpenStudy?.call(studyId);
  }

  static void openConsultation(String consultationId) {
    _onOpenConsultation?.call(consultationId);
  }

  static void openConsultationMessages({
    required String consultationId,
    required String patientName,
    required String patientNo,
    required String consultationStatus,
  }) {
    _onOpenConsultationMessages?.call(
      consultationId: consultationId,
      patientName: patientName,
      patientNo: patientNo,
      consultationStatus: consultationStatus,
    );
  }

  static void openAnalysis(Object request) {
    _onOpenAnalysis?.call(request);
  }

  static void openAssistant(BuildContext context) {
    Navigator.of(context).pop();
    _onOpenAssistant?.call();
  }

  static void closeDetail() {
    _onCloseDetail?.call();
  }

  static void logout(BuildContext context) {
    Navigator.of(context).pop();
    _onLogout?.call();
  }
}

class RadiologyNavigationDrawer extends StatelessWidget {
  const RadiologyNavigationDrawer({
    super.key,
    required this.user,
    required this.selectedIndex,
  });

  final ClinicianUser user;
  final int selectedIndex;

  @override
  Widget build(BuildContext context) {
    final departmentName =
        user.role.name.trim().isEmpty ? '영상의학과' : user.role.name.trim();

    final loginId = user.loginId.trim().isEmpty ? '-' : user.loginId.trim();

    return Drawer(
      width: MediaQuery.of(context).size.width * 0.72,
      elevation: 0,
      backgroundColor: const Color(0xFFF8FBFF),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topRight: Radius.circular(20),
          bottomRight: Radius.circular(20),
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            18,
            18,
            14,
            14,
          ),
          child: Column(
            children: [
              // ==============================================================
              // 프로필 카드
              // ==============================================================

              _ProfileCard(
                name: user.name,
                department: departmentName,
                loginId: loginId,
                onTap: () {
                  RadiologyNavigation.selectTab(
                    context,
                    4,
                  );
                },
              ),

              const SizedBox(height: 24),

              // ==============================================================
              // 주요 메뉴
              // ==============================================================

              _DrawerMenuItem(
                label: '홈',
                selected: selectedIndex == 2,
                onTap: () {
                  RadiologyNavigation.selectTab(
                    context,
                    2,
                  );
                },
              ),

              const SizedBox(height: 4),

              _DrawerMenuItem(
                label: '환자',
                selected: selectedIndex == 0,
                onTap: () {
                  RadiologyNavigation.selectTab(
                    context,
                    0,
                  );
                },
              ),

              const SizedBox(height: 4),

              _DrawerMenuItem(
                label: '협진',
                selected: selectedIndex == 1,
                onTap: () {
                  RadiologyNavigation.selectTab(
                    context,
                    1,
                  );
                },
              ),

              const SizedBox(height: 4),

              _DrawerMenuItem(
                label: '분석요청',
                selected: selectedIndex == 3,
                onTap: () {
                  RadiologyNavigation.selectTab(
                    context,
                    3,
                  );
                },
              ),

              const SizedBox(height: 4),

              _DrawerMenuItem(
                label: 'AI 도우미',
                selected: false,
                onTap: () {
                  RadiologyNavigation.openAssistant(
                    context,
                  );
                },
              ),

              const SizedBox(height: 18),

              // ==============================================================
              // 마이페이지
              // ==============================================================

              _DrawerMenuItem(
                label: '마이페이지',
                selected: selectedIndex == 4,
                onTap: () {
                  RadiologyNavigation.selectTab(
                    context,
                    4,
                  );
                },
              ),

              // ==============================================================
              // 목업처럼 중간 여백을 크게 확보
              // ==============================================================

              const Spacer(),

              // ==============================================================
              // 로그아웃
              // ==============================================================

              _LogoutButton(
                onTap: () {
                  RadiologyNavigation.logout(
                    context,
                  );
                },
              ),

              const SizedBox(height: 22),

              // ==============================================================
              // Footer
              // ==============================================================

              const Row(
                children: [
                  Text(
                    'Brain On  v1.0.0',
                    style: TextStyle(
                      color: Color(0xFF7183A0),
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Spacer(),
                  Flexible(
                    child: Text(
                      'Better Brain, Brighter Tomorrow',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.right,
                      style: TextStyle(
                        color: Color(0xFF7183A0),
                        fontSize: 9,
                        fontStyle: FontStyle.italic,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 4),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 프로필 카드
// ============================================================================

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({
    required this.name,
    required this.department,
    required this.loginId,
    required this.onTap,
  });

  final String name;
  final String department;
  final String loginId;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFFF8FBFF),
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: 14,
            vertical: 14,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),

            //기존보다 조금 더 보이는 블루 계열 테두리
            border: Border.all(
              color: const Color(0xFFF0F3F8),
              width: 1.4,
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(
                  0xFF263247,
                ).withValues(
                  alpha: 0.010,
                ),
                blurRadius: 18,
                offset: const Offset(
                  0,
                  6,
                ),
              ),
            ],
          ),
          child: Row(
            children: [
              // 프로필 아이콘
              Container(
                width: 58,
                height: 58,
                decoration: const BoxDecoration(
                  color: Color(0xFFEAF2FF),//아이콘 동그라미
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.person_rounded,
                  color: radiologyBlue,
                  size: 30,
                ),
              ),

              const SizedBox(width: 14),

              // 이름 / 진료과 / ID
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name.trim().isEmpty ? '의료진' : name.trim(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: radiologyNavy,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        height: 1.15,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      department,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF7183A0),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      loginId,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF7E8DA5),
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 8),

              const Icon(
                Icons.chevron_right_rounded,
                color: Color(0xFF667085),
                size: 25,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 메뉴 아이템
// ============================================================================

class _DrawerMenuItem extends StatelessWidget {
  const _DrawerMenuItem({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? const Color(0xFFE6F0FF) : Colors.transparent,
      borderRadius: BorderRadius.circular(13),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(13),
        child: SizedBox(
          height: 54,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 14,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: selected ? const Color(0xFF1677F0) : radiologyNavy,
                      fontSize: 17,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w700,
                    ),
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: selected
                      ? const Color(0xFF1677F0)
                      : const Color(0xFF667085),
                  size: 25,
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
// 로그아웃 버튼
// ============================================================================

class _LogoutButton extends StatelessWidget {
  const _LogoutButton({
    required this.onTap,
  });

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFFFFF8F8),
      borderRadius: BorderRadius.circular(15),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(15),
        child: Container(
          width: double.infinity,
          height: 58,
          padding: const EdgeInsets.symmetric(
            horizontal: 16,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(15),
            border: Border.all(
              color: const Color(0xFFFFC9C9),
              width: 1.2,
            ),
          ),
          child: const Row(
            children: [
              Icon(
                Icons.logout_rounded,
                color: Color(0xFFFF3B3B),
                size: 24,
              ),
              SizedBox(width: 13),
              Expanded(
                child: Text(
                  '로그아웃',
                  style: TextStyle(
                    color: Color(0xFFFF3B3B),
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: Color(0xFFE45A5A),
                size: 25,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 상세 화면에서 Drawer 여는 버튼
// ============================================================================

class RadiologyDrawerButton extends StatelessWidget {
  const RadiologyDrawerButton({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Builder(
      builder: (scaffoldContext) {
        return IconButton(
          tooltip: '메뉴',
          icon: const Icon(
            Icons.menu_rounded,
          ),
          onPressed: () {
            Scaffold.of(
              scaffoldContext,
            ).openDrawer();
          },
        );
      },
    );
  }
}
