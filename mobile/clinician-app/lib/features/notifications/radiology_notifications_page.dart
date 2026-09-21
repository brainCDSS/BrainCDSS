import 'package:flutter/material.dart';
import '../../core/api/clinician_api_client.dart';
import 'notifications_api.dart';

class RadiologyNotificationsPage extends StatefulWidget {
  const RadiologyNotificationsPage({super.key, required this.apiClient});
  final ClinicianApiClient apiClient;
  @override
  State<RadiologyNotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<RadiologyNotificationsPage> {
  late final ClinicianNotificationsApi api = ClinicianNotificationsApi(widget.apiClient);
  List<Map<String, dynamic>> items = const [];
  Map<String, dynamic>? preferences;
  bool loading = true;
  String? error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final result = await api.list();
      final prefs = await api.preferences();
      if (!mounted) return;
      setState(() {
        items = (result['results'] as List? ?? const []).whereType<Map>()
            .map((value) => Map<String, dynamic>.from(value)).toList();
        preferences = prefs; loading = false; error = null;
      });
    } catch (_) {
      if (mounted) setState(() { loading = false; error = '알림을 불러오지 못했습니다.'; });
    }
  }

  Future<void> _read(Map<String, dynamic> item) async {
    if (item['is_read'] != true) await api.markRead(item['id'].toString());
    await _load();
  }

  Future<void> _toggleDnd(bool enabled) async {
    final dnd = Map<String, dynamic>.from(preferences?['dnd'] as Map? ?? const {});
    await api.updatePreferences({
      'dnd_enabled': enabled,
      'dnd_start': dnd['start'] ?? '22:00',
      'dnd_end': dnd['end'] ?? '07:00',
      'timezone': dnd['timezone'] ?? 'Asia/Seoul',
    });
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final dnd = Map<String, dynamic>.from(preferences?['dnd'] as Map? ?? const {});
    return Scaffold(
      appBar: AppBar(title: const Text('알림 센터')),
      body: RefreshIndicator(onRefresh: _load, child: ListView(
        physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.all(16),
        children: [
          if (preferences != null) SwitchListTile(
            title: const Text('방해 금지'), value: dnd['enabled'] == true,
            onChanged: _toggleDnd,
          ),
          if (loading) const Center(child: CircularProgressIndicator())
          else if (error != null) TextButton(onPressed: _load, child: Text('$error 다시 시도'))
          else if (items.isEmpty) const Padding(padding: EdgeInsets.all(32), child: Center(child: Text('새 알림이 없습니다.')))
          else ...items.map((item) => Card(child: ListTile(
            leading: Icon(item['is_read'] == true ? Icons.notifications_none : Icons.notifications_active),
            title: Text(item['title']?.toString() ?? ''),
            subtitle: Text(item['body']?.toString() ?? ''),
            onTap: () => _read(item),
          ))),
        ],
      )),
    );
  }
}
