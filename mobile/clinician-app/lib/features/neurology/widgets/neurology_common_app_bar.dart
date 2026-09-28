import 'package:flutter/material.dart';

class NeurologyCommonAppBar extends StatelessWidget
    implements PreferredSizeWidget {
  const NeurologyCommonAppBar({
    super.key,
    required this.screenTitle,
    required this.onNotifications,
    this.onBack,
  });

  final String screenTitle;
  final VoidCallback onNotifications;
  final VoidCallback? onBack;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) => AppBar(
        leading: onBack == null
            ? null
            : IconButton(
                tooltip: '뒤로가기',
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: onBack,
              ),
        titleSpacing: onBack == null ? 20 : 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Brain On',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
            const SizedBox(height: 1),
            Text(screenTitle,
                style: const TextStyle(
                    color: Color(0xFF60718A),
                    fontSize: 12,
                    fontWeight: FontWeight.w600)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: '알림',
            onPressed: onNotifications,
            icon: const Icon(Icons.notifications_none_rounded),
          ),
          const SizedBox(width: 4),
        ],
      );
}
