import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';

const _primary = Color(0xFF2F9D76);
const _soft = Color(0xFFE3F6EF);
const _border = Color(0xFFCFD7E8);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);

class MedicationsPage extends StatelessWidget {
  const MedicationsPage({super.key, required this.apiClient});
  final ApiClient apiClient;
  static void openSchedule(BuildContext context, ApiClient client) => _open(context, const _MedicationEmptyPage(title: '복약 일정', message: '등록된 복약 일정이 없습니다.'));
  static void openHistory(BuildContext context, ApiClient client) => _open(context, const _MedicationEmptyPage(title: '복약 기록', message: '등록된 복약 기록이 없습니다.'));
  static void openNotificationSettings(BuildContext context) => _open(context, const _MedicationEmptyPage(title: '복약 알림 설정', message: '설정할 복약 일정이 없습니다.'));
  static void _open(BuildContext context, Widget page) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  @override Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(20), children: [
    const Text('오늘의 복약', style: TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w800)), const SizedBox(height: 10),
    const _EmptyMedicationCard(), const SizedBox(height: 22),
    _menu(context, Icons.calendar_month_outlined, '복약 일정', () => openSchedule(context, apiClient)), const SizedBox(height: 10),
    _menu(context, Icons.fact_check_outlined, '복약 기록', () => openHistory(context, apiClient)),
  ]);
  Widget _menu(BuildContext context, IconData icon, String title, VoidCallback onTap) => ListTile(tileColor: _soft, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: _border)), leading: Icon(icon, color: _primary), title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)), trailing: const Icon(Icons.chevron_right, color: _muted), onTap: onTap);
}
class _EmptyMedicationCard extends StatelessWidget { const _EmptyMedicationCard(); @override Widget build(BuildContext context) => Container(width: double.infinity, padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 36), decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)), child: const Column(children: [Icon(Icons.medication_outlined, color: _primary, size: 42), SizedBox(height: 14), Text('복약할 약이 없습니다.', style: TextStyle(color: _text, fontWeight: FontWeight.w700)), SizedBox(height: 6), Text('복약 일정 API의 실제 응답 연결이 필요합니다.', style: TextStyle(color: _muted))])); }
class _MedicationEmptyPage extends StatelessWidget { const _MedicationEmptyPage({required this.title, required this.message}); final String title, message; @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: Text(title)), body: Center(child: Text(message))); }
