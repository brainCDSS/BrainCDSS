import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../auth/clinician_session.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'neurology_imaging_pages.dart';

class NeurologyEmergencyPage extends StatelessWidget {
  const NeurologyEmergencyPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
    children: [
      const RadiologySectionTitle(title: '응급 Worklist'),
      const SizedBox(height: 8),
      const Text('본인에게 배정된 긴급·응급 환자를 확인합니다.', style: TextStyle(color: radiologyMuted, fontSize: 13)),
      const SizedBox(height: 16),
      const RadiologyEmptyState(
        icon: Icons.emergency_outlined,
        message: '응급 Worklist는 접근 범위 보완 후 연결될 예정입니다.',
      ),
    ],
  );
}

class NeurologyHomePage extends StatefulWidget {
  const NeurologyHomePage({
    super.key,
    required this.apiClient,
    required this.onSelectTab,
    required this.onOpenClinicalRecords,
  });

  final ClinicianApiClient apiClient;
  final ValueChanged<int> onSelectTab;
  final VoidCallback onOpenClinicalRecords;

  @override
  State<NeurologyHomePage> createState() => _NeurologyHomePageState();
}

class _NeurologyHomePageState extends State<NeurologyHomePage> {
  List<_RecentStudy> _recentStudies = const [];
  bool _loadingStudies = true;
  String? _studiesError;

  @override
  void initState() {
    super.initState();
    _loadRecentStudies();
  }

  Future<void> _loadRecentStudies() async {
    setState(() {
      _loadingStudies = true;
      _studiesError = null;
    });
    try {
      final response = await widget.apiClient.get('/api/v1/imaging-studies');
      final studies = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => _RecentStudy.fromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) {
        setState(() => _recentStudies = studies);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _studiesError = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _studiesError = '최근 검사 목록을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _loadingStudies = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '오늘 업무'),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.75,
            children: [
              const _SummaryCard(
                icon: Icons.emergency_outlined,
                label: '응급 환자',
                value: '-',
                caption: '연동 대기',
              ),
              _SummaryCard(
                icon: Icons.image_search_outlined,
                label: '확인할 검사',
                value: _loadingStudies ? '-' : '${_recentStudies.length}건',
                caption: _loadingStudies ? '불러오는 중' : '접근 가능한 검사',
              ),
              const _SummaryCard(
                icon: Icons.forum_outlined,
                label: '진행 중 협진',
                value: '-',
                caption: '연동 대기',
              ),
              const _SummaryCard(
                icon: Icons.description_outlined,
                label: '진료기록',
                value: '-',
                caption: '연동 대기',
              ),
            ],
          ),
          const SizedBox(height: 24),
          const RadiologySectionTitle(title: '빠른 업무'),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _QuickTaskCard(
                icon: Icons.people_outline_rounded,
                label: '환자 조회',
                onTap: () => widget.onSelectTab(1),
              ),
              _QuickTaskCard(
                icon: Icons.image_outlined,
                label: '검사 결과',
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => NeurologyImagingStudiesPage(
                      apiClient: widget.apiClient,
                    ),
                  ),
                ),
              ),
              _QuickTaskCard(
                icon: Icons.emergency_outlined,
                label: '응급 Worklist',
                onTap: () => widget.onSelectTab(0),
              ),
              _QuickTaskCard(
                icon: Icons.description_outlined,
                label: '진료기록',
                onTap: widget.onOpenClinicalRecords,
              ),
            ],
          ),
          const SizedBox(height: 24),
          const RadiologySectionTitle(title: '최근 검사'),
          const SizedBox(height: 10),
          if (_loadingStudies)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_studiesError != null)
            _RetryCard(message: _studiesError!, onRetry: _loadRecentStudies)
          else if (_recentStudies.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.image_search_outlined,
              message: '최근 확인할 영상검사가 없습니다.',
            )
          else
            ..._recentStudies.take(3).map(
                  (study) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(18),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => NeurologyImagingStudyDetailPage(
                            apiClient: widget.apiClient,
                            studyId: study.id,
                          ),
                        ),
                      ),
                      child: RadiologyInfoCard(
                        child: Row(
                          children: [
                            Icon(
                              study.criticalFinding
                                  ? Icons.warning_amber_rounded
                                  : Icons.image_outlined,
                              color: study.criticalFinding
                                  ? const Color(0xFFB34B58)
                                  : radiologyBlue,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    study.patientName.isEmpty
                                        ? '환자 정보 없음'
                                        : study.patientName,
                                    style: const TextStyle(
                                      color: radiologyNavy,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    study.details,
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
                  ),
                ),
        ],
      );
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.caption,
  });

  final IconData icon;
  final String label;
  final String value;
  final String caption;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Icon(icon, color: radiologyBlue),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 12)),
                  const SizedBox(height: 2),
                  Text(value, style: const TextStyle(color: radiologyNavy, fontSize: 18, fontWeight: FontWeight.w800)),
                  Text(caption, style: const TextStyle(color: radiologyMuted, fontSize: 11)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _QuickTaskCard extends StatelessWidget {
  const _QuickTaskCard({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: (MediaQuery.sizeOf(context).width - 50) / 2,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: onTap,
          child: RadiologyInfoCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
            child: Row(
              children: [
                Icon(icon, color: radiologyBlue),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    label,
                    style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Column(
          children: [
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 10),
            TextButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ),
      );
}

class _RecentStudy {
  const _RecentStudy({
    required this.id,
    required this.patientName,
    required this.modalities,
    required this.studyDateTime,
    required this.status,
    required this.criticalFinding,
  });

  factory _RecentStudy.fromJson(Map<String, dynamic> json) {
    final patient = json['patient'] as Map?;
    return _RecentStudy(
      id: json['study_id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      modalities: (json['modalities'] as List? ?? const [])
          .map((item) => item.toString())
          .join(', '),
      studyDateTime: json['study_datetime']?.toString(),
      status: json['status']?.toString() ?? '',
      criticalFinding: json['critical_finding'] == true,
    );
  }

  final String id;
  final String patientName;
  final String modalities;
  final String? studyDateTime;
  final String status;
  final bool criticalFinding;

  String get details => [
        if (modalities.isNotEmpty) modalities,
        if (studyDateTime != null) _formatDateTime(studyDateTime),
        if (status.isNotEmpty) status,
      ].join(' · ');
}

class NeurologyClinicalRecordsPage extends StatelessWidget {
  const NeurologyClinicalRecordsPage({super.key});
  @override
  Widget build(BuildContext context) => const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('진료기록은 현재 읽기 전용 화면으로 준비 중입니다.', textAlign: TextAlign.center, style: TextStyle(color: radiologyMuted))));
}

class NeurologyProfilePage extends StatelessWidget {
  const NeurologyProfilePage({super.key, required this.user, required this.onLogout});
  final ClinicianUser user;
  final VoidCallback onLogout;

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(title: const Text('로그아웃하시겠습니까?'), content: const Text('현재 로그인 세션이 종료됩니다.'), actions: [TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('취소')), FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('로그아웃'))]));
    if (confirmed == true && context.mounted) onLogout();
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(20, 20, 20, 32), children: [
    RadiologyInfoCard(child: ListTile(leading: const CircleAvatar(backgroundColor: Color(0xFFEAF2FF), child: Icon(Icons.person_rounded, color: radiologyBlue)), title: Text(user.name.isEmpty ? '이름 정보 없음' : user.name, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800)), subtitle: Text(user.loginId.isNotEmpty ? user.loginId : user.email), trailing: const Text('신경과', style: TextStyle(color: radiologyBlue, fontWeight: FontWeight.w700)))),
    const SizedBox(height: 22),
    const RadiologySectionTitle(title: '설정'),
    const SizedBox(height: 10),
    const _SettingsCard(icon: Icons.notifications_none_rounded, title: '알림 설정'),
    const SizedBox(height: 10),
    const _SettingsCard(icon: Icons.settings_outlined, title: '앱 설정'),
    const SizedBox(height: 24),
    OutlinedButton.icon(onPressed: () => _confirmLogout(context), icon: const Icon(Icons.logout_rounded), label: const Text('로그아웃')),
  ]);
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.icon, required this.title});
  final IconData icon; final String title;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(child: Row(children: [Icon(icon, color: radiologyBlue), const SizedBox(width: 12), Expanded(child: Text(title, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800))), const Icon(Icons.chevron_right_rounded, color: radiologyMuted)]));
}

String _formatDateTime(String? value) {
  final dateTime = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value ?? '정보 없음';
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
