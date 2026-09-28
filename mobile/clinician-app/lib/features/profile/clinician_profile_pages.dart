import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../auth/clinician_session.dart';
import '../radiology/widgets/radiology_ui.dart';

class ClinicianProfilePage extends StatelessWidget {
  const ClinicianProfilePage({
    super.key,
    required this.user,
    required this.onLogout,
    required this.onOpenNotificationSettings,
    required this.onOpenProfileDetails,
  });

  final ClinicianUser user;
  final VoidCallback onLogout;
  final VoidCallback onOpenNotificationSettings;
  final VoidCallback onOpenProfileDetails;

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
          _ClinicianProfileHeader(user: user),
          const SizedBox(height: 22),
          const RadiologySectionTitle(title: '설정'),
          const SizedBox(height: 10),
          _ProfileMenuCard(
            icon: Icons.notifications_none_rounded,
            title: '알림 설정',
            subtitle: '업무 알림 수신 방식을 관리합니다.',
            onTap: onOpenNotificationSettings,
          ),
          const SizedBox(height: 10),
          _ProfileMenuCard(
            icon: Icons.person_outline_rounded,
            title: '내 정보 수정',
            subtitle: '의료진 기본 정보를 확인합니다.',
            onTap: onOpenProfileDetails,
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () => _confirmLogout(context),
            style: OutlinedButton.styleFrom(
              foregroundColor: radiologyDanger,
              side: const BorderSide(
                color: Color(0xFFF1CDD1),
              ),
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
            icon: const Icon(Icons.logout_rounded),
            label: const Text('로그아웃'),
          ),
        ],
      );
}

/// 의료진 공통 알림 설정
///
/// 로그인한 사용자의 notification preference API를 사용한다.
/// RADIOLOGY / NEUROLOGIST가 동일 페이지를 사용한다.
class ClinicianNotificationSettingsPage extends StatefulWidget {
  const ClinicianNotificationSettingsPage({
    super.key,
    required this.apiClient,
  });

  final ClinicianApiClient apiClient;

  @override
  State<ClinicianNotificationSettingsPage> createState() =>
      _ClinicianNotificationSettingsPageState();
}

class _ClinicianNotificationSettingsPageState
    extends State<ClinicianNotificationSettingsPage> {
  Map<String, _NotificationPreference> _preferences = const {};
  final Set<String> _savingCategories = <String>{};
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  Future<void> _loadPreferences() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final response = await widget.apiClient.get(
        '/api/v1/notification-preferences',
      );
      if (mounted) {
        setState(() {
          _preferences = _preferencesFromResponse(response);
          _isLoading = false;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() {
          _errorMessage = error.message;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _errorMessage = '알림 설정을 불러오지 못했습니다.';
          _isLoading = false;
        });
      }
    }
  }

  Map<String, _NotificationPreference> _preferencesFromResponse(
    Map<String, dynamic> response,
  ) {
    final preferences = <String, _NotificationPreference>{};
    for (final item in response['categories'] as List? ?? const []) {
      if (item is! Map) {
        continue;
      }
      final json = Map<String, dynamic>.from(item);
      final category = json['category']?.toString() ?? '';
      if (!_notificationCategoryByCode.containsKey(category)) {
        continue;
      }
      preferences[category] = _NotificationPreference(
        enabled: json['enabled'] == true,
        required: json['required'] == true,
      );
    }
    return preferences;
  }

  Future<void> _updatePreference(
    String category,
    _NotificationPreference preference,
    bool enabled,
  ) async {
    if (preference.required || _savingCategories.contains(category)) {
      return;
    }

    final previousPreferences = _preferences;
    setState(() {
      _savingCategories.add(category);
      _preferences = {
        ..._preferences,
        category: preference.copyWith(enabled: enabled),
      };
    });

    try {
      final response = await widget.apiClient.patch(
        '/api/v1/notification-preferences',
        body: {
          'categories': {category: enabled},
        },
      );
      if (mounted) {
        setState(() {
          _preferences = _preferencesFromResponse(response);
          _savingCategories.remove(category);
        });
      }
    } on ClinicianApiException catch (error) {
      _restorePreference(category, previousPreferences, error.message);
    } catch (_) {
      _restorePreference(
        category,
        previousPreferences,
        '알림 설정을 변경하지 못했습니다.',
      );
    }
  }

  void _restorePreference(
    String category,
    Map<String, _NotificationPreference> previousPreferences,
    String message,
  ) {
    if (!mounted) {
      return;
    }
    setState(() {
      _preferences = previousPreferences;
      _savingCategories.remove(category);
    });
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '업무 알림'),
          const SizedBox(height: 10),
          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_errorMessage != null)
            RadiologyInfoCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _errorMessage!,
                    style: const TextStyle(color: radiologyMuted),
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: _loadPreferences,
                    child: const Text('다시 시도'),
                  ),
                ],
              ),
            )
          else if (_preferences.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.notifications_none_rounded,
              message: '표시할 알림 설정이 없습니다.',
            )
          else ...[
            for (final definition in _notificationCategoryDefinitions)
              if (_preferences[definition.category] case final preference?) ...[
                _NotificationSettingCard(
                  icon: definition.icon,
                  title: definition.title,
                  subtitle: definition.subtitle,
                  value: preference.enabled,
                  onChanged: preference.required ||
                          _savingCategories.contains(definition.category)
                      ? null
                      : (value) => _updatePreference(
                            definition.category,
                            preference,
                            value,
                          ),
                ),
                const SizedBox(height: 11),
              ],
            const Padding(
              padding: EdgeInsets.fromLTRB(4, 7, 4, 0),
              child: Text(
                '중요 알림은 설정과 관계없이 표시될 수 있습니다.',
                style: TextStyle(color: radiologyMuted, fontSize: 12),
              ),
            ),
          ],
        ],
      );
}

class _NotificationPreference {
  const _NotificationPreference({
    required this.enabled,
    required this.required,
  });

  final bool enabled;
  final bool required;

  _NotificationPreference copyWith({bool? enabled}) =>
      _NotificationPreference(
        enabled: enabled ?? this.enabled,
        required: required,
      );
}

class _NotificationCategoryDefinition {
  const _NotificationCategoryDefinition({
    required this.category,
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final String category;
  final IconData icon;
  final String title;
  final String subtitle;
}

const _notificationCategoryDefinitions = <_NotificationCategoryDefinition>[
  _NotificationCategoryDefinition(
    category: 'EMERGENCY',
    icon: Icons.emergency_rounded,
    title: '응급 알림',
    subtitle: '긴급 환자 및 우선 처리 알림을 받습니다.',
  ),
  _NotificationCategoryDefinition(
    category: 'CONSULTATION',
    icon: Icons.forum_outlined,
    title: '협진 알림',
    subtitle: '협진 요청과 의견 회신 알림을 받습니다.',
  ),
  _NotificationCategoryDefinition(
    category: 'IMAGING',
    icon: Icons.image_search_outlined,
    title: '영상·검사 알림',
    subtitle: '영상 검사 및 판독 관련 알림을 받습니다.',
  ),
  _NotificationCategoryDefinition(
    category: 'AI_ANALYSIS',
    icon: Icons.auto_awesome_outlined,
    title: 'AI 분석 알림',
    subtitle: 'AI 분석 요청과 결과 알림을 받습니다.',
  ),
  _NotificationCategoryDefinition(
    category: 'APPOINTMENT',
    icon: Icons.calendar_month_outlined,
    title: '예약 알림',
    subtitle: '예약 일정과 변경 관련 알림을 받습니다.',
  ),
  _NotificationCategoryDefinition(
    category: 'SYSTEM',
    icon: Icons.settings_outlined,
    title: '시스템 알림',
    subtitle: '서비스 운영 및 시스템 안내를 받습니다.',
  ),
];

final _notificationCategoryByCode = <String, _NotificationCategoryDefinition>{
  for (final definition in _notificationCategoryDefinitions)
    definition.category: definition,
};

class LegacyClinicianNotificationSettingsPage extends StatefulWidget {
  const LegacyClinicianNotificationSettingsPage({
    super.key,
  });

  @override
  State<LegacyClinicianNotificationSettingsPage> createState() =>
      _LegacyClinicianNotificationSettingsPageState();
}

class _LegacyClinicianNotificationSettingsPageState
    extends State<LegacyClinicianNotificationSettingsPage> {
  bool _emergencyEnabled = true;
  bool _consultationEnabled = true;
  bool _imagingEnabled = true;
  bool _aiAnalysisEnabled = true;
  bool _appointmentEnabled = true;
  bool _systemEnabled = true;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(
            title: '업무 알림',
          ),
          const SizedBox(height: 10),
          _NotificationSettingCard(
            icon: Icons.emergency_rounded,
            title: '응급 알림',
            subtitle: '긴급 환자 및 우선 처리 알림을 받습니다.',
            value: _emergencyEnabled,
            onChanged: (value) {
              setState(() {
                _emergencyEnabled = value;
              });
            },
          ),
          const SizedBox(height: 11),
          _NotificationSettingCard(
            icon: Icons.forum_outlined,
            title: '협진 알림',
            subtitle: '협진 요청과 의견 회신 알림을 받습니다.',
            value: _consultationEnabled,
            onChanged: (value) {
              setState(() {
                _consultationEnabled = value;
              });
            },
          ),
          const SizedBox(height: 11),
          _NotificationSettingCard(
            icon: Icons.image_search_outlined,
            title: '영상·검사 알림',
            subtitle: '영상 검사 및 판독 관련 알림을 받습니다.',
            value: _imagingEnabled,
            onChanged: (value) {
              setState(() {
                _imagingEnabled = value;
              });
            },
          ),
          const SizedBox(height: 11),
          _NotificationSettingCard(
            icon: Icons.auto_awesome_outlined,
            title: 'AI 분석 알림',
            subtitle: 'AI 분석 요청과 결과 알림을 받습니다.',
            value: _aiAnalysisEnabled,
            onChanged: (value) {
              setState(() {
                _aiAnalysisEnabled = value;
              });
            },
          ),
          const SizedBox(height: 11),
          _NotificationSettingCard(
            icon: Icons.calendar_month_outlined,
            title: '예약 알림',
            subtitle: '예약 일정과 변경 관련 알림을 받습니다.',
            value: _appointmentEnabled,
            onChanged: (value) {
              setState(() {
                _appointmentEnabled = value;
              });
            },
          ),
          const SizedBox(height: 11),
          _NotificationSettingCard(
            icon: Icons.settings_outlined,
            title: '시스템 알림',
            subtitle: '서비스 운영 및 시스템 안내를 받습니다.',
            value: _systemEnabled,
            onChanged: (value) {
              setState(() {
                _systemEnabled = value;
              });
            },
          ),
          const SizedBox(height: 18),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 4),
            child: Text(
              '중요 알림은 설정과 관계없이 표시될 수 있습니다.',
              style: TextStyle(
                color: radiologyMuted,
                fontSize: 12,
              ),
            ),
          ),
        ],
      );
}

/// 의료진 공통 내 정보 화면
class ClinicianProfileDetailsPage extends StatelessWidget {
  const ClinicianProfileDetailsPage({
    super.key,
    required this.user,
  });

  final ClinicianUser user;

  String get _department =>
      user.role.name.isNotEmpty ? user.role.name : user.role.code;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(
            title: '내 정보',
          ),
          const SizedBox(height: 8),
          const Text(
            '현재 로그인한 의료진의 계정 정보를 확인할 수 있습니다.',
            style: TextStyle(
              color: radiologyMuted,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 14),
          RadiologyInfoCard(
            child: Column(
              children: [
                _ProfileInfoRow(
                  label: '이름',
                  value: user.name.isEmpty ? '정보 없음' : user.name,
                ),
                const Divider(
                  height: 24,
                  color: radiologyBorder,
                ),
                _ProfileInfoRow(
                  label: '이메일',
                  value: user.email.isEmpty ? '정보 없음' : user.email,
                ),
                const Divider(
                  height: 24,
                  color: radiologyBorder,
                ),
                _ProfileInfoRow(
                  label: '진료과',
                  value: _department.isEmpty ? '정보 없음' : _department,
                ),
                const Divider(
                  height: 24,
                  color: radiologyBorder,
                ),
                _ProfileInfoRow(
                  label: '아이디',
                  value: user.loginId.isEmpty ? '정보 없음' : user.loginId,
                ),
              ],
            ),
          ),
        ],
      );
}

class _NotificationSettingCard extends StatelessWidget {
  const _NotificationSettingCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(
          children: [
            _SettingIcon(
              icon: icon,
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
                    style: const TextStyle(
                      color: radiologyMuted,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Switch(
              value: value,
              onChanged: onChanged,
            ),
          ],
        ),
      );
}

class _ClinicianProfileHeader extends StatelessWidget {
  const _ClinicianProfileHeader({
    required this.user,
  });

  final ClinicianUser user;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const CircleAvatar(
              radius: 31,
              backgroundColor: Color(0xFFEAF2FF),
              child: Icon(
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
                    user.role.name.isNotEmpty ? user.role.name : user.role.code,
                    style: const TextStyle(
                      color: radiologyBlue,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    user.loginId.isNotEmpty ? user.loginId : user.email,
                    style: const TextStyle(
                      color: radiologyMuted,
                      fontSize: 13,
                    ),
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
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: EdgeInsets.zero,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                _SettingIcon(
                  icon: icon,
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
                        style: const TextStyle(
                          color: radiologyMuted,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: radiologyMuted,
                ),
              ],
            ),
          ),
        ),
      );
}

class _SettingIcon extends StatelessWidget {
  const _SettingIcon({
    required this.icon,
  });

  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: const Color(0xFFEAF2FF),
          borderRadius: BorderRadius.circular(13),
        ),
        child: Icon(
          icon,
          color: radiologyBlue,
        ),
      );
}

class _ProfileInfoRow extends StatelessWidget {
  const _ProfileInfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: const TextStyle(
                color: radiologyMuted,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: radiologyNavy,
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.right,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      );
}
