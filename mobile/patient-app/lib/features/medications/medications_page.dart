import 'package:flutter/material.dart';

class MedicationsPage extends StatelessWidget {
  const MedicationsPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: const [
          Text('오늘의 복약'),
          Divider(height: 32),
          Text('복약 일정'),
          Divider(height: 32),
          Text('복약 기록'),
          Divider(height: 32),
          Text('약 상세와 복약 알림은 추후 제공됩니다.'),
        ],
      );
}
