import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../home/home_api.dart';

const _primary = Color(0xFF416AAB);
const _soft = Color(0xFFEAF1FC);
const _border = Color(0xFFDEE6F2);
const _text = Color(0xFF1D3153);
const _muted = Color(0xFF75849A);
const _danger = Color(0xFFE94E4E);

class AppointmentsPage extends StatefulWidget {
  const AppointmentsPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<AppointmentsPage> createState() => _AppointmentsPageState();
}

class _AppointmentsPageState extends State<AppointmentsPage> {
  late final HomeApi _api;
  bool _loading = true;
  String? _error;
  List<HomeAppointment> _appointments = const [];

  @override
  void initState() {
    super.initState();
    _api = HomeApi(widget.apiClient);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _api.getMyAppointments();
      if (!mounted) return;
      setState(() {
        _appointments = result;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = '예약 정보를 불러오지 못했습니다.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final upcoming = _appointments.where((item) {
      final date = item.scheduledAt;
      return date != null && !date.isBefore(now) &&
          !{'CANCELLED', 'REJECTED', 'COMPLETED'}.contains(item.status);
    }).toList();
    final past = _appointments.where((item) => !upcoming.contains(item)).toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          _ReserveBanner(onTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const _ReservationStartPage()),
          )),
          const SizedBox(height: 24),
          const _SectionTitle('예정된 예약'),
          const SizedBox(height: 10),
          if (_loading)
            const _StateCard.loading()
          else if (_error != null)
            _StateCard.error(message: _error!, onRetry: _load)
          else if (upcoming.isEmpty)
            const _StateCard.empty(
              icon: Icons.event_available_outlined,
              title: '예정된 예약이 없습니다.',
              description: '진료를 예약하면 여기에 표시됩니다.',
            )
          else
            ...upcoming.map((item) => _AppointmentTile(
              appointment: item,
              onTap: () => _openDetail(item),
            )),
          const SizedBox(height: 24),
          const _SectionTitle('지난 예약'),
          const SizedBox(height: 10),
          if (!_loading && _error == null && past.isEmpty)
            const _StateCard.empty(
              icon: Icons.history_rounded,
              title: '지난 예약이 없습니다.',
              description: '완료되거나 취소된 예약이 여기에 표시됩니다.',
            )
          else if (!_loading && _error == null)
            ...past.map((item) => _AppointmentTile(
              appointment: item,
              onTap: () => _openDetail(item),
            )),
        ],
      ),
    );
  }

  void _openDetail(HomeAppointment appointment) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => AppointmentDetailPage(appointment: appointment),
    ));
  }
}

class _ReserveBanner extends StatelessWidget {
  const _ReserveBanner({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(20),
    child: Ink(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFFAFC9F2), Color(0xFF79A5DF)]),
        borderRadius: BorderRadius.circular(20),
      ),
      child: const Row(children: [
        Icon(Icons.calendar_month_rounded, color: Colors.white, size: 34),
        SizedBox(width: 16),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('진료 예약하기', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
          SizedBox(height: 5),
          Text('희망 날짜와 진료과를 선택해 예약할 수 있어요.', style: TextStyle(color: Colors.white, height: 1.4)),
        ])),
        CircleAvatar(backgroundColor: Colors.white, child: Icon(Icons.arrow_forward_rounded, color: _primary)),
      ]),
    ),
  );
}

class _AppointmentTile extends StatelessWidget {
  const _AppointmentTile({required this.appointment, required this.onTap});
  final HomeAppointment appointment;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final date = appointment.scheduledAt?.toLocal();
    final details = [
      appointment.hospitalName,
      appointment.departmentName,
      appointment.clinicianName,
    ].where((value) => value.isNotEmpty).join(' · ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18), border: Border.all(color: _border)),
          child: Row(children: [
            Container(width: 44, height: 44, decoration: BoxDecoration(color: _soft, borderRadius: BorderRadius.circular(14)), child: const Icon(Icons.calendar_today_outlined, color: _primary)),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(date == null ? '예약 일시 정보 없음' : _formatDate(date), style: const TextStyle(color: _text, fontWeight: FontWeight.w800)),
              if (details.isNotEmpty) ...[const SizedBox(height: 5), Text(details, style: const TextStyle(color: _muted, fontSize: 13))],
            ])),
            const Icon(Icons.chevron_right_rounded, color: _muted),
          ]),
        ),
      ),
    );
  }
}

class AppointmentDetailPage extends StatelessWidget {
  const AppointmentDetailPage({super.key, required this.appointment});
  final HomeAppointment appointment;

  @override
  Widget build(BuildContext context) {
    final date = appointment.scheduledAt?.toLocal();
    return Scaffold(
      appBar: AppBar(title: const Text('예약 상세')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        _InfoCard(title: appointment.departmentName.isEmpty ? '진료 예약' : appointment.departmentName, rows: {
          '예약일시': date == null ? '-' : _formatDate(date),
          '병원': appointment.hospitalName.isEmpty ? '-' : appointment.hospitalName,
          '의료진': appointment.clinicianName.isEmpty ? '-' : appointment.clinicianName,
          '상태': _statusLabel(appointment.status),
          '예약 유형': appointment.requestType.isEmpty ? '-' : appointment.requestType,
        }),
        const SizedBox(height: 18),
        Row(children: [
          Expanded(child: OutlinedButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const _ReservationChangePage())), child: const Text('예약 변경'))),
          const SizedBox(width: 10),
          Expanded(child: OutlinedButton(style: OutlinedButton.styleFrom(foregroundColor: _danger), onPressed: () => _showCancel(context), child: const Text('예약 취소'))),
        ]),
      ]),
    );
  }

  void _showCancel(BuildContext context) {
    showDialog<void>(context: context, builder: (dialogContext) => AlertDialog(
      title: const Text('예약을 취소할까요?'),
      content: const Text('예약 취소 API가 확인되지 않아 현재 화면에서는 실제 취소가 처리되지 않습니다.'),
      actions: [TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('확인'))],
    ));
  }
}

class _ReservationStartPage extends StatelessWidget {
  const _ReservationStartPage();
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('진료 예약')),
    body: const _StateCard.empty(icon: Icons.calendar_month_outlined, title: '예약 접수 화면 준비 중', description: '예약 생성 API 계약이 확인되면 진료과와 일정을 연결합니다.'),
  );
}

class _ReservationChangePage extends StatelessWidget {
  const _ReservationChangePage();
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('예약 변경')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const _SectionTitle('날짜 선택'),
      const SizedBox(height: 12),
      const _StateCard.empty(icon: Icons.event_repeat_outlined, title: '변경 가능한 일정이 없습니다.', description: '예약 변경 API와 가용 슬롯이 연결되면 표시됩니다.'),
      const SizedBox(height: 20),
      FilledButton(onPressed: null, child: const Text('다음')),
    ]),
  );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.title, required this.rows});
  final String title;
  final Map<String, String> rows;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: const TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w800)),
      const Divider(height: 28),
      ...rows.entries.map((row) => Padding(padding: const EdgeInsets.only(bottom: 14), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 88, child: Text(row.key, style: const TextStyle(color: _muted))),
        Expanded(child: Text(row.value, style: const TextStyle(color: _text, fontWeight: FontWeight.w600))),
      ]))),
    ]),
  );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: const TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w800));
}

class _StateCard extends StatelessWidget {
  const _StateCard.empty({required this.icon, required this.title, required this.description}) : loading = false, message = null, onRetry = null;
  const _StateCard.loading() : loading = true, icon = Icons.hourglass_empty, title = '', description = '', message = null, onRetry = null;
  const _StateCard.error({required this.message, required this.onRetry}) : loading = false, icon = Icons.error_outline, title = '', description = '';
  final bool loading;
  final IconData icon;
  final String title;
  final String description;
  final String? message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    margin: const EdgeInsets.all(20),
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: _border), borderRadius: BorderRadius.circular(18)),
    child: loading
      ? const Center(child: CircularProgressIndicator())
      : Column(children: [
          Icon(icon, color: const Color(0xFF8FAFE8), size: 34),
          const SizedBox(height: 12),
          Text(message ?? title, textAlign: TextAlign.center, style: const TextStyle(color: _text, fontWeight: FontWeight.w700)),
          if (message == null) ...[const SizedBox(height: 6), Text(description, textAlign: TextAlign.center, style: const TextStyle(color: _muted, height: 1.4))],
          if (onRetry != null) ...[const SizedBox(height: 14), OutlinedButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('다시 시도'))],
        ]),
  );
}

String _formatDate(DateTime value) {
  final month = value.month.toString().padLeft(2, '0');
  final day = value.day.toString().padLeft(2, '0');
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${value.year}.$month.$day  $hour:$minute';
}

String _statusLabel(String status) => {
  'REQUESTED': '예약 요청',
  'CONFIRMED': '예약 확정',
  'IN_PROGRESS': '진료 중',
  'COMPLETED': '진료 완료',
  'CANCELLED': '취소',
  'REJECTED': '예약 거절',
}[status] ?? (status.isEmpty ? '상태 정보 없음' : status);
