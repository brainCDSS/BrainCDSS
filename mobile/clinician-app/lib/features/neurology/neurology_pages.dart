import 'package:flutter/material.dart';

import '../auth/clinician_session.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyEmergencyPage extends StatelessWidget {
  const NeurologyEmergencyPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '응급 Worklist'),
          const SizedBox(height: 8),
          const Text('초기 평가가 필요한 응급 환자를 확인합니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 13)),
          const SizedBox(height: 16),
          ...const [
            _EmergencyPreview('김민준', 'EMERGENCY', 'FAST 양성 · 초기평가 대기', '08:20', '대기'),
            _EmergencyPreview('이서연', 'URGENT', 'FAST 확인 필요 · 초기평가 진행', '09:05', '진행중'),
          ].map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _EmergencyCard(item: item),
            ),
          ),
        ],
      );
}

class NeurologyPatientsPage extends StatelessWidget {
  const NeurologyPatientsPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '환자'),
          const SizedBox(height: 14),
          TextField(
            decoration: InputDecoration(
              hintText: '환자명 또는 환자번호 검색',
              prefixIcon: const Icon(Icons.search_rounded),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: radiologyBorder),
              ),
            ),
          ),
          const SizedBox(height: 18),
          ...const [
            _PatientPreview('김민준', '남성 · 54세', 'P-20260920-001', '진료중'),
            _PatientPreview('박도윤', '여성 · 67세', 'P-20260920-002', '대기'),
          ].map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _PatientCard(item: item),
            ),
          ),
        ],
      );
}

class NeurologyHomePage extends StatelessWidget {
  const NeurologyHomePage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '오늘 업무 요약'),
          const SizedBox(height: 12),
          const _MetricGrid(),
          const SizedBox(height: 24),
          const RadiologySectionTitle(title: '최근 처리 내역'),
          const SizedBox(height: 10),
          const _RecentCard(
            icon: Icons.emergency_outlined,
            title: '응급 초기평가가 등록되었습니다.',
            subtitle: '오늘 09:10',
          ),
          const SizedBox(height: 10),
          const _RecentCard(
            icon: Icons.description_outlined,
            title: '확인할 검사결과가 있습니다.',
            subtitle: '오늘 08:42',
          ),
        ],
      );
}

class NeurologyClinicalRecordsPage extends StatelessWidget {
  const NeurologyClinicalRecordsPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '진료기록'),
          const SizedBox(height: 8),
          const Text('진료기록은 확인용으로만 제공됩니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 13)),
          const SizedBox(height: 16),
          ...const [
            _RecordPreview('김민준', '2026.09.20', '김현우 교수', 'FINAL'),
            _RecordPreview('박도윤', '2026.09.19', '이수민 교수', 'FINAL'),
          ].map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _RecordCard(item: item),
            ),
          ),
        ],
      );
}

class NeurologyProfilePage extends StatelessWidget {
  const NeurologyProfilePage({
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
              child: const Text('취소')),
          FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('로그아웃')),
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
          RadiologyInfoCard(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                const CircleAvatar(
                  radius: 30,
                  backgroundColor: Color(0xFFEAF2FF),
                  child: Icon(Icons.person_rounded, color: radiologyBlue, size: 34),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user.name.isEmpty ? '이름 정보 없음' : user.name,
                          style: const TextStyle(
                              color: radiologyNavy,
                              fontSize: 19,
                              fontWeight: FontWeight.w800)),
                      const SizedBox(height: 4),
                      const Text('신경과',
                          style: TextStyle(
                              color: radiologyBlue, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 4),
                      Text(user.loginId.isNotEmpty ? user.loginId : user.email,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: radiologyMuted, fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          const RadiologySectionTitle(title: '설정'),
          const SizedBox(height: 10),
          const _SettingsCard(icon: Icons.notifications_none_rounded, title: '알림 설정'),
          const SizedBox(height: 10),
          const _SettingsCard(icon: Icons.settings_outlined, title: '앱 설정'),
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

class _EmergencyPreview {
  const _EmergencyPreview(this.name, this.priority, this.summary, this.lkw, this.status);
  final String name;
  final String priority;
  final String summary;
  final String lkw;
  final String status;
}

class _EmergencyCard extends StatelessWidget {
  const _EmergencyCard({required this.item});
  final _EmergencyPreview item;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(item.name, style: const TextStyle(color: radiologyNavy, fontSize: 16, fontWeight: FontWeight.w800))),
            RadiologyStatusChip(label: item.priority, color: const Color(0xFFB34B58)),
          ]),
          const SizedBox(height: 10),
          Text(item.summary, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w600)),
          const SizedBox(height: 5),
          Text('LKW ${item.lkw} · ${item.status}', style: const TextStyle(color: radiologyMuted, fontSize: 13)),
        ]),
      );
}

class _PatientPreview {
  const _PatientPreview(this.name, this.demographics, this.number, this.status);
  final String name;
  final String demographics;
  final String number;
  final String status;
}

class _PatientCard extends StatelessWidget {
  const _PatientCard({required this.item});
  final _PatientPreview item;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(children: [
          CircleAvatar(
              backgroundColor: const Color(0xFFEAF2FF),
              child: Text(item.name.substring(0, 1), style: const TextStyle(color: radiologyBlue, fontWeight: FontWeight.w800))),
          const SizedBox(width: 13),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(item.name, style: const TextStyle(color: radiologyNavy, fontSize: 16, fontWeight: FontWeight.w800)),
            const SizedBox(height: 3),
            Text('${item.demographics} · ${item.number}', style: const TextStyle(color: radiologyMuted, fontSize: 12)),
            const SizedBox(height: 6),
            Text(item.status, style: const TextStyle(color: radiologyBlue, fontSize: 13, fontWeight: FontWeight.w700)),
          ])),
          const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
        ]),
      );
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid();

  @override
  Widget build(BuildContext context) => GridView.count(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        shrinkWrap: true,
        physics: NeverScrollableScrollPhysics(),
        childAspectRatio: 1.6,
        children: [
          _MetricCard('오늘 응급환자', '2건', Icons.emergency_outlined),
          _MetricCard('초기평가', '1건', Icons.fact_check_outlined),
          _MetricCard('협진 요청', '3건', Icons.forum_outlined),
          _MetricCard('검사결과', '2건', Icons.description_outlined),
        ],
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard(this.label, this.value, this.icon);
  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: radiologyBlue),
          const Spacer(),
          Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 12)),
          Text(value, style: const TextStyle(color: radiologyNavy, fontSize: 18, fontWeight: FontWeight.w800)),
        ]),
      );
}

class _RecentCard extends StatelessWidget {
  const _RecentCard({required this.icon, required this.title, required this.subtitle});
  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(children: [
          Icon(icon, color: radiologyBlue),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w700)),
            const SizedBox(height: 3),
            Text(subtitle, style: const TextStyle(color: radiologyMuted, fontSize: 13)),
          ])),
        ]),
      );
}

class _RecordPreview {
  const _RecordPreview(this.patient, this.date, this.author, this.status);
  final String patient;
  final String date;
  final String author;
  final String status;
}

class _RecordCard extends StatelessWidget {
  const _RecordCard({required this.item});
  final _RecordPreview item;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(children: [
          const Icon(Icons.description_outlined, color: radiologyBlue),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(item.patient, style: const TextStyle(color: radiologyNavy, fontSize: 16, fontWeight: FontWeight.w800)),
            const SizedBox(height: 3),
            Text('${item.date} · ${item.author}', style: const TextStyle(color: radiologyMuted, fontSize: 12)),
          ])),
          RadiologyStatusChip(label: item.status, color: const Color(0xFF208563)),
        ]),
      );
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.icon, required this.title});
  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(children: [
          Icon(icon, color: radiologyBlue),
          const SizedBox(width: 12),
          Expanded(child: Text(title, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w800))),
          const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
        ]),
      );
}
