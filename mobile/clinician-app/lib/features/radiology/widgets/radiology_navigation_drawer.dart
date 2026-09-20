import 'package:flutter/material.dart';

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

  static void selectTab(BuildContext context, int index) {
    Navigator.of(context).pop();
    _onSelectTab?.call(index);
  }

  static void openPatient(String patientId) => _onOpenPatient?.call(patientId);

  static void openStudy(String studyId) => _onOpenStudy?.call(studyId);

  static void openConsultation(String consultationId) =>
      _onOpenConsultation?.call(consultationId);

  static void openConsultationMessages({
    required String consultationId,
    required String patientName,
    required String patientNo,
    required String consultationStatus,
  }) =>
      _onOpenConsultationMessages?.call(
        consultationId: consultationId,
        patientName: patientName,
        patientNo: patientNo,
        consultationStatus: consultationStatus,
      );

  static void openAnalysis(Object request) => _onOpenAnalysis?.call(request);

  static void openAssistant(BuildContext context) {
    Navigator.of(context).pop();
    _onOpenAssistant?.call();
  }

  static void closeDetail() => _onCloseDetail?.call();

  static void logout(BuildContext context) {
    Navigator.of(context).pop();
    _onLogout?.call();
  }
}

class RadiologyNavigationDrawer extends StatelessWidget {
  const RadiologyNavigationDrawer({super.key});

  @override
  Widget build(BuildContext context) => Drawer(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(12, 16, 12, 20),
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 8, 16, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Brain On', style: TextStyle(color: radiologyNavy, fontSize: 22, fontWeight: FontWeight.w800)),
                    SizedBox(height: 3),
                    Text('영상의학과', style: TextStyle(color: radiologyMuted, fontSize: 13, fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
              _DrawerItem(icon: Icons.home_outlined, label: '홈', onTap: () => RadiologyNavigation.selectTab(context, 2)),
              _DrawerItem(icon: Icons.people_outline_rounded, label: '환자', onTap: () => RadiologyNavigation.selectTab(context, 0)),
              _DrawerItem(icon: Icons.forum_outlined, label: '협진', onTap: () => RadiologyNavigation.selectTab(context, 1)),
              _DrawerItem(icon: Icons.analytics_outlined, label: '분석요청', onTap: () => RadiologyNavigation.selectTab(context, 3)),
              _DrawerItem(icon: Icons.smart_toy_outlined, label: 'AI 도우미', onTap: () => RadiologyNavigation.openAssistant(context)),
              _DrawerItem(icon: Icons.person_outline_rounded, label: '마이', onTap: () => RadiologyNavigation.selectTab(context, 4)),
              const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Divider(color: radiologyBorder)),
              _DrawerItem(icon: Icons.logout_rounded, label: '로그아웃', onTap: () => RadiologyNavigation.logout(context)),
            ],
          ),
        ),
      );
}

class RadiologyDrawerButton extends StatelessWidget {
  const RadiologyDrawerButton({super.key});

  @override
  Widget build(BuildContext context) => Builder(
        builder: (scaffoldContext) => IconButton(
          tooltip: '메뉴',
          icon: const Icon(Icons.menu_rounded),
          onPressed: () => Scaffold.of(scaffoldContext).openDrawer(),
        ),
      );
}

class _DrawerItem extends StatelessWidget {
  const _DrawerItem({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        leading: Icon(icon, color: radiologyBlue),
        title: Text(label, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w700)),
        trailing: const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
        onTap: onTap,
      );
}
