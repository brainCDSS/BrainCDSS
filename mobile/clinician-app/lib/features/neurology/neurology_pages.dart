import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../auth/clinician_session.dart';
import '../consultations/radiology_consultations_page.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'neurology_imaging_pages.dart';

class NeurologyEmergencyPage extends StatefulWidget {
  const NeurologyEmergencyPage({super.key, required this.apiClient});
  final ClinicianApiClient apiClient;
  @override
  State<NeurologyEmergencyPage> createState() => _NeurologyEmergencyPageState();
}

class _NeurologyEmergencyPageState extends State<NeurologyEmergencyPage> {
  List<_EmergencyItem> _items = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final response = await widget.apiClient.get('/api/v1/neurology/emergency-worklist');
      final items = (response['results'] as List? ?? const []).whereType<Map>().map((item) => _EmergencyItem.fromJson(Map<String, dynamic>.from(item))).toList(growable: false);
      if (mounted) setState(() => _items = items);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '응급 Worklist를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
    children: [
      const RadiologySectionTitle(title: '응급 Worklist'),
      const SizedBox(height: 8),
      const Text('본인에게 배정된 긴급·응급 환자를 확인합니다.', style: TextStyle(color: radiologyMuted, fontSize: 13)),
      const SizedBox(height: 16),
      if (_loading) const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()))
      else if (_error != null) _RetryCard(message: _error!, onRetry: _load)
      else if (_items.isEmpty) const RadiologyEmptyState(icon: Icons.emergency_outlined, message: '현재 배정된 응급 환자가 없습니다.')
      else ..._items.map((item) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: RadiologyInfoCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Expanded(child: Text(item.patientName.isEmpty ? '환자 정보 없음' : item.patientName, style: const TextStyle(color: radiologyNavy, fontSize: 16, fontWeight: FontWeight.w800))), RadiologyStatusChip(label: item.priority, color: item.priority == 'EMERGENCY' ? const Color(0xFFB34B58) : const Color(0xFFB46912))]),
          const SizedBox(height: 8),
          Text(item.redFlags.isEmpty ? '초기평가 결과를 확인하세요.' : item.redFlags.join(' · '), style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w600)),
          const SizedBox(height: 5),
          Text('LKW ${_formatDateTime(item.lkwAt)} · ${item.eventStatus}', style: const TextStyle(color: radiologyMuted, fontSize: 13)),
        ])),
      )),
    ],
  );
}

class NeurologyHomePage extends StatelessWidget {
  const NeurologyHomePage({super.key, required this.apiClient});
  final ClinicianApiClient apiClient;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
    children: [
      const RadiologySectionTitle(title: '오늘 업무'),
      const SizedBox(height: 12),
      _NavigationCard(icon: Icons.image_outlined, title: '영상검사 결과', subtitle: '접근 권한이 있는 영상검사와 최종 판독을 확인합니다.', onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => NeurologyImagingStudiesPage(apiClient: apiClient)))),
      const SizedBox(height: 10),
      _NavigationCard(icon: Icons.forum_outlined, title: '협진', subtitle: '내가 요청하거나 배정된 협진을 확인합니다.', onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => RadiologyConsultationsPage(apiClient: apiClient, viewerRelation: null)))),
    ],
  );
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

class _EmergencyItem {
  const _EmergencyItem({required this.patientName, required this.priority, required this.lkwAt, required this.eventStatus, required this.redFlags});
  factory _EmergencyItem.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    return _EmergencyItem(patientName: patient?['name']?.toString() ?? '', priority: json['triage_priority']?.toString() ?? 'URGENT', lkwAt: json['lkw_at']?.toString(), eventStatus: (json['event'] as Map?)?['status']?.toString() ?? '', redFlags: (json['red_flags'] as List? ?? const []).whereType<Map>().map((flag) => flag['item_code']?.toString() ?? '').where((value) => value.isNotEmpty).toList(growable: false));
  }
  final String patientName;
  final String priority;
  final String? lkwAt;
  final String eventStatus;
  final List<String> redFlags;
}

class _NavigationCard extends StatelessWidget {
  const _NavigationCard({required this.icon, required this.title, required this.subtitle, required this.onTap});
  final IconData icon; final String title; final String subtitle; final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => InkWell(borderRadius: BorderRadius.circular(18), onTap: onTap, child: RadiologyInfoCard(child: Row(children: [Icon(icon, color: radiologyBlue), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800)), const SizedBox(height: 4), Text(subtitle, style: const TextStyle(color: radiologyMuted, fontSize: 13))])), const Icon(Icons.chevron_right_rounded, color: radiologyMuted)])));
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.icon, required this.title});
  final IconData icon; final String title;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(child: Row(children: [Icon(icon, color: radiologyBlue), const SizedBox(width: 12), Expanded(child: Text(title, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800))), const Icon(Icons.chevron_right_rounded, color: radiologyMuted)]));
}

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});
  final String message; final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(child: Column(children: [Text(message, textAlign: TextAlign.center), const SizedBox(height: 10), TextButton(onPressed: onRetry, child: const Text('다시 시도'))]));
}

String _formatDateTime(String? value) {
  final dateTime = value == null ? null : DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) return value ?? '정보 없음';
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
