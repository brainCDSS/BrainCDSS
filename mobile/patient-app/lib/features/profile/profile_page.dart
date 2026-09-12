import 'package:flutter/material.dart';

import '../auth/auth_session.dart';

const _primary = Color(0xFF416AAB);
const _soft = Color(0xFFEAF1FC);
const _border = Color(0xFFDEE6F2);
const _text = Color(0xFF1D3153);
const _muted = Color(0xFF75849A);
const _danger = Color(0xFFE94E4E);

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key, required this.session, required this.onLogout});

  final AuthSession session;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    final name = session.user.name.trim();
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(color: _soft, borderRadius: BorderRadius.circular(20)),
          child: Row(children: [
            const CircleAvatar(radius: 27, backgroundColor: Colors.white, child: Icon(Icons.person_outline_rounded, color: _primary, size: 30)),
            const SizedBox(width: 15),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name.isEmpty ? '환자 회원' : '$name님', style: const TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 4),
              Text(session.user.loginId, style: const TextStyle(color: _muted)),
            ])),
            const Icon(Icons.chevron_right_rounded, color: _primary),
          ]),
        ),
        const SizedBox(height: 18),
        _ProfileMenu(icon: Icons.person_outline, title: '내 정보', description: '기본 정보를 확인할 수 있어요.', onTap: () => _open(context, _MyInfoPage(session: session))),
        _ProfileMenu(icon: Icons.link_outlined, title: '연결 설정', description: '연동 서비스 설정을 관리할 수 있어요.', onTap: () => _open(context, const _ConnectionSettingsPage())),
        _ProfileMenu(icon: Icons.notifications_outlined, title: '알림 설정', description: '알림 수신 항목을 설정할 수 있어요.', onTap: () => _open(context, const _NotificationSettingsPage())),
        _ProfileMenu(icon: Icons.description_outlined, title: '동의 · 약관', description: '이용 약관과 동의 내역을 확인할 수 있어요.', onTap: () => _open(context, const _TermsPage())),
        const SizedBox(height: 14),
        OutlinedButton.icon(
          style: OutlinedButton.styleFrom(foregroundColor: _danger, padding: const EdgeInsets.symmetric(vertical: 14)),
          onPressed: () => _confirmLogout(context),
          icon: const Icon(Icons.logout_rounded),
          label: const Text('로그아웃'),
        ),
      ],
    );
  }

  void _open(BuildContext context, Widget page) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: const Text('로그아웃할까요?'),
      content: const Text('로그인 화면으로 이동합니다.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('취소')),
        FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('로그아웃')),
      ],
    ));
    if (confirmed == true) onLogout();
  }
}

class _ProfileMenu extends StatelessWidget {
  const _ProfileMenu({required this.icon, required this.title, required this.description, required this.onTap});
  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Ink(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(16)),
        child: Row(children: [
          Icon(icon, color: _primary),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
            const SizedBox(height: 3),
            Text(description, style: const TextStyle(color: _muted, fontSize: 12)),
          ])),
          const Icon(Icons.chevron_right_rounded, color: _muted),
        ]),
      ),
    ),
  );
}

class _MyInfoPage extends StatelessWidget {
  const _MyInfoPage({required this.session});
  final AuthSession session;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('내 정보')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      _InfoRow(label: '이름', value: session.user.name),
      _InfoRow(label: '아이디', value: session.user.loginId),
      _InfoRow(label: '이메일', value: session.user.email ?? ''),
    ]),
  );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.all(17),
    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(15)),
    child: Row(children: [
      SizedBox(width: 80, child: Text(label, style: const TextStyle(color: _muted))),
      Expanded(child: Text(value.isEmpty ? '-' : value, style: const TextStyle(color: _text, fontWeight: FontWeight.w700))),
    ]),
  );
}

class _ConnectionSettingsPage extends StatelessWidget {
  const _ConnectionSettingsPage();
  @override
  Widget build(BuildContext context) => const _EmptySettingsPage(title: '연결 설정', icon: Icons.link_off_rounded, message: '연결된 서비스가 없습니다.');
}

class _TermsPage extends StatelessWidget {
  const _TermsPage();
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('동의 · 약관')),
    body: ListView(padding: const EdgeInsets.all(20), children: const [
      _StaticMenu(title: '서비스 이용약관'),
      _StaticMenu(title: '개인정보 처리방침'),
      _StaticMenu(title: '민감정보 처리 동의'),
    ]),
  );
}

class _NotificationSettingsPage extends StatefulWidget {
  const _NotificationSettingsPage();
  @override
  State<_NotificationSettingsPage> createState() => _NotificationSettingsPageState();
}

class _NotificationSettingsPageState extends State<_NotificationSettingsPage> {
  final Map<String, bool> _values = {
    '예약 알림': true,
    '복약 알림': true,
    '검사 결과 알림': true,
    '진료 · 처방 알림': false,
  };

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('알림 설정')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Container(
        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
        child: Column(children: _values.entries.map((entry) => SwitchListTile(
          title: Text(entry.key, style: const TextStyle(color: _text, fontWeight: FontWeight.w600)),
          value: entry.value,
          onChanged: (value) => setState(() => _values[entry.key] = value),
        )).toList()),
      ),
      const SizedBox(height: 14),
      const Text('알림 설정 저장 API가 연결되기 전까지 현재 화면에서만 유지됩니다.', textAlign: TextAlign.center, style: TextStyle(color: _muted, fontSize: 12)),
    ]),
  );
}

class _StaticMenu extends StatelessWidget {
  const _StaticMenu({required this.title});
  final String title;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.all(17),
    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(15)),
    child: Row(children: [Expanded(child: Text(title, style: const TextStyle(color: _text, fontWeight: FontWeight.w600))), const Icon(Icons.chevron_right_rounded, color: _muted)]),
  );
}

class _EmptySettingsPage extends StatelessWidget {
  const _EmptySettingsPage({required this.title, required this.icon, required this.message});
  final String title;
  final IconData icon;
  final String message;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(title)),
    body: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, color: const Color(0xFF8FAFE8), size: 40),
      const SizedBox(height: 14),
      Text(message, style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
      const SizedBox(height: 6),
      const Text('관련 API가 연결되면 이곳에 표시됩니다.', style: TextStyle(color: _muted)),
    ])),
  );
}

