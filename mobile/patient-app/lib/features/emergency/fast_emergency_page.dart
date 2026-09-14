import 'package:flutter/material.dart';

class FastEmergencyPage extends StatelessWidget {
  const FastEmergencyPage({super.key});

  static void open(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const FastEmergencyPage()),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('FAST 응급안내')),
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF1F1),
                border: Border.all(color: const Color(0xFFF3B9B9)),
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.health_and_safety_outlined,
                      color: Color(0xFFE94E4E), size: 36),
                  SizedBox(height: 14),
                  Text('뇌졸중 의심 증상을 FAST로 확인하세요.',
                      style: TextStyle(
                        color: Color(0xFF263A5A),
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      )),
                  SizedBox(height: 16),
                  _FastItem(letter: 'F', title: 'Face', description: '웃을 때 한쪽 얼굴이 처지는지 확인합니다.'),
                  _FastItem(letter: 'A', title: 'Arms', description: '두 팔을 들었을 때 한쪽 팔이 내려가는지 확인합니다.'),
                  _FastItem(letter: 'S', title: 'Speech', description: '말이 어눌하거나 문장을 제대로 말하지 못하는지 확인합니다.'),
                  _FastItem(letter: 'T', title: 'Time', description: '증상이 있으면 즉시 응급 도움을 요청해야 합니다.'),
                ],
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFE94E4E),
                padding: const EdgeInsets.symmetric(vertical: 15),
              ),
              onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('119 전화 연결 기능은 준비 중입니다.')),
              ),
              icon: const Icon(Icons.call_outlined),
              label: const Text('119 연결'),
            ),
          ],
        ),
      );
}

class _FastItem extends StatelessWidget {
  const _FastItem({required this.letter, required this.title, required this.description});

  final String letter;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: const Color(0xFFE94E4E),
              foregroundColor: Colors.white,
              child: Text(letter, style: const TextStyle(fontWeight: FontWeight.w800)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 3),
                  Text(description, style: const TextStyle(color: Color(0xFF65758D), height: 1.4)),
                ],
              ),
            ),
          ],
        ),
      );
}
