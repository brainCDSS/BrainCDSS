import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../../core/notifications/clinician_fcm_service.dart';
import '../radiology/widgets/radiology_ui.dart';

/// Notification transport is intentionally not connected yet: the current
/// backend runtime does not reliably scope RADIOLOGY notifications by recipient.
class RadiologyNotificationsPage extends StatefulWidget {
  const RadiologyNotificationsPage({
    super.key,
    required this.apiClient,
    this.onOpenConsultation,
    this.onOpenAnalysis,
  });

  final ClinicianApiClient apiClient;
  final ValueChanged<String>? onOpenConsultation;
  final Future<void> Function(String analysisId)? onOpenAnalysis;

  @override
  State<RadiologyNotificationsPage> createState() =>
      _RadiologyNotificationsPageState();
}

class _RadiologyNotificationsPageState
    extends State<RadiologyNotificationsPage> {
  List<RadiologyNotificationItem> _notifications = const [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await widget.apiClient.get('/api/v1/notifications');
      final notifications = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => RadiologyNotificationItem.fromJson(
              Map<String, dynamic>.from(item)))
          .toList(growable: false);
      if (mounted) setState(() => _notifications = notifications);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '알림을 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _openNotification(RadiologyNotificationItem notification) async {
    if (!notification.isRead) {
      try {
        await widget.apiClient
            .patch('/api/v1/notifications/${notification.id}/read');
      } catch (_) {
        _showMessage('알림을 읽음 처리하지 못했습니다.');
        return;
      }
      if (!mounted) return;
      setState(() => notification.isRead = true);
    }
    final category = notification.category.trim().toUpperCase();
    if (category == 'CONSULTATION') {
      final consultationId = notification.data['consultation_id']?.toString();
      if (consultationId == null || consultationId.isEmpty) {
        _showMessage('협진 상세 정보를 확인할 수 없습니다.');
        return;
      }
      widget.onOpenConsultation?.call(consultationId);
      return;
    }
    if (category == 'AI_ANALYSIS') {
      final analysisId = await _analysisIdFor(notification);
      if (!mounted) return;
      if (analysisId == null) {
        _showMessage('분석 결과 식별자를 확인할 수 없습니다.');
        return;
      }
      final openAnalysis = widget.onOpenAnalysis;
      if (openAnalysis == null) {
        _showMessage('분석 결과 화면을 열 수 없습니다.');
        return;
      }
      await openAnalysis(analysisId);
    }
  }

  Future<String?> _analysisIdFor(RadiologyNotificationItem notification) async {
    final directId = ClinicianFcmService.analysisIdFromData(notification.data);
    if (directId != null) return directId;

    var page = 1;
    final visitedPages = <int>{};
    try {
      while (visitedPages.add(page)) {
        final response = await widget.apiClient.get(
          '/api/v1/notifications',
          query: {'category': 'AI_ANALYSIS', 'page': '$page'},
        );
        for (final item in response['results'] as List? ?? const []) {
          if (item is! Map) continue;
          final row = Map<String, dynamic>.from(item);
          if (row['id']?.toString() != notification.id) continue;
          final data = Map<String, dynamic>.from(row['data'] as Map? ?? const {});
          return ClinicianFcmService.analysisIdFromData(data);
        }
        final next = int.tryParse(response['next']?.toString() ?? '');
        if (next == null) return null;
        page = next;
      }
    } on ClinicianApiException {
      _showMessage('알림 정보를 다시 확인하지 못했습니다.');
    } catch (_) {
      _showMessage('알림 정보를 다시 확인하지 못했습니다.');
    }
    return null;
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
          RadiologySectionTitle(title: '알림센터'),
          SizedBox(height: 8),
          Text(
            '업무 관련 알림을 확인할 수 있습니다.',
            style: TextStyle(color: radiologyMuted, fontSize: 13),
          ),
          SizedBox(height: 18),
          _NotificationFilterBar(),
          SizedBox(height: 14),
          if (_isLoading)
            Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_error != null)
            _NotificationRetryCard(message: _error!, onRetry: _load)
          else if (_notifications.isEmpty)
            RadiologyEmptyState(
              icon: Icons.notifications_none_rounded,
              message: '표시할 알림이 없습니다.',
            )
          else
            ..._notifications.map(
              (notification) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _NotificationCard(
                  notification: notification,
                  onTap: () => _openNotification(notification),
                ),
              ),
            ),
        ],
      );
}

class RadiologyNotificationItem {
  RadiologyNotificationItem({
    required this.id,
    required this.category,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
    required this.data,
  });

  factory RadiologyNotificationItem.fromJson(Map<String, dynamic> json) =>
      RadiologyNotificationItem(
        id: json['id']?.toString() ?? '',
        category: json['category']?.toString() ?? 'SYSTEM',
        title: json['title']?.toString() ?? '',
        body: json['body']?.toString() ?? '',
        isRead: json['is_read'] == true,
        createdAt: json['created_at']?.toString() ?? '',
        data: Map<String, dynamic>.from(json['data'] as Map? ?? const {}),
      );

  final String id;
  final String category;
  final String title;
  final String body;
  bool isRead;
  final String createdAt;
  final Map<String, dynamic> data;
}

class _NotificationRetryCard extends StatelessWidget {
  const _NotificationRetryCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(message, textAlign: TextAlign.center),
          TextButton(onPressed: onRetry, child: const Text('다시 시도')),
        ]),
      );
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notification, required this.onTap});

  final RadiologyNotificationItem notification;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: RadiologyInfoCard(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              notification.isRead
                  ? Icons.notifications_none_rounded
                  : Icons.notifications_rounded,
              color: notification.isRead ? radiologyMuted : radiologyBlue,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      RadiologyStatusChip(
                        label:
                            _notificationCategoryLabel(notification.category),
                        color: radiologyBlue,
                      ),
                      const Spacer(),
                      Text(
                        notification.isRead ? '읽음' : '읽지 않음',
                        style: TextStyle(
                          color: notification.isRead
                              ? radiologyMuted
                              : radiologyBlue,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 9),
                  Text(
                    notification.title,
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    notification.body,
                    style: const TextStyle(color: radiologyMuted, fontSize: 13),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _formatNotificationDateTime(notification.createdAt),
                    style: const TextStyle(color: radiologyMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      ));
}

String _notificationCategoryLabel(String category) => switch (category) {
      'AI_ANALYSIS' => 'AI 분석',
      'CONSULTATION' => '협진',
      'EMERGENCY' => '응급',
      'IMAGING' => '영상',
      'APPOINTMENT' => '예약',
      'SYSTEM' => '시스템',
      _ => category,
    };

String _formatNotificationDateTime(String value) {
  final parsed = DateTime.tryParse(value);
  if (parsed == null) return value;
  final seoul = parsed.toUtc().add(const Duration(hours: 9));
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${seoul.year}.${twoDigits(seoul.month)}.${twoDigits(seoul.day)} '
      '${twoDigits(seoul.hour)}:${twoDigits(seoul.minute)}';
}

class _NotificationFilterBar extends StatelessWidget {
  const _NotificationFilterBar();

  @override
  Widget build(BuildContext context) => Row(
        children: const [
          _FilterChip(label: '전체', selected: true),
          SizedBox(width: 8),
          _FilterChip(label: '읽지 않음'),
        ],
      );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({required this.label, this.selected = false});

  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFFEAF2FF) : Colors.white,
          border: Border.all(color: radiologyBorder),
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? radiologyBlue : radiologyMuted,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
}
