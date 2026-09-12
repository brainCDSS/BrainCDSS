import 'package:flutter/material.dart';

class AppointmentsPage extends StatelessWidget {
  const AppointmentsPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: const [
          Text('예약하기'),
          Divider(height: 32),
          Text('예정된 예약'),
          Divider(height: 32),
          Text('지난 예약'),
          SizedBox(height: 24),
          Text('예약 상세 · 변경 · 취소 기능은 추후 제공됩니다.'),
        ],
      );
}
