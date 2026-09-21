import 'package:flutter/material.dart';

import '../../radiology/widgets/radiology_ui.dart';

class NeurologyNavigation {
  static ValueChanged<int>? _onSelectTab;
  static VoidCallback? _onOpenClinicalRecords;
  static VoidCallback? _onOpenAssistant;
  static VoidCallback? _onLogout;

  static void configure({
    required ValueChanged<int> onSelectTab,
    required VoidCallback onOpenClinicalRecords,
    required VoidCallback onOpenAssistant,
    required VoidCallback onLogout,
  }) {
    _onSelectTab = onSelectTab;
    _onOpenClinicalRecords = onOpenClinicalRecords;
    _onOpenAssistant = onOpenAssistant;
    _onLogout = onLogout;
  }

  static void selectTab(BuildContext context, int index) {
    Navigator.of(context).pop();
    _onSelectTab?.call(index);
  }

  static void openAssistant(BuildContext context) {
    Navigator.of(context).pop();
    _onOpenAssistant?.call();
  }

  static void openClinicalRecords(BuildContext context) {
    Navigator.of(context).pop();
    _onOpenClinicalRecords?.call();
  }

  static void logout(BuildContext context) {
    Navigator.of(context).pop();
    _onLogout?.call();
  }
}

class NeurologyNavigationDrawer extends StatelessWidget {
  const NeurologyNavigationDrawer({super.key});

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
                    Text('신경과', style: TextStyle(color: radiologyMuted, fontSize: 13, fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
              _DrawerItem(icon: Icons.home_outlined, label: '홈', onTap: () => NeurologyNavigation.selectTab(context, 2)),
              _DrawerItem(icon: Icons.emergency_outlined, label: '응급', onTap: () => NeurologyNavigation.selectTab(context, 0)),
              _DrawerItem(icon: Icons.people_outline_rounded, label: '환자', onTap: () => NeurologyNavigation.selectTab(context, 1)),
              _DrawerItem(icon: Icons.forum_outlined, label: '협진', onTap: () => NeurologyNavigation.selectTab(context, 3)),
              _DrawerItem(icon: Icons.description_outlined, label: '진료기록', onTap: () => NeurologyNavigation.openClinicalRecords(context)),
              _DrawerItem(icon: Icons.smart_toy_outlined, label: 'AI 도우미', onTap: () => NeurologyNavigation.openAssistant(context)),
              _DrawerItem(icon: Icons.person_outline_rounded, label: '마이', onTap: () => NeurologyNavigation.selectTab(context, 4)),
              const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Divider(color: radiologyBorder)),
              _DrawerItem(icon: Icons.logout_rounded, label: '로그아웃', onTap: () => NeurologyNavigation.logout(context)),
            ],
          ),
        ),
      );
}

class NeurologyDrawerButton extends StatelessWidget {
  const NeurologyDrawerButton({super.key});

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
