import 'package:flutter/material.dart';

import '../../auth/clinician_session.dart';
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
  const NeurologyNavigationDrawer({
    super.key,
    required this.user,
  });

  final ClinicianUser user;

  @override
  Widget build(BuildContext context) {
    final displayName = user.name.isEmpty ? '이름 정보 없음' : user.name;

    final account = user.loginId.isNotEmpty ? user.loginId : user.email;

    return Drawer(
      backgroundColor: const Color(0xFFF8FAFD),
      child: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  14,
                  18,
                  14,
                  12,
                ),
                children: [
                  // ==========================================================
                  // 계정 정보 카드
                  // ==========================================================

                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        color: radiologyBorder,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(
                            alpha: 0.04,
                          ),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 54,
                          height: 54,
                          decoration: const BoxDecoration(
                            color: Color(0xFFEAF2FF),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.person_rounded,
                            color: radiologyBlue,
                            size: 30,
                          ),
                        ),
                        const SizedBox(width: 13),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                displayName,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: radiologyNavy,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                '신경과',
                                style: TextStyle(
                                  color: radiologyMuted,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              if (account.isNotEmpty) ...[
                                const SizedBox(height: 2),
                                Text(
                                  account,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: Color(0xFF8A94A6),
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Icon(
                          Icons.chevron_right_rounded,
                          color: radiologyMuted,
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 22),

                  // ==========================================================
                  // 메뉴
                  // ==========================================================

                  _DrawerItem(
                    icon: Icons.home_outlined,
                    label: '홈',
                    onTap: () => NeurologyNavigation.selectTab(
                      context,
                      2,
                    ),
                  ),

                  _DrawerItem(
                    icon: Icons.emergency_outlined,
                    label: '응급',
                    onTap: () => NeurologyNavigation.selectTab(
                      context,
                      0,
                    ),
                  ),

                  _DrawerItem(
                    icon: Icons.people_outline_rounded,
                    label: '환자',
                    onTap: () => NeurologyNavigation.selectTab(
                      context,
                      1,
                    ),
                  ),

                  _DrawerItem(
                    icon: Icons.forum_outlined,
                    label: '협진',
                    onTap: () => NeurologyNavigation.selectTab(
                      context,
                      3,
                    ),
                  ),

                  _DrawerItem(
                    icon: Icons.smart_toy_outlined,
                    label: 'AI 도우미',
                    onTap: () => NeurologyNavigation.openAssistant(
                      context,
                    ),
                  ),

                  _DrawerItem(
                    icon: Icons.person_outline_rounded,
                    label: '마이페이지',
                    onTap: () => NeurologyNavigation.selectTab(
                      context,
                      4,
                    ),
                  ),
                ],
              ),
            ),

            // ==========================================================
            // 로그아웃
            // ==========================================================

            Padding(
              padding: const EdgeInsets.fromLTRB(
                14,
                8,
                14,
                10,
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: () => NeurologyNavigation.logout(context),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 14,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF3F3),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: const Color(0xFFFFDADA),
                    ),
                  ),
                  child: const Row(
                    children: [
                      Icon(
                        Icons.logout_rounded,
                        color: Color(0xFFD92D20),
                      ),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          '로그아웃',
                          style: TextStyle(
                            color: Color(0xFFD92D20),
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      Icon(
                        Icons.chevron_right_rounded,
                        color: Color(0xFFD92D20),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // ==========================================================
            // Footer
            // ==========================================================

            const Padding(
              padding: EdgeInsets.fromLTRB(
                18,
                8,
                18,
                18,
              ),
              child: Row(
                children: [
                  Text(
                    'Brain On  v1.0.0',
                    style: TextStyle(
                      color: radiologyMuted,
                      fontSize: 11,
                    ),
                  ),
                  Spacer(),
                  Text(
                    'Better Brain, Brighter Tomorrow',
                    style: TextStyle(
                      color: Color(0xFF8A94A6),
                      fontSize: 10,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
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
  const _DrawerItem({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: ListTile(
          dense: true,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 2,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          leading: Icon(
            icon,
            color: radiologyBlue,
            size: 22,
          ),
          title: Text(
            label,
            style: const TextStyle(
              color: radiologyNavy,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          trailing: const Icon(
            Icons.chevron_right_rounded,
            color: radiologyMuted,
            size: 21,
          ),
          onTap: onTap,
        ),
      );
}
