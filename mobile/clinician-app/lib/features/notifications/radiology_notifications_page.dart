import 'package:flutter/material.dart';

import '../radiology/widgets/radiology_ui.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';

/// Notification transport is intentionally not connected yet: the current
/// backend runtime does not reliably scope RADIOLOGY notifications by recipient.
class RadiologyNotificationsPage extends StatelessWidget {
  const RadiologyNotificationsPage({
    super.key,
    this.notifications = const [],
    this.isLoading = false,
  });

  final List<RadiologyNotificationItem> notifications;
  final bool isLoading;

  @override
  Widget build(BuildContext context) => Scaffold(
        drawer: const RadiologyNavigationDrawer(),
        appBar: AppBar(title: const Text('알림')),
        body: ListView(
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
            if (isLoading)
              Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (notifications.isEmpty)
              RadiologyEmptyState(
                icon: Icons.notifications_none_rounded,
                message: '표시할 알림이 없습니다.',
              )
            else
              ...notifications.map(
                (notification) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _NotificationCard(notification: notification),
                ),
              ),
          ],
        ),
      );
}

class RadiologyNotificationItem {
  const RadiologyNotificationItem({
    required this.category,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
  });

  final String category;
  final String title;
  final String body;
  final bool isRead;
  final String createdAt;
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notification});

  final RadiologyNotificationItem notification;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
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
                        label: notification.category,
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
                    notification.createdAt,
                    style: const TextStyle(color: radiologyMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
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
