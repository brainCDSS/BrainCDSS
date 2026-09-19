import 'package:flutter/material.dart';

import '../auth/clinician_session.dart';
import '../radiology/widgets/radiology_ui.dart';

class RadiologyProfilePage extends StatelessWidget {
  const RadiologyProfilePage({
    super.key,
    required this.user,
    required this.onLogout,
  });

  final ClinicianUser user;
  final VoidCallback onLogout;

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('로그아웃하시겠습니까?'),
        content: const Text('현재 로그인 세션이 종료됩니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('로그아웃'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      onLogout();
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          _ProfileHeader(user: user),
          const SizedBox(height: 22),
          const RadiologySectionTitle(title: '설정'),
          const SizedBox(height: 10),
          const _ProfileMenuCard(
            icon: Icons.notifications_none_rounded,
            title: '알림 설정',
            subtitle: '업무 알림 수신 방식을 관리합니다.',
          ),
          const SizedBox(height: 10),
          const _ProfileMenuCard(
            icon: Icons.settings_outlined,
            title: '앱 설정',
            subtitle: '앱 환경과 표시 설정을 확인합니다.',
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () => _confirmLogout(context),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFFB34B58),
              side: const BorderSide(color: Color(0xFFF1CDD1)),
              minimumSize: const Size.fromHeight(52),
            ),
            icon: const Icon(Icons.logout_rounded),
            label: const Text('로그아웃'),
          ),
        ],
      );
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.user});

  final ClinicianUser user;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            CircleAvatar(
              radius: 31,
              backgroundColor: const Color(0xFFEAF2FF),
              child: const Icon(
                Icons.person_rounded,
                size: 34,
                color: radiologyBlue,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    user.name.isEmpty ? '이름 정보 없음' : user.name,
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    user.role.name.isEmpty ? '영상의학과' : user.role.name,
                    style: const TextStyle(
                      color: radiologyBlue,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    user.loginId.isNotEmpty ? user.loginId : user.email,
                    style: const TextStyle(color: radiologyMuted, fontSize: 13),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ProfileMenuCard extends StatelessWidget {
  const _ProfileMenuCard({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: const Color(0xFFEAF2FF),
                borderRadius: BorderRadius.circular(13),
              ),
              child: Icon(icon, color: radiologyBlue),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(color: radiologyMuted, fontSize: 13),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
          ],
        ),
      );
}
