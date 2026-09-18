import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../auth/auth_session.dart';
import '../notifications/notifications_api.dart';
import 'patient_profile_api.dart';

const _primary = Color(0xFF5665B8);
const _soft = Color(0xFFE5E8FF);
const _border = Color(0xFFCFD7E8);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);
const _danger = Color(0xFFE94E4E);

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key, required this.session, required this.onLogout, required this.apiClient, required this.onOpenNotificationSettings});

  final AuthSession session;
  final Future<void> Function() onLogout;
  final ApiClient apiClient;
  final VoidCallback onOpenNotificationSettings;

  static void openMyInfo(
    BuildContext context,
    ApiClient client,
  ) =>
      _openPage(context, _PatientProfileDetailPage(apiClient: client));

  static void openConnections(BuildContext context) =>
      _openPage(context, const _ConnectionSettingsPage());

  static void openNotifications(BuildContext context, ApiClient client) =>
      _openPage(
          context,
          Scaffold(
              appBar: AppBar(title: const Text('알림 설정')),
              body: NotificationSettingsContent(apiClient: client)));

  static void openTerms(BuildContext context) =>
      _openPage(context, const _TermsPage());

  static void _openPage(BuildContext context, Widget page) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));

  @override
  Widget build(BuildContext context) {
    final name = session.user.name.trim();
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight - 36),
          child: IntrinsicHeight(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
        InkWell(
          onTap: () => openMyInfo(context, apiClient),
          borderRadius: BorderRadius.circular(24),
          child: Ink(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFF0F1FF), Color(0xFFE4E8FF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(24),
              boxShadow: const [
                BoxShadow(color: Color(0x120F1E61), blurRadius: 12, offset: Offset(0, 4)),
              ],
            ),
            child: Row(children: [
              const CircleAvatar(radius: 29, backgroundColor: Colors.white, child: Icon(Icons.person_outline_rounded, color: _primary, size: 33)),
              const SizedBox(width: 15),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(name.isEmpty ? '환자 회원' : '$name님', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _text, fontSize: 19, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                const Text('patient · 환자', style: TextStyle(color: _muted, fontSize: 13)),
                const SizedBox(height: 7),
                const Text('건강한 일상을 응원합니다.', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _muted, fontSize: 12)),
              ])),
              const SizedBox(width: 6),
              const Icon(Icons.chevron_right_rounded, color: _primary),
            ]),
          ),
        ),
        const SizedBox(height: 16),
        _ProfileMenu(icon: Icons.notifications_outlined, title: '알림 설정', description: '예약, 검사, 복약 알림을 설정할 수 있어요.', onTap: onOpenNotificationSettings),
        _ProfileMenu(icon: Icons.description_outlined, title: '동의 · 약관', description: '이용 약관과 동의 내역을 확인할 수 있어요.', onTap: () => openTerms(context)),
        const Spacer(),
        const SizedBox(height: 20),
        const _CustomerSupportCard(),
        const SizedBox(height: 12),
        TextButton.icon(
          style: TextButton.styleFrom(foregroundColor: _danger, padding: const EdgeInsets.symmetric(vertical: 10)),
          onPressed: () => _confirmLogout(context),
          icon: const Icon(Icons.logout_rounded),
          label: const Text('로그아웃'),
        ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: const Text('로그아웃할까요?'),
      content: const Text('로그인 화면으로 이동합니다.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('취소')),
        FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('로그아웃')),
      ],
    ));
    if (confirmed == true) await onLogout();
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
    padding: const EdgeInsets.only(bottom: 11),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Ink(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: const Color(0xFFDDE2F3)), borderRadius: BorderRadius.circular(18)),
        child: Row(children: [
          Container(width: 42, height: 42, decoration: BoxDecoration(color: _soft, shape: BoxShape.circle), child: Icon(icon, color: _primary, size: 22)),
          const SizedBox(width: 13),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _text, fontWeight: FontWeight.w800)),
            const SizedBox(height: 3),
            Text(description, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12, height: 1.35)),
          ])),
          const Icon(Icons.chevron_right_rounded, color: _muted),
        ]),
      ),
    ),
  );
}

class _CustomerSupportCard extends StatelessWidget {
  const _CustomerSupportCard();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(color: const Color(0xFFF0F4FF), border: Border.all(color: const Color(0xFFDDE6FA)), borderRadius: BorderRadius.circular(17)),
        child: const Row(children: [
          Icon(Icons.support_agent_rounded, color: _primary, size: 25),
          SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('궁금한 점이 있으신가요?', style: TextStyle(color: _text, fontWeight: FontWeight.w800)),
            SizedBox(height: 3),
            Text('고객센터로 문의하시면 빠르게 도와드릴게요.', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _muted, fontSize: 12)),
          ])),
        ]),
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

class _PatientProfileDetailPage extends StatefulWidget {
  const _PatientProfileDetailPage({required this.apiClient});

  final ApiClient apiClient;

  @override
  State<_PatientProfileDetailPage> createState() =>
      _PatientProfileDetailPageState();
}

class _PatientProfileDetailPageState extends State<_PatientProfileDetailPage> {
  late final PatientProfileApi _api = PatientProfileApi(widget.apiClient);
  PatientProfile? _profile;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final profile = await _api.getProfile();
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = '내 정보를 불러오지 못했습니다.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('내 정보')),
        body: RefreshIndicator(
          onRefresh: _load,
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? _ProfileLoadError(message: _error!, onRetry: _load)
                  : _ProfileDetailContent(profile: _profile!),
        ),
      );
}

class _ProfileDetailContent extends StatelessWidget {
  const _ProfileDetailContent({required this.profile});

  final PatientProfile profile;

  @override
  Widget build(BuildContext context) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        children: [
          _ProfileHeader(profile: profile),
          const SizedBox(height: 16),
          _ProfileInformationCard(
            title: '기본 정보',
            children: [
              _ProfileInformationRow(
                  icon: Icons.person_outline_rounded,
                  label: '이름',
                  value: _profileValue(profile.name)),
              _ProfileInformationRow(
                  icon: Icons.cake_outlined,
                  label: '생년월일',
                  value: _formatBirthDate(profile.birthDate)),
              _ProfileInformationRow(
                  icon: Icons.wc_outlined,
                  label: '성별',
                  value: _formatSex(profile.sex),
                  isLast: true),
            ],
          ),
          const SizedBox(height: 12),
          _ProfileInformationCard(
            title: '연락처 정보',
            children: [
              _ProfileInformationRow(
                  icon: Icons.phone_outlined,
                  label: '휴대폰 번호',
                  value: _profileValue(profile.phone)),
              _ProfileInformationRow(
                  icon: Icons.contact_phone_outlined,
                  label: '비상 연락처',
                  value: _profileValue(profile.emergencyContact),
                  isLast: true),
            ],
          ),
          const SizedBox(height: 12),
          _ProfileInformationCard(
            title: '알레르기 정보',
            children: [
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                        color: _soft, borderRadius: BorderRadius.circular(12)),
                    child: const Icon(Icons.health_and_safety_outlined,
                        color: _primary, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _hasValue(profile.allergyInfo)
                          ? profile.allergyInfo!.trim()
                          : '등록된 알레르기 정보가 없습니다.',
                      style: TextStyle(
                        color: _hasValue(profile.allergyInfo)
                            ? _text
                            : _muted,
                        fontSize: 14,
                        height: 1.45,
                        fontWeight: _hasValue(profile.allergyInfo)
                            ? FontWeight.w700
                            : FontWeight.w400,
                      ),
                    ),
                  ),
                ]),
              ),
            ],
          ),
        ],
      );
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.profile});

  final PatientProfile profile;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(22),
        ),
        child: Row(children: [
          const CircleAvatar(
            radius: 31,
            backgroundColor: Colors.white,
            child: Icon(Icons.person_outline_rounded, color: _primary, size: 34),
          ),
          const SizedBox(width: 15),
          Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_profileValue(profile.name),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: _text, fontSize: 20, fontWeight: FontWeight.w800)),
              const SizedBox(height: 5),
              const Text('patient · 환자',
                  style: TextStyle(color: _muted, fontSize: 14)),
            ]),
          ),
        ]),
      );
}

class _ProfileInformationCard extends StatelessWidget {
  const _ProfileInformationCard({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title,
              style: const TextStyle(
                  color: _text, fontSize: 17, fontWeight: FontWeight.w800)),
          const SizedBox(height: 14),
          ...children,
        ]),
      );
}

class _ProfileInformationRow extends StatelessWidget {
  const _ProfileInformationRow({
    required this.icon,
    required this.label,
    required this.value,
    this.isLast = false,
  });

  final IconData icon;
  final String label;
  final String value;
  final bool isLast;

  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.only(bottom: isLast ? 0 : 13),
        margin: EdgeInsets.only(bottom: isLast ? 0 : 13),
        decoration: BoxDecoration(
          border: isLast
              ? null
              : const Border(
                  bottom: BorderSide(color: Color(0xFFF0F1F7)),
                ),
        ),
        child: Row(children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
                color: _soft, borderRadius: BorderRadius.circular(11)),
            child: Icon(icon, color: _primary, size: 19),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(color: _muted, fontSize: 12)),
                  const SizedBox(height: 3),
                  Text(value,
                      style: const TextStyle(
                          color: _text,
                          fontSize: 15,
                          fontWeight: FontWeight.w700)),
                ]),
          ),
        ]),
      );
}

class _ProfileLoadError extends StatelessWidget {
  const _ProfileLoadError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: _border),
                borderRadius: BorderRadius.circular(18)),
            child: Column(children: [
              const Icon(Icons.error_outline_rounded, color: _primary, size: 38),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('다시 시도')),
            ]),
          ),
        ],
      );
}

bool _hasValue(String? value) => value?.trim().isNotEmpty == true;

String _profileValue(String? value) => _hasValue(value) ? value!.trim() : '-';

String _formatBirthDate(DateTime? value) => value == null
    ? '-'
    : '${value.year}.${value.month.toString().padLeft(2, '0')}.${value.day.toString().padLeft(2, '0')}';

String _formatSex(String? value) {
  switch (value?.trim().toUpperCase()) {
    case 'M':
    case 'MALE':
      return '남성';
    case 'F':
    case 'FEMALE':
      return '여성';
    default:
      return _profileValue(value);
  }
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

class NotificationSettingsContent extends StatefulWidget {
  const NotificationSettingsContent({super.key, required this.apiClient});
  final ApiClient apiClient;
  @override
  State<NotificationSettingsContent> createState() => _NotificationSettingsContentState();
}

class _NotificationSettingsContentState extends State<NotificationSettingsContent> {
  late final NotificationsApi _api = NotificationsApi(widget.apiClient);
  NotificationPreferences? _preferences;
  String? _error;
  bool _saving = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async { try { final value = await _api.preferences(); if (mounted) setState(() { _preferences = value; _error = null; }); } catch (_) { if (mounted) setState(() => _error = '알림 설정을 불러오지 못했습니다.'); } }

  Future<void> _change(NotificationCategoryPreference item, bool enabled) async {
    if (item.isRequired && !enabled || _preferences == null) return;
    setState(() { _preferences = _preferences!.toggle(item.category, enabled); _saving = true; });
    try { final saved = await _api.updatePreferences(_preferences!); if (mounted) setState(() { _preferences = saved; _saving = false; }); } catch (_) { if (mounted) setState(() { _error = '알림 설정을 저장하지 못했습니다.'; _saving = false; }); }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(20), children: [
      if (_preferences == null && _error == null) const Center(child: CircularProgressIndicator()),
      if (_error != null) TextButton(onPressed: _load, child: Text('$_error 다시 시도')),
      if (_preferences != null)
      Container(
        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
        child: Column(children: _preferences!.categories.map((entry) => SwitchListTile(
          title: Text(entry.category, style: const TextStyle(color: _text, fontWeight: FontWeight.w600)),
          subtitle: entry.isRequired ? const Text('필수 알림') : null,
          value: entry.isRequired ? true : entry.enabled,
          onChanged: entry.isRequired || _saving ? null : (value) => _change(entry, value),
        )).toList()),
      ),
    ]);
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
    body: Center(child: Padding(
      padding: const EdgeInsets.all(20),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 42),
        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, color: const Color(0xFF8B96E8), size: 40),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center, style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          const Text('연결할 서비스가 등록되면 이곳에서 확인할 수 있습니다.', textAlign: TextAlign.center, style: TextStyle(color: _muted)),
        ]),
      ),
    )),
  );
}
