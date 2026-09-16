import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';

const _primary = Color(0xFF7567C8);
const _soft = Color(0xFFEEEAFE);
const _border = Color(0xFFCFD7E8);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);

class TestResultsPage extends StatelessWidget {
  const TestResultsPage({super.key, required this.apiClient});
  final ApiClient apiClient;

  static void openResults(BuildContext context) =>
      _openPage(context, const _ResultDetailPage());

  static void openVisits(BuildContext context) =>
      _openPage(context, const _VisitDetailPage());

  static void openPrescriptions(BuildContext context, ApiClient client) =>
      _openPage(context, const _PrescriptionDetailPage());

  static void _openPage(BuildContext context, Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      _MenuCard(icon: Icons.assignment_turned_in_outlined, title: '검사 결과', description: '검사 결과를 확인할 수 있어요.', onTap: () => openResults(context)),
      const SizedBox(height: 12),
      _MenuCard(icon: Icons.history_edu_outlined, title: '진료 내역', description: '진료 기록을 확인할 수 있어요.', onTap: () => openVisits(context)),
      const SizedBox(height: 12),
      _MenuCard(icon: Icons.description_outlined, title: '처방 정보', description: '처방된 약 정보를 확인할 수 있어요.', onTap: () => openPrescriptions(context, apiClient)),
    ],
  );

}

class _MenuCard extends StatelessWidget {
  const _MenuCard({required this.icon, required this.title, required this.description, required this.onTap});
  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(18),
    child: Ink(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
      child: Row(children: [
        Container(width: 44, height: 44, decoration: BoxDecoration(color: _soft, borderRadius: BorderRadius.circular(13)), child: Icon(icon, color: _primary)),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(color: _text, fontSize: 16, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(description, style: const TextStyle(color: _muted, fontSize: 13)),
        ])),
        const Icon(Icons.chevron_right_rounded, color: _muted),
      ]),
    ),
  );
}

class _ResultDetailPage extends StatelessWidget {
  const _ResultDetailPage();
  @override
  Widget build(BuildContext context) => const _DetailScaffold(
    title: '검사 결과 상세',
    icon: Icons.biotech_outlined,
    emptyTitle: '등록된 검사 결과가 없습니다.',
    description: '검사 결과가 등록되면 이곳에서 확인할 수 있습니다.',
  );
}

class _VisitDetailPage extends StatelessWidget {
  const _VisitDetailPage();
  @override
  Widget build(BuildContext context) => const _DetailScaffold(
    title: '진료 내역 상세',
    icon: Icons.medical_information_outlined,
    emptyTitle: '등록된 진료 내역이 없습니다.',
    description: '진료 기록이 등록되면 이곳에서 확인할 수 있습니다.',
  );
}

class _PrescriptionDetailPage extends StatelessWidget {
  const _PrescriptionDetailPage();
  @override
  Widget build(BuildContext context) => const _DetailScaffold(
    title: '처방 정보',
    icon: Icons.receipt_long_outlined,
    emptyTitle: '등록된 처방 정보가 없습니다.',
    description: '처방 정보가 등록되면 이곳에서 확인할 수 있습니다.',
  );
}

class _DetailScaffold extends StatelessWidget {
  const _DetailScaffold({required this.title, required this.icon, required this.emptyTitle, required this.description});
  final String title;
  final IconData icon;
  final String emptyTitle;
  final String description;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(title)),
    body: Center(child: Container(
      margin: const EdgeInsets.all(20),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 42),
      decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 38, color: _primary),
        const SizedBox(height: 14),
        Text(emptyTitle, textAlign: TextAlign.center, style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
        const SizedBox(height: 7),
        Text(description, textAlign: TextAlign.center, style: const TextStyle(color: _muted, height: 1.45)),
      ]),
    )),
  );
}
