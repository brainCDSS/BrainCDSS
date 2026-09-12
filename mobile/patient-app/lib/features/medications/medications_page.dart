import 'package:flutter/material.dart';

const _primary = Color(0xFF416AAB);
const _soft = Color(0xFFEAF1FC);
const _border = Color(0xFFDEE6F2);
const _text = Color(0xFF1D3153);
const _muted = Color(0xFF75849A);

class MedicationsPage extends StatelessWidget {
  const MedicationsPage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      const Text('오늘의 복약', style: TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w800)),
      const SizedBox(height: 10),
      const _EmptyMedicationCard(),
      const SizedBox(height: 22),
      _MedicationMenu(icon: Icons.calendar_month_outlined, title: '복약 일정', description: '예정된 복약 일정을 확인할 수 있어요.', onTap: () => _open(context, const _MedicationSchedulePage())),
      const SizedBox(height: 10),
      _MedicationMenu(icon: Icons.fact_check_outlined, title: '복약 기록', description: '복약 기록을 확인할 수 있어요.', onTap: () => _open(context, const _MedicationHistoryPage())),
      const SizedBox(height: 10),
      _MedicationMenu(icon: Icons.medication_outlined, title: '약 정보 상세', description: '처방 약의 상세 정보를 확인할 수 있어요.', onTap: () => _open(context, const _MedicationDetailPage())),
    ],
  );

  void _open(BuildContext context, Widget page) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
}

class _EmptyMedicationCard extends StatelessWidget {
  const _EmptyMedicationCard();
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 36),
    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
    child: const Column(children: [
      Icon(Icons.medication_outlined, color: Color(0xFF8FAFE8), size: 42),
      SizedBox(height: 14),
      Text('복약할 약이 없습니다.', style: TextStyle(color: _text, fontWeight: FontWeight.w700)),
      SizedBox(height: 6),
      Text('복약 일정이 있으면 여기에 표시됩니다.', style: TextStyle(color: _muted)),
    ]),
  );
}

class _MedicationMenu extends StatelessWidget {
  const _MedicationMenu({required this.icon, required this.title, required this.description, required this.onTap});
  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(18),
    child: Ink(
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
      child: Row(children: [
        Container(width: 42, height: 42, decoration: BoxDecoration(color: _soft, borderRadius: BorderRadius.circular(13)), child: Icon(icon, color: _primary)),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(color: _text, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(description, style: const TextStyle(color: _muted, fontSize: 13)),
        ])),
        const Icon(Icons.chevron_right_rounded, color: _muted),
      ]),
    ),
  );
}

class _MedicationSchedulePage extends StatelessWidget {
  const _MedicationSchedulePage();
  @override
  Widget build(BuildContext context) => const _MedicationEmptyPage(title: '복약 일정', icon: Icons.calendar_month_outlined, message: '등록된 복약 일정이 없습니다.');
}

class _MedicationHistoryPage extends StatelessWidget {
  const _MedicationHistoryPage();
  @override
  Widget build(BuildContext context) => const _MedicationEmptyPage(title: '복약 기록', icon: Icons.fact_check_outlined, message: '등록된 복약 기록이 없습니다.');
}

class _MedicationDetailPage extends StatelessWidget {
  const _MedicationDetailPage();
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('약 상세')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const _MedicationEmptyPageBody(icon: Icons.health_and_safety_outlined, message: '등록된 복약 정보가 없습니다.'),
      const SizedBox(height: 16),
      OutlinedButton.icon(
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const _MedicationNotificationPage())),
        icon: const Icon(Icons.notifications_outlined),
        label: const Text('개별 복약 알림 설정'),
      ),
    ]),
  );
}

class _MedicationNotificationPage extends StatelessWidget {
  const _MedicationNotificationPage();
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('복약 알림 설정')),
    body: const _MedicationEmptyPageBody(icon: Icons.notifications_none_rounded, message: '설정할 복약 일정이 없습니다.'),
  );
}

class _MedicationEmptyPage extends StatelessWidget {
  const _MedicationEmptyPage({required this.title, required this.icon, required this.message});
  final String title;
  final IconData icon;
  final String message;
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: Text(title)), body: _MedicationEmptyPageBody(icon: icon, message: message));
}

class _MedicationEmptyPageBody extends StatelessWidget {
  const _MedicationEmptyPageBody({required this.icon, required this.message});
  final IconData icon;
  final String message;
  @override
  Widget build(BuildContext context) => Center(child: Container(
    width: double.infinity,
    margin: const EdgeInsets.all(20),
    padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
    child: Column(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, color: const Color(0xFF8FAFE8), size: 38),
      const SizedBox(height: 14),
      Text(message, textAlign: TextAlign.center, style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
      const SizedBox(height: 6),
      const Text('관련 API가 연결되면 이곳에 표시됩니다.', textAlign: TextAlign.center, style: TextStyle(color: _muted)),
    ]),
  ));
}
