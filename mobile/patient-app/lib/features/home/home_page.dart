import 'package:flutter/material.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: const [
          _HomeSection(title: '건강 요약', description: '연결된 건강 정보가 표시될 영역입니다.'),
          _HomeSection(title: '오늘 일정', description: '오늘의 예약 일정이 표시될 영역입니다.'),
          _HomeSection(title: '오늘 복약', description: '오늘의 복약 일정이 표시될 영역입니다.'),
          _HomeSection(title: '주요 알림', description: '확인이 필요한 알림이 표시될 영역입니다.'),
          Row(
            children: [
              Expanded(child: _EmergencyButton(icon: Icons.health_and_safety_outlined, label: 'FAST 응급안내')),
              SizedBox(width: 12),
              Expanded(child: _EmergencyButton(icon: Icons.call_outlined, label: '119 연락')),
            ],
          ),
        ],
      );
}

class _HomeSection extends StatelessWidget {
  const _HomeSection({required this.title, required this.description});
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(description),
            const Divider(height: 24),
          ],
        ),
      );
}

class _EmergencyButton extends StatelessWidget {
  const _EmergencyButton({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => OutlinedButton.icon(
        onPressed: null,
        icon: Icon(icon),
        label: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Text(label),
        ),
      );
}
