import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../home/home_api.dart';
import 'appointments_api.dart';

const _primary = Color(0xFF367FD3);
const _soft = Color(0xFFE7F1FF);
const _border = Color(0xFFCFD7E8);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);
const _danger = Color(0xFFE94E4E);

class AppointmentsPage extends StatefulWidget {
  const AppointmentsPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  static void openReservation(BuildContext context, ApiClient apiClient, {VoidCallback? onChanged}) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => _ReservationStartPage(apiClient: apiClient, onChanged: onChanged)),
    );
  }

  @override
  State<AppointmentsPage> createState() => AppointmentsPageState();
}

class AppointmentsPageState extends State<AppointmentsPage> {
  late final HomeApi _api;
  final _upcomingKey = GlobalKey();
  final _pastKey = GlobalKey();
  bool _loading = true;
  String? _error;
  List<HomeAppointment> _appointments = const [];

  void showUpcoming() => _showSection(_upcomingKey);

  void showPast() => _showSection(_pastKey);

  void _showSection(GlobalKey key) {
    final sectionContext = key.currentContext;
    if (sectionContext != null) {
      Scrollable.ensureVisible(
        sectionContext,
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeOut,
      );
    }
  }

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
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
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
          _ReserveBanner(onTap: () => AppointmentsPage.openReservation(context, widget.apiClient, onChanged: _load)),
          const SizedBox(height: 24),
          KeyedSubtree(
            key: _upcomingKey,
            child: const _SectionTitle('예정된 예약'),
          ),
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
          KeyedSubtree(
            key: _pastKey,
            child: const _SectionTitle('지난 예약'),
          ),
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

  Future<void> _openDetail(HomeAppointment appointment) async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => AppointmentDetailPage(appointment: appointment, apiClient: widget.apiClient),
    ));
    await _load();
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

class AppointmentDetailPage extends StatefulWidget {
  const AppointmentDetailPage({super.key, required this.appointment, required this.apiClient});
  final HomeAppointment appointment;
  final ApiClient apiClient;

  @override
  State<AppointmentDetailPage> createState() => _AppointmentDetailPageState();
}

class _AppointmentDetailPageState extends State<AppointmentDetailPage> {
  Map<String, dynamic>? _detail;
  String? _error;
  bool _isCancelling = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try { final value = await AppointmentsApi(widget.apiClient).detail(widget.appointment.appointmentId); if (mounted) setState(() { _detail = value; _error = null; }); }
    on ApiException catch (error) { if (mounted) setState(() => _error = error.message); }
    catch (_) { if (mounted) setState(() => _error = '예약 상세를 불러오지 못했습니다.'); }
  }

  @override
  Widget build(BuildContext context) {
    if (_detail == null) return Scaffold(appBar: AppBar(title: const Text('예약 상세')), body: Center(child: _error == null ? const CircularProgressIndicator() : TextButton(onPressed: _load, child: Text('$_error 다시 시도'))));
    String nested(String key) { final value = _detail![key]; return value is Map ? value['name']?.toString() ?? '' : ''; }
    final date = DateTime.tryParse(_detail!['scheduled_at']?.toString() ?? '')?.toLocal();
    return Scaffold(
      appBar: AppBar(title: const Text('예약 상세')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        _InfoCard(title: nested('department').isEmpty ? '진료 예약' : nested('department'), rows: {
          '예약일시': date == null ? '-' : _formatDate(date),
          '병원': nested('hospital').isEmpty ? '-' : nested('hospital'),
          '의료진': nested('clinician').isEmpty ? '-' : nested('clinician'),
          '상태': _statusLabel(_detail!['status']?.toString() ?? ''),
          '예약 유형': _detail!['request_type']?.toString() ?? '-',
        }),
        const SizedBox(height: 18),
        Row(children: [
          Expanded(child: OutlinedButton(onPressed: () async { final changed = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => _ReservationChangePage(apiClient: widget.apiClient, appointment: widget.appointment))); if (changed == true && context.mounted) Navigator.pop(context); }, child: const Text('예약 변경'))),
          const SizedBox(width: 10),
          Expanded(child: OutlinedButton(style: OutlinedButton.styleFrom(foregroundColor: _danger), onPressed: _isCancelling ? null : () => _showCancel(context), child: Text(_isCancelling ? '취소 중...' : '예약 취소'))),
        ]),
      ]),
    );
  }

  void _showCancel(BuildContext context) {
    final reason = TextEditingController();
    showDialog<void>(context: context, builder: (dialogContext) => AlertDialog(
      title: const Text('예약을 취소할까요?'),
      content: TextField(controller: reason, decoration: const InputDecoration(labelText: '취소 사유 (선택)')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('닫기')),
        FilledButton(onPressed: () async {
          if (_isCancelling) return;
          setState(() => _isCancelling = true);
          try {
            await AppointmentsApi(widget.apiClient).cancel(widget.appointment.appointmentId, reason: reason.text);
            if (dialogContext.mounted) Navigator.pop(dialogContext);
            if (context.mounted) Navigator.pop(context);
          } on ApiException catch (error) {
            if (dialogContext.mounted) ScaffoldMessenger.of(dialogContext).showSnackBar(SnackBar(content: Text(error.message)));
          } catch (_) {
            if (dialogContext.mounted) ScaffoldMessenger.of(dialogContext).showSnackBar(const SnackBar(content: Text('예약 취소를 처리하지 못했습니다.')));
          } finally {
            if (mounted) setState(() => _isCancelling = false);
          }
        }, child: const Text('예약 취소')),
      ],
    ));
  }
}

class _ReservationStartPage extends StatelessWidget {
  const _ReservationStartPage({required this.apiClient, this.onChanged});
  final ApiClient apiClient;
  final VoidCallback? onChanged;
  @override
  Widget build(BuildContext context) => _SlotSelectionPage(
    apiClient: apiClient,
    title: '진료 예약',
    onSubmit: (slotId) => AppointmentsApi(apiClient).create(slotId),
    onChanged: onChanged,
  );
}

class _ReservationChangePage extends StatelessWidget {
  const _ReservationChangePage({required this.apiClient, required this.appointment});
  final ApiClient apiClient;
  final HomeAppointment appointment;
  @override
  Widget build(BuildContext context) => _SlotSelectionPage(
    apiClient: apiClient,
    title: '예약 변경',
    fixedClinicianId: appointment.clinicianId,
    onSubmit: (slotId) => AppointmentsApi(apiClient).reschedule(appointment.appointmentId, slotId),
  );
}

class _SlotSelectionPage extends StatefulWidget {
  const _SlotSelectionPage({required this.apiClient, required this.title, required this.onSubmit, this.fixedClinicianId, this.onChanged});
  final ApiClient apiClient;
  final String title;
  final String? fixedClinicianId;
  final Future<void> Function(String slotId) onSubmit;
  final VoidCallback? onChanged;
  @override
  State<_SlotSelectionPage> createState() => _SlotSelectionPageState();
}

class _SlotSelectionPageState extends State<_SlotSelectionPage> {
  late final AppointmentsApi _api = AppointmentsApi(widget.apiClient);
  List<ClinicianOption> _clinicians = const [];
  List<AppointmentSlot> _slots = const [];
  String? _clinicianId;
  String? _selectedSlotId;
  DateTime _date = DateTime.now();
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _clinicianId = widget.fixedClinicianId?.isNotEmpty == true ? widget.fixedClinicianId : null;
    if (_clinicianId == null) {
      _loadClinicians();
    } else {
      _loadSlots();
    }
  }

  Future<void> _loadClinicians() async {
    try {
      final values = await _api.clinicians();
      if (!mounted) return;
      setState(() { _clinicians = values; _loading = false; });
    } on ApiException catch (error) {
      if (mounted) setState(() { _error = error.message; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _error = '의료진 목록을 불러오지 못했습니다.'; _loading = false; });
    }
  }

  Future<void> _loadSlots() async {
    final clinicianId = _clinicianId;
    if (clinicianId == null || clinicianId.isEmpty) return;
    setState(() { _loading = true; _error = null; _selectedSlotId = null; });
    try {
      final values = await _api.slots(clinicianId, _date);
      if (mounted) setState(() { _slots = values; _loading = false; });
    } on ApiException catch (error) {
      if (mounted) setState(() { _slots = const []; _error = error.message; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _slots = const []; _error = '예약 가능 시간을 불러오지 못했습니다.'; _loading = false; });
    }
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(context: context, initialDate: _date, firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 365)));
    if (selected != null) { _date = selected; await _loadSlots(); }
  }

  Future<void> _submit() async {
    final slotId = _selectedSlotId;
    if (slotId == null || _submitting) return;
    setState(() => _submitting = true);
    try {
      await widget.onSubmit(slotId);
      widget.onChanged?.call();
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (error) {
      if (mounted) setState(() { _error = error.message; _submitting = false; });
    } catch (_) {
      if (mounted) setState(() => _error = '요청을 처리하지 못했습니다.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.title)),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      if (widget.fixedClinicianId == null) DropdownButtonFormField<String>(
        value: _clinicianId,
        decoration: const InputDecoration(labelText: '담당 의료진'),
        items: _clinicians.map((item) => DropdownMenuItem(value: item.id, child: Text('${item.name} · ${item.department}'))).toList(),
        onChanged: (value) { setState(() => _clinicianId = value); if (value != null) _loadSlots(); },
      ),
      const SizedBox(height: 12),
      OutlinedButton.icon(onPressed: _pickDate, icon: const Icon(Icons.calendar_today_outlined), label: Text('${_date.year}.${_date.month}.${_date.day}')),
      const SizedBox(height: 16),
      if (_loading) const Center(child: CircularProgressIndicator())
      else if (_error != null) _StateCard.error(message: _error!, onRetry: _loadSlots)
      else if (_slots.isEmpty) const _StateCard.empty(icon: Icons.event_busy_outlined, title: '예약 가능한 시간이 없습니다.', description: '다른 날짜 또는 의료진을 선택해 주세요.')
      else Wrap(spacing: 8, runSpacing: 8, children: _slots.map((slot) => ChoiceChip(
        selected: _selectedSlotId == slot.id,
        label: Text(slot.startAt?.toLocal().toString().substring(11, 16) ?? '-'),
        onSelected: (_) => setState(() => _selectedSlotId = slot.id),
      )).toList()),
      const SizedBox(height: 20),
      FilledButton(onPressed: _selectedSlotId == null || _submitting ? null : _submit, child: Text(_submitting ? '처리 중...' : '확인')),
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
          Icon(icon, color: _primary, size: 34),
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
