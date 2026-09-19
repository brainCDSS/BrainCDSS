import 'package:flutter/material.dart';

import '../radiology/widgets/radiology_ui.dart';

class RadiologyHomePage extends StatelessWidget {
  const RadiologyHomePage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: const [
          _WorkSummaryCard(),
          SizedBox(height: 24),
          RadiologySectionTitle(title: '최근 알림', action: '전체 보기'),
          SizedBox(height: 10),
          _ActivityCard(
            icon: Icons.notifications_active_outlined,
            title: '새 분석 요청이 도착했습니다',
            subtitle: '뇌 MRI · 10분 전',
            color: Color(0xFF2563B8),
          ),
          SizedBox(height: 10),
          _ActivityCard(
            icon: Icons.forum_outlined,
            title: '협진 답변을 확인해 주세요',
            subtitle: '신경외과 · 35분 전',
            color: Color(0xFF7C5CC4),
          ),
          SizedBox(height: 24),
          RadiologySectionTitle(title: '최근 처리 내역', action: '전체 보기'),
          SizedBox(height: 10),
          _RecentWorkCard(
            patient: '김민준',
            exam: 'Brain MRI',
            time: '오늘 09:42',
            status: '분석 완료',
          ),
          SizedBox(height: 10),
          _RecentWorkCard(
            patient: '이서연',
            exam: 'Brain CT',
            time: '어제 16:10',
            status: '협진 회신',
          ),
        ],
      );
}

class _WorkSummaryCard extends StatelessWidget {
  const _WorkSummaryCard();

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '오늘 업무 요약',
              style: TextStyle(
                color: radiologyNavy,
                fontSize: 20,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              '우선 확인이 필요한 업무를 살펴보세요.',
              style: TextStyle(color: radiologyMuted, fontSize: 13),
            ),
            const SizedBox(height: 18),
            const Row(
              children: [
                Expanded(
                  child: _SummaryMetric(
                    icon: Icons.analytics_outlined,
                    label: '미처리 분석요청',
                    value: '3건',
                    color: Color(0xFF2563B8),
                  ),
                ),
                SizedBox(width: 12),
                Expanded(
                  child: _SummaryMetric(
                    icon: Icons.forum_outlined,
                    label: '미확인 협진',
                    value: '2건',
                    color: Color(0xFF7C5CC4),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _SummaryMetric extends StatelessWidget {
  const _SummaryMetric({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 14),
            Text(label, style: const TextStyle(color: radiologyMuted, fontSize: 12)),
            const SizedBox(height: 3),
            Text(
              value,
              style: const TextStyle(
                color: radiologyNavy,
                fontSize: 19,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      );
}

class _ActivityCard extends StatelessWidget {
  const _ActivityCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Row(
          children: [
            CircleAvatar(
              radius: 21,
              backgroundColor: color.withValues(alpha: 0.1),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 3),
                  Text(subtitle, style: const TextStyle(color: radiologyMuted, fontSize: 13)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
          ],
        ),
      );
}

class _RecentWorkCard extends StatelessWidget {
  const _RecentWorkCard({
    required this.patient,
    required this.exam,
    required this.time,
    required this.status,
  });

  final String patient;
  final String exam;
  final String time;
  final String status;

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
              child: const Icon(Icons.description_outlined, color: radiologyBlue),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('$patient · $exam', style: const TextStyle(color: radiologyNavy, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 3),
                  Text(time, style: const TextStyle(color: radiologyMuted, fontSize: 13)),
                ],
              ),
            ),
            RadiologyStatusChip(label: status, color: const Color(0xFF208563)),
          ],
        ),
      );
}
