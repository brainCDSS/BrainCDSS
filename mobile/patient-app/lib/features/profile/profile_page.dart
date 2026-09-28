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
  const ProfilePage({
    super.key,
    required this.session,
    required this.onLogout,
    required this.apiClient,
    required this.onOpenNotificationSettings,
    required this.onOpenChatbot,
  });

  final AuthSession session;
  final Future<void> Function() onLogout;
  final ApiClient apiClient;
  final VoidCallback onOpenNotificationSettings;
  final VoidCallback onOpenChatbot;

  static void openMyInfo(
    BuildContext context,
    ApiClient client,
  ) =>
      _openPage(
        context,
        _PatientProfileDetailPage(apiClient: client),
      );

  static void openConnections(BuildContext context) => _openPage(
        context,
        const _ConnectionSettingsPage(),
      );

  static void openNotifications(
    BuildContext context,
    ApiClient client,
  ) =>
      _openPage(
        context,
        Scaffold(
          appBar: AppBar(
            title: const Text('알림 설정'),
          ),
          body: NotificationSettingsContent(
            apiClient: client,
          ),
        ),
      );

  static void openTerms(BuildContext context) => _openPage(
        context,
        const _TermsPage(),
      );

  static void _openPage(
    BuildContext context,
    Widget page,
  ) =>
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => page,
        ),
      );

  @override
  Widget build(BuildContext context) {
    final name = session.user.name.trim();

    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(
          20,
          16,
          20,
          20,
        ),
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: constraints.maxHeight - 36,
          ),
          child: IntrinsicHeight(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                InkWell(
                  onTap: () => openMyInfo(
                    context,
                    apiClient,
                  ),
                  borderRadius: BorderRadius.circular(24),
                  child: Ink(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [
                          Color(0xFFF0F1FF),
                          Color(0xFFE4E8FF),
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x120F1E61),
                          blurRadius: 12,
                          offset: Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        const CircleAvatar(
                          radius: 29,
                          backgroundColor: Colors.white,
                          child: Icon(
                            Icons.person_outline_rounded,
                            color: _primary,
                            size: 33,
                          ),
                        ),
                        const SizedBox(width: 15),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                name.isEmpty ? '환자 회원' : '$name님',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: _text,
                                  fontSize: 19,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                'patient · 환자',
                                style: TextStyle(
                                  color: _muted,
                                  fontSize: 13,
                                ),
                              ),
                              const SizedBox(height: 7),
                              const Text(
                                '건강한 일상을 응원합니다.',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: _muted,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Icon(
                          Icons.chevron_right_rounded,
                          color: _primary,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                _ProfileMenu(
                  icon: Icons.notifications_outlined,
                  title: '알림 설정',
                  description: '예약, 검사, 진료 알림을 설정할 수 있어요.',
                  onTap: onOpenNotificationSettings,
                ),
                _ProfileMenu(
                  icon: Icons.description_outlined,
                  title: '동의 · 약관',
                  description: '이용 약관과 동의 내역을 확인할 수 있어요.',
                  onTap: () => openTerms(context),
                ),
                const Spacer(),
                const SizedBox(height: 20),
                _CustomerSupportCard(onTap: onOpenChatbot),
                const SizedBox(height: 12),
                TextButton.icon(
                  style: TextButton.styleFrom(
                    foregroundColor: _danger,
                    padding: const EdgeInsets.symmetric(
                      vertical: 10,
                    ),
                  ),
                  onPressed: () => _confirmLogout(context),
                  icon: const Icon(
                    Icons.logout_rounded,
                  ),
                  label: const Text(
                    '로그아웃',
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _confirmLogout(
    BuildContext context,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text(
          '로그아웃할까요?',
        ),
        content: const Text(
          '로그인 화면으로 이동합니다.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(
              dialogContext,
              false,
            ),
            child: const Text(
              '취소',
            ),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(
              dialogContext,
              true,
            ),
            child: const Text(
              '로그아웃',
            ),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await onLogout();
    }
  }
}

class _ProfileMenu extends StatelessWidget {
  const _ProfileMenu({
    required this.icon,
    required this.title,
    required this.description,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(
          bottom: 11,
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Ink(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(
                color: const Color(
                  0xFFDDE2F3,
                ),
              ),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: const BoxDecoration(
                    color: _soft,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    icon,
                    color: _primary,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: _text,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        description,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: _muted,
                          fontSize: 12,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: _muted,
                ),
              ],
            ),
          ),
        ),
      );
}

class _CustomerSupportCard extends StatelessWidget {
  const _CustomerSupportCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(17),
        child: Ink(
        padding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
        decoration: BoxDecoration(
          color: const Color(
            0xFFF0F4FF,
          ),
          border: Border.all(
            color: const Color(
              0xFFDDE6FA,
            ),
          ),
          borderRadius: BorderRadius.circular(17),
        ),
        child: const Row(
          children: [
            Icon(
              Icons.support_agent_rounded,
              color: _primary,
              size: 25,
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '궁금한 점이 있으신가요?',
                    style: TextStyle(
                      color: _text,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  SizedBox(height: 3),
                  Text(
                    '고객센터로 문의하시면 빠르게 도와드릴게요.',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: _muted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: _primary,
            ),
          ],
        ),
      ),
      );
}

class _PatientProfileDetailPage extends StatefulWidget {
  const _PatientProfileDetailPage({
    required this.apiClient,
  });

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
        appBar: AppBar(
          title: const Text(
            '내 정보',
          ),
        ),
        body: RefreshIndicator(
          onRefresh: _load,
          child: _loading
              ? const Center(
                  child: CircularProgressIndicator(),
                )
              : _error != null
                  ? _ProfileLoadError(
                      message: _error!,
                      onRetry: _load,
                    )
                  : _ProfileDetailContent(
                      profile: _profile!,
                    ),
        ),
      );
}

class _ProfileDetailContent extends StatelessWidget {
  const _ProfileDetailContent({
    required this.profile,
  });

  final PatientProfile profile;

  @override
  Widget build(BuildContext context) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(
          20,
          16,
          20,
          28,
        ),
        children: [
          _ProfileHeader(
            profile: profile,
          ),
          const SizedBox(height: 16),
          _ProfileInformationCard(
            title: '기본 정보',
            children: [
              _ProfileInformationRow(
                icon: Icons.person_outline_rounded,
                label: '이름',
                value: _profileValue(
                  profile.name,
                ),
              ),
              _ProfileInformationRow(
                icon: Icons.cake_outlined,
                label: '생년월일',
                value: _formatBirthDate(
                  profile.birthDate,
                ),
              ),
              _ProfileInformationRow(
                icon: Icons.wc_outlined,
                label: '성별',
                value: _formatSex(
                  profile.sex,
                ),
                isLast: true,
              ),
            ],
          ),
          const SizedBox(height: 12),
          _ProfileInformationCard(
            title: '연락처 정보',
            children: [
              _ProfileInformationRow(
                icon: Icons.phone_outlined,
                label: '휴대폰 번호',
                value: _profileValue(
                  profile.phone,
                ),
              ),
              _ProfileInformationRow(
                icon: Icons.contact_phone_outlined,
                label: '비상 연락처',
                value: _profileValue(
                  profile.emergencyContact,
                ),
                isLast: true,
              ),
            ],
          ),
          const SizedBox(height: 12),
          _ProfileInformationCard(
            title: '알레르기 정보',
            children: [
              Padding(
                padding: const EdgeInsets.only(
                  top: 4,
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: _soft,
                        borderRadius: BorderRadius.circular(
                          12,
                        ),
                      ),
                      child: const Icon(
                        Icons.health_and_safety_outlined,
                        color: _primary,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _hasValue(
                          profile.allergyInfo,
                        )
                            ? profile.allergyInfo!.trim()
                            : '등록된 알레르기 정보가 없습니다.',
                        style: TextStyle(
                          color: _hasValue(
                            profile.allergyInfo,
                          )
                              ? _text
                              : _muted,
                          fontSize: 14,
                          height: 1.45,
                          fontWeight: _hasValue(
                            profile.allergyInfo,
                          )
                              ? FontWeight.w700
                              : FontWeight.w400,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      );
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({
    required this.profile,
  });

  final PatientProfile profile;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(
          18,
        ),
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(
            22,
          ),
        ),
        child: Row(
          children: [
            const CircleAvatar(
              radius: 31,
              backgroundColor: Colors.white,
              child: Icon(
                Icons.person_outline_rounded,
                color: _primary,
                size: 34,
              ),
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _profileValue(
                      profile.name,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: _text,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    'patient · 환자',
                    style: TextStyle(
                      color: _muted,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ProfileInformationCard extends StatelessWidget {
  const _ProfileInformationCard({
    required this.title,
    required this.children,
  });

  final String title;

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(
          18,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(
            color: _border,
          ),
          borderRadius: BorderRadius.circular(
            20,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: _text,
                fontSize: 17,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 14),
            ...children,
          ],
        ),
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
        padding: EdgeInsets.only(
          bottom: isLast ? 0 : 13,
        ),
        margin: EdgeInsets.only(
          bottom: isLast ? 0 : 13,
        ),
        decoration: BoxDecoration(
          border: isLast
              ? null
              : const Border(
                  bottom: BorderSide(
                    color: Color(
                      0xFFF0F1F7,
                    ),
                  ),
                ),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: _soft,
                borderRadius: BorderRadius.circular(
                  11,
                ),
              ),
              child: Icon(
                icon,
                color: _primary,
                size: 19,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      color: _muted,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    value,
                    style: const TextStyle(
                      color: _text,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ProfileLoadError extends StatelessWidget {
  const _ProfileLoadError({
    required this.message,
    required this.onRetry,
  });

  final String message;

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(
          20,
        ),
        children: [
          Container(
            padding: const EdgeInsets.all(
              24,
            ),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(
                color: _border,
              ),
              borderRadius: BorderRadius.circular(
                18,
              ),
            ),
            child: Column(
              children: [
                const Icon(
                  Icons.error_outline_rounded,
                  color: _primary,
                  size: 38,
                ),
                const SizedBox(height: 12),
                Text(
                  message,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(
                    Icons.refresh_rounded,
                  ),
                  label: const Text(
                    '다시 시도',
                  ),
                ),
              ],
            ),
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
      return _profileValue(
        value,
      );
  }
}

class _ConnectionSettingsPage extends StatelessWidget {
  const _ConnectionSettingsPage();

  @override
  Widget build(BuildContext context) => const _EmptySettingsPage(
        title: '연결 설정',
        icon: Icons.link_off_rounded,
        message: '연결된 서비스가 없습니다.',
      );
}

class _TermsPage extends StatelessWidget {
  const _TermsPage();

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text(
            '동의 · 약관',
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.all(
            20,
          ),
          children: const [
            _StaticMenu(
              title: '서비스 이용약관',
            ),
            _StaticMenu(
              title: '개인정보 처리방침',
            ),
            _StaticMenu(
              title: '민감정보 처리 동의',
            ),
          ],
        ),
      );
}

///
/// 서버에서 내려오는 알림 category를
/// 환자가 이해하기 쉬운 한글 이름으로 변환한다.
/// API 값 자체는 변경하지 않는다.
///
String _notificationCategoryLabel(
  String category,
) {
  switch (category.trim().toUpperCase()) {
    case 'EMERGENCY':
      return '중요 건강 알림';

    case 'CONSULTATION':
      return '진료 알림';

    case 'PRESCRIPTION':
      return '처방 알림';

    case 'MEDICATION_SAFETY':
      return '약물 안전 알림';

    case 'IMAGING':
      return '검사 결과 알림';

    case 'AI_ANALYSIS':
      return 'AI 분석 결과 알림';

    case 'APPOINTMENT':
      return '예약 알림';

    case 'SYSTEM':
      return '서비스 알림';

    case 'CRITICAL':
      return '긴급 알림';

    default:
      return category;
  }
}

///
/// 알림 종류별 안내 문구.
///
String _notificationCategoryDescription(
  String category,
) {
  switch (category.trim().toUpperCase()) {
    case 'EMERGENCY':
      return '긴급하거나 중요한 건강 관련 안내를 받아요.';

    case 'CONSULTATION':
      return '진료와 관련된 주요 안내를 받아요.';

    case 'PRESCRIPTION':
      return '새 처방과 처방 변경 사항을 알려드려요.';

    case 'MEDICATION_SAFETY':
      return '약물 복용 시 주의가 필요한 사항을 알려드려요.';

    case 'IMAGING':
      return '검사 일정과 검사 결과 등록 안내를 받아요.';

    case 'AI_ANALYSIS':
      return 'AI 분석 결과가 등록되면 알려드려요.';

    case 'APPOINTMENT':
      return '예약 일정과 변경 사항을 알려드려요.';

    case 'SYSTEM':
      return '서비스 이용에 필요한 중요한 안내를 받아요.';

    case 'CRITICAL':
      return '안전과 관련된 긴급 알림은 항상 수신됩니다.';

    default:
      return '알림 수신 여부를 설정할 수 있어요.';
  }
}

///
/// 알림 category별 아이콘.
///
IconData _notificationCategoryIcon(
  String category,
) {
  switch (category.trim().toUpperCase()) {
    case 'EMERGENCY':
      return Icons.health_and_safety_outlined;

    case 'CONSULTATION':
      return Icons.medical_services_outlined;

    case 'PRESCRIPTION':
      return Icons.medication_outlined;

    case 'MEDICATION_SAFETY':
      return Icons.health_and_safety_outlined;

    case 'IMAGING':
      return Icons.monitor_heart_outlined;

    case 'AI_ANALYSIS':
      return Icons.auto_awesome_outlined;

    case 'APPOINTMENT':
      return Icons.calendar_month_outlined;

    case 'SYSTEM':
      return Icons.info_outline_rounded;

    case 'CRITICAL':
      return Icons.warning_amber_rounded;

    default:
      return Icons.notifications_outlined;
  }
}

class NotificationSettingsContent extends StatefulWidget {
  const NotificationSettingsContent({
    super.key,
    required this.apiClient,
  });

  final ApiClient apiClient;

  @override
  State<NotificationSettingsContent> createState() =>
      _NotificationSettingsContentState();
}

class _NotificationSettingsContentState
    extends State<NotificationSettingsContent> {
  late final NotificationsApi _api = NotificationsApi(
    widget.apiClient,
  );

  NotificationPreferences? _preferences;

  String? _error;

  bool _saving = false;

  @override
  void initState() {
    super.initState();

    _load();
  }

  Future<void> _load() async {
    try {
      final value = await _api.preferences();

      if (!mounted) return;

      setState(() {
        _preferences = value;
        _error = null;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _error = '알림 설정을 불러오지 못했습니다.';
      });
    }
  }

  Future<void> _change(
    NotificationCategoryPreference item,
    bool enabled,
  ) async {
    if ((item.isRequired && !enabled) || _preferences == null) {
      return;
    }

    setState(() {
      _preferences = _preferences!.toggle(
        item.category,
        enabled,
      );

      _saving = true;

      _error = null;
    });

    try {
      final saved = await _api.updatePreferences(
        _preferences!,
      );

      if (!mounted) return;

      setState(() {
        _preferences = saved;
        _saving = false;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _error = '알림 설정을 저장하지 못했습니다.';
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_preferences == null && _error == null) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_preferences == null && _error != null) {
      return _NotificationSettingsError(
        message: _error!,
        onRetry: _load,
      );
    }

    final categories = _preferences!.categories;
    final requiredCategories = categories.where((item) => item.isRequired).toList();
    final healthCategories = categories
        .where((item) =>
            !item.isRequired &&
            const {
              'EMERGENCY',
              'CONSULTATION',
              'PRESCRIPTION',
              'MEDICATION_SAFETY',
              'IMAGING',
              'AI_ANALYSIS',
            }.contains(item.category.toUpperCase()))
        .toList();
    final serviceCategories = categories
        .where((item) =>
            !item.isRequired && !healthCategories.contains(item))
        .toList();

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(
        20,
        18,
        20,
        28,
      ),
      children: [
        const Text(
          '받고 싶은 알림을 선택해 주세요.',
          style: TextStyle(
            color: _text,
            fontSize: 18,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          '중요 안내 및 필수 알림은 해제할 수 없습니다.',
          style: TextStyle(
            color: _muted,
            fontSize: 13,
            height: 1.4,
          ),
        ),
        const SizedBox(height: 18),
        if (_error != null)
          Container(
            margin: const EdgeInsets.only(
              bottom: 12,
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 11,
            ),
            decoration: BoxDecoration(
              color: const Color(
                0xFFFFF3F3,
              ),
              border: Border.all(
                color: const Color(
                  0xFFFFD9D9,
                ),
              ),
              borderRadius: BorderRadius.circular(
                14,
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.error_outline_rounded,
                  color: _danger,
                  size: 20,
                ),
                const SizedBox(
                  width: 8,
                ),
                Expanded(
                  child: Text(
                    _error!,
                    style: const TextStyle(
                      color: _danger,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),
        if (healthCategories.isNotEmpty)
          _NotificationSettingsGroup(
            title: '건강 및 진료',
            description: '건강 상태와 진료·검사·처방 관련 알림을 설정해요.',
            items: healthCategories,
            saving: _saving,
            onChanged: _change,
          ),
        if (serviceCategories.isNotEmpty) ...[
          const SizedBox(height: 18),
          _NotificationSettingsGroup(
            title: '예약 및 서비스',
            description: '예약 일정과 서비스 이용 관련 알림을 설정해요.',
            items: serviceCategories,
            saving: _saving,
            onChanged: _change,
          ),
        ],
        if (requiredCategories.isNotEmpty) ...[
          const SizedBox(height: 18),
          _NotificationSettingsGroup(
            title: '필수 알림',
            description: '긴급 알림은 안전을 위해 항상 켜져 있어요.',
            items: requiredCategories,
            saving: _saving,
            onChanged: _change,
          ),
        ],
        const SizedBox(height: 14),
        const Padding(
          padding: EdgeInsets.symmetric(
            horizontal: 4,
          ),
          child: Text(
            '앱 알림이 오지 않는 경우 휴대폰 설정에서 호닥의 알림 권한이 허용되어 있는지 확인해 주세요.',
            style: TextStyle(
              color: _muted,
              fontSize: 12,
              height: 1.45,
            ),
          ),
        ),
      ],
    );
  }
}

class _NotificationSettingsGroup extends StatelessWidget {
  const _NotificationSettingsGroup({
    required this.title,
    required this.description,
    required this.items,
    required this.saving,
    required this.onChanged,
  });

  final String title;
  final String description;
  final List<NotificationCategoryPreference> items;
  final bool saving;
  final void Function(NotificationCategoryPreference, bool) onChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: _text,
              fontSize: 15,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            description,
            style: const TextStyle(
              color: _muted,
              fontSize: 12,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 9),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: _border),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              children: [
                for (int index = 0; index < items.length; index++)
                  _NotificationSettingTile(
                    item: items[index],
                    isLast: index == items.length - 1,
                    saving: saving,
                    onChanged: (value) => onChanged(items[index], value),
                  ),
              ],
            ),
          ),
        ],
      );
}

class _NotificationSettingTile extends StatelessWidget {
  const _NotificationSettingTile({
    required this.item,
    required this.isLast,
    required this.saving,
    required this.onChanged,
  });

  final NotificationCategoryPreference item;

  final bool isLast;

  final bool saving;

  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final required = item.isRequired;

    final enabled = required ? true : item.enabled;

    return Container(
      padding: const EdgeInsets.fromLTRB(
        16,
        15,
        8,
        15,
      ),
      decoration: BoxDecoration(
        border: isLast
            ? null
            : const Border(
                bottom: BorderSide(
                  color: Color(
                    0xFFF0F1F7,
                  ),
                ),
              ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: _soft,
              borderRadius: BorderRadius.circular(
                13,
              ),
            ),
            child: Icon(
              _notificationCategoryIcon(
                item.category,
              ),
              color: _primary,
              size: 22,
            ),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        _notificationCategoryLabel(
                          item.category,
                        ),
                        style: const TextStyle(
                          color: _text,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (required) ...[
                      const SizedBox(
                        width: 6,
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 7,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(
                            0xFFF0F2FF,
                          ),
                          borderRadius: BorderRadius.circular(
                            8,
                          ),
                        ),
                        child: const Text(
                          '필수',
                          style: TextStyle(
                            color: _primary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(
                  height: 5,
                ),
                Text(
                  _notificationCategoryDescription(
                    item.category,
                  ),
                  style: const TextStyle(
                    color: _muted,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Switch(
            value: enabled,
            onChanged: required || saving ? null : onChanged,
            activeColor: required ? _primary : null,
            activeTrackColor: required ? const Color(0xFFBFD2EE) : null,
          ),
        ],
      ),
    );
  }
}

class _NotificationSettingsError extends StatelessWidget {
  const _NotificationSettingsError({
    required this.message,
    required this.onRetry,
  });

  final String message;

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(
          20,
        ),
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 24,
              vertical: 32,
            ),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(
                color: _border,
              ),
              borderRadius: BorderRadius.circular(
                18,
              ),
            ),
            child: Column(
              children: [
                const Icon(
                  Icons.notifications_off_outlined,
                  color: _primary,
                  size: 40,
                ),
                const SizedBox(
                  height: 12,
                ),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: _text,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(
                  height: 14,
                ),
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(
                    Icons.refresh_rounded,
                  ),
                  label: const Text(
                    '다시 시도',
                  ),
                ),
              ],
            ),
          ),
        ],
      );
}

class _StaticMenu extends StatelessWidget {
  const _StaticMenu({
    required this.title,
  });

  final String title;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(
          bottom: 10,
        ),
        padding: const EdgeInsets.all(
          17,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(
            color: _border,
          ),
          borderRadius: BorderRadius.circular(
            15,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  color: _text,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const Icon(
              Icons.chevron_right_rounded,
              color: _muted,
            ),
          ],
        ),
      );
}

class _EmptySettingsPage extends StatelessWidget {
  const _EmptySettingsPage({
    required this.title,
    required this.icon,
    required this.message,
  });

  final String title;
  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(
            title,
          ),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(
              20,
            ),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 42,
              ),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(
                  color: _border,
                ),
                borderRadius: BorderRadius.circular(
                  18,
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    icon,
                    color: const Color(
                      0xFF8B96E8,
                    ),
                    size: 40,
                  ),
                  const SizedBox(
                    height: 14,
                  ),
                  Text(
                    message,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: _text,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(
                    height: 6,
                  ),
                  const Text(
                    '연결할 서비스가 등록되면 이곳에서 확인할 수 있습니다.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: _muted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
