import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';
import 'notifications_api.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  late final NotificationsApi _api = NotificationsApi(widget.apiClient);
  NotificationResponse? _data;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final value = await _api.list();
      if (mounted) setState(() => _data = value);
    } catch (_) {
      if (mounted) setState(() => _error = '알림을 불러오지 못했습니다.');
    }
  }

  Future<void> _read(PatientNotification item) async {
    if (item.isRead) return;
    try {
      await _api.markRead(item.id);
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.message)),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('알림센터')),
        body: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              if (_data == null && _error == null)
                const Center(child: CircularProgressIndicator())
              else if (_error != null)
                Center(
                  child: TextButton(
                    onPressed: _load,
                    child: Text('$_error 다시 시도'),
                  ),
                )
              else if (_data!.items.isEmpty)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('새로운 알림이 없습니다.'),
                  ),
                )
              else
                ..._data!.items.map(
                  (item) => Card(
                    child: ListTile(
                      leading: Icon(
                        item.isRead
                            ? Icons.notifications_none
                            : Icons.notifications_active,
                        color: item.severity == 'CRITICAL'
                            ? const Color(0xFFE94E4E)
                            : const Color(0xFF5665B8),
                      ),
                      title: Text(item.title),
                      subtitle: Text(item.body),
                      onTap: () => _read(item),
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
}
