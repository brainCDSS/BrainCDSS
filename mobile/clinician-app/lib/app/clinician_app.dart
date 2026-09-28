import 'dart:async';

import 'package:brainon_mobile_core/brainon_mobile_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../core/notifications/clinician_fcm_service.dart';
import '../features/auth/clinician_auth_api.dart';
import '../features/auth/clinician_login_page.dart';
import '../features/auth/clinician_session.dart';
import 'neurology_main_shell.dart';
import 'radiology_main_shell.dart';

class ClinicianApp extends StatefulWidget {
  const ClinicianApp({super.key});

  @override
  State<ClinicianApp> createState() => _ClinicianAppState();
}

class _ClinicianAppState extends State<ClinicianApp> {
  final _apiClient = ClinicianApiClient();
  final _navigatorKey = GlobalKey<NavigatorState>();
  final _foregroundNotifications = <_ForegroundNotification>[];
  final _foregroundNotificationIds = <String>{};
  ClinicianSession? _session;
  bool _isForegroundDialogVisible = false;

  @override
  void initState() {
    super.initState();
    debugPrint('BRAINON_CLINICIAN_APP_INIT_STATE');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      debugPrint('BRAINON_CLINICIAN_APP_FIRST_FRAME');
    });
    ClinicianFcmService.instance.onForegroundMessage = _showForegroundMessage;
  }

  @override
  void dispose() {
    ClinicianFcmService.instance.onForegroundMessage = null;
    super.dispose();
  }

  void _showForegroundMessage(RemoteMessage message) {
    if (_session == null) return;

    unawaited(_enqueueForegroundMessage(message));
  }

  Future<void> _enqueueForegroundMessage(RemoteMessage message) async {
    var notification = _ForegroundNotification.fromMessage(message);
    if (notification.isAiAnalysis) {
      notification = await _resolveAiNotification(notification);
    }
    if (!mounted || _session == null) return;

    if (!_foregroundNotificationIds.add(notification.deduplicationId)) return;
    _foregroundNotifications.add(notification);
    unawaited(_showNextForegroundNotification());
  }

  Future<_ForegroundNotification> _resolveAiNotification(
    _ForegroundNotification notification,
  ) async {
    final notificationId = notification.notificationId;
    if (notificationId == null) return notification;
    try {
      final record = await _findNotification(notificationId);
      if (record == null || record.category != 'AI_ANALYSIS') {
        debugPrint('BRAINON_FCM_AI_LOOKUP_FOUND=false');
        return notification;
      }
      var resolved = _ForegroundNotification.fromMessage(
        notification.message,
        notificationData: record.data,
        notificationCategory: record.category,
      );
      final analysisId = resolved.analysisId;
      if (analysisId == null) {
        debugPrint('BRAINON_FCM_AI_LOOKUP_FOUND=true analysis_id_present=false');
        return resolved;
      }
      final analysis = await _apiClient.get('/api/v1/ai-analyses/$analysisId');
      if (analysis['analysis_id']?.toString() != analysisId) {
        debugPrint('BRAINON_FCM_AI_DETAIL_ID_MATCH=false');
        return resolved;
      }
      resolved = _ForegroundNotification.fromMessage(
        notification.message,
        notificationData: record.data,
        notificationCategory: record.category,
        analysisStatus: analysis['status']?.toString(),
      );
      debugPrint(
        'BRAINON_FCM_AI_LOOKUP_FOUND=true '
        'analysis_id_present=true '
        'analysis_status=${analysis['status']?.toString() ?? '<missing>'}',
      );
      return resolved;
    } on Object {
      debugPrint('BRAINON_FCM_AI_LOOKUP_FAILED');
      return notification;
    }
  }

  Future<_NotificationRecord?> _findNotification(String notificationId) async {
    var page = 1;
    final visitedPages = <int>{};
    while (visitedPages.add(page)) {
      final response = await _apiClient.get(
        '/api/v1/notifications',
        query: {'category': 'AI_ANALYSIS', 'page': '$page'},
      );
      for (final item in response['results'] as List? ?? const []) {
        if (item is! Map) continue;
        final row = Map<String, dynamic>.from(item);
        if (row['id']?.toString() != notificationId) continue;
        return _NotificationRecord(
          category: row['category']?.toString() ?? '',
          data: Map<String, dynamic>.from(row['data'] as Map? ?? const {}),
        );
      }
      final next = int.tryParse(response['next']?.toString() ?? '');
      if (next == null) return null;
      page = next;
    }
    return null;
  }

  Future<void> _showNextForegroundNotification() async {
    if (!mounted ||
        _isForegroundDialogVisible ||
        _foregroundNotifications.isEmpty) {
      return;
    }

    final context = _navigatorKey.currentContext;
    if (context == null) return;

    final notification = _foregroundNotifications.removeAt(0);
    _isForegroundDialogVisible = true;
    try {
      final shouldOpen = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => _ForegroundConsultationDialog(
          notification: notification,
          onLater: () => Navigator.of(dialogContext).pop(false),
          onOpen: () => Navigator.of(dialogContext).pop(true),
        ),
      );
      if (shouldOpen == true && mounted) {
        _openForegroundNotification(notification);
      }
    } finally {
      _isForegroundDialogVisible = false;
      if (mounted) _showNextForegroundNotification();
    }
  }

  void _openForegroundNotification(_ForegroundNotification notification) {
    if (notification.isAiAnalysis) {
      final analysisId = notification.analysisId;
      if (analysisId == null) {
        ClinicianFcmService.instance.openNotifications();
      } else {
        ClinicianFcmService.instance.openAnalysis(analysisId);
      }
      return;
    }
    final consultationId = notification.message.data['consultation_id']
        ?.toString()
        .trim();
    if (consultationId != null && consultationId.isNotEmpty) {
      ClinicianFcmService.instance.handleMessageTap(notification.message);
      return;
    }
    ClinicianFcmService.instance.openNotifications();
  }

  void _onAuthenticated(ClinicianSession session) {
    _apiClient.setAccessToken(session.accessToken);
    setState(() => _session = session);
    ClinicianFcmService.instance.register(_apiClient);
  }

  Future<void> _logout() async {
    await ClinicianFcmService.instance.unregister();
    _apiClient.setAccessToken(null);
    setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) {
    debugPrint('BRAINON_CLINICIAN_APP_BUILD');
    return MaterialApp(
        title: 'Brain On',
        debugShowCheckedModeBanner: false,
        navigatorKey: _navigatorKey,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF4F8FE8),
            brightness: Brightness.light,
          ),
          scaffoldBackgroundColor: const Color(0xFFF3F7FC),
          appBarTheme: const AppBarTheme(
            backgroundColor: Colors.white,
            foregroundColor: Color(0xFF172B4D),
            surfaceTintColor: Colors.white,
            elevation: 0,
          ),
        ),
        home: _home(),
        navigatorObservers: [NoopNavigationObserver()],
      );
  }

  Widget _home() {
    final session = _session;
    if (session == null) {
      debugPrint('BRAINON_LOGIN_PAGE_CREATE');
      return ClinicianLoginPage(
        authApi: ClinicianAuthApi(_apiClient),
        onAuthenticated: _onAuthenticated,
      );
    }
    if (session.user.role.code == 'RADIOLOGY') {
      return RadiologyMainShell(
        apiClient: _apiClient,
        user: session.user,
        onLogout: _logout,
      );
    }
    if (session.user.role.code == 'NEUROLOGIST') {
      return NeurologyMainShell(
        apiClient: _apiClient,
        user: session.user,
        onLogout: _logout,
      );
    }
    return _UnsupportedRolePage(roleName: session.user.role.name);
  }
}

class _UnsupportedRolePage extends StatelessWidget {
  const _UnsupportedRolePage({required this.roleName});

  final String roleName;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              '$roleName 역할은 아직 이 앱에서 지원하지 않습니다.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
}

class _ForegroundNotification {
  const _ForegroundNotification({
    required this.message,
    required this.deduplicationId,
    required this.title,
    required this.body,
    required this.actionLabel,
    required this.isAiAnalysis,
    required this.notificationId,
    required this.analysisId,
  });

  factory _ForegroundNotification.fromMessage(
    RemoteMessage message, {
    Map<String, dynamic>? notificationData,
    String? notificationCategory,
    String? analysisStatus,
  }) {
    final data = {...message.data, ...?notificationData};
    final eventType = data['event_type']?.toString().trim().toUpperCase();
    final category = (notificationCategory ?? data['category']?.toString() ?? '')
        .trim()
        .toUpperCase();
    final resolvedAnalysisStatus = (analysisStatus ??
            data['analysis_status'] ??
            data['status'])
        ?.toString()
        .trim()
        .toUpperCase();
    final isAiAnalysis =
        category == 'AI_ANALYSIS' ||
        (eventType ?? '').startsWith('AI_ANALYSIS');
    final content = isAiAnalysis
        ? switch ((eventType, resolvedAnalysisStatus)) {
            ('AI_ANALYSIS_COMPLETED', _) || (_, 'COMPLETED') => (
                'AI 영상 분석 완료',
                '요청한 영상 분석이 완료되었습니다.',
                '결과 확인',
              ),
            ('AI_ANALYSIS_FAILED', _) || (_, 'FAILED') => (
                'AI 영상 분석 실패',
                '요청한 영상 분석을 완료하지 못했습니다.',
                '확인',
              ),
            _ => ('AI 영상 분석 알림', '새로운 AI 영상 분석 알림이 도착했습니다.', '확인'),
          }
        : switch (eventType) {
      'CONSULTATION_REQUESTED' => (
        '새로운 협진 요청',
        '확인이 필요한 협진 요청이 도착했습니다.',
        '협진 확인',
      ),
      'CONSULTATION_RESPONDED' => (
        '협진 회신 도착',
        '요청한 협진에 대한 회신이 도착했습니다.',
        '협진 확인',
      ),
      'CONSULTATION_ACCEPTED' => ('협진 요청 수락', '협진 요청이 수락되었습니다.', '협진 확인'),
      'CONSULTATION_REJECTED' => ('협진 요청 거절', '협진 요청이 거절되었습니다.', '협진 확인'),
      _ => ('새 알림', '새로운 알림이 도착했습니다.', '확인'),
    };
    final notificationId = data['notification_id']?.toString().trim();
    final deduplicationId = message.messageId?.trim().isNotEmpty == true
        ? message.messageId!.trim()
        : notificationId?.isNotEmpty == true
        ? notificationId!
        : '${eventType ?? ''}:${data['consultation_id'] ?? data['analysis_id'] ?? ''}:${message.sentTime?.microsecondsSinceEpoch ?? ''}';

    return _ForegroundNotification(
      message: message,
      deduplicationId: deduplicationId,
      title: content.$1,
      body: content.$2,
      actionLabel: content.$3,
      isAiAnalysis: isAiAnalysis,
      notificationId: notificationId?.isEmpty == true ? null : notificationId,
      analysisId: ClinicianFcmService.analysisIdFromData(data),
    );
  }

  final RemoteMessage message;
  final String deduplicationId;
  final String title;
  final String body;
  final String actionLabel;
  final bool isAiAnalysis;
  final String? notificationId;
  final String? analysisId;
}

class _NotificationRecord {
  const _NotificationRecord({required this.category, required this.data});

  final String category;
  final Map<String, dynamic> data;
}

class _ForegroundConsultationDialog extends StatelessWidget {
  const _ForegroundConsultationDialog({
    required this.notification,
    required this.onLater,
    required this.onOpen,
  });

  final _ForegroundNotification notification;
  final VoidCallback onLater;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) => Dialog(
    insetPadding: const EdgeInsets.symmetric(horizontal: 24),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 420),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: const BoxDecoration(
                color: Color(0xFFEAF2FF),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.notifications_active_outlined,
                color: Color(0xFF4F8FE8),
                size: 28,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              notification.title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF172B4D),
                fontSize: 19,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              notification.body,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF60718A),
                fontSize: 14,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: onLater,
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      foregroundColor: const Color(0xFF36577B),
                      side: const BorderSide(color: Color(0xFFC8D8EC)),
                    ),
                    child: const Text('나중에'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton(
                    onPressed: onOpen,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      backgroundColor: const Color(0xFF4F8FE8),
                    ),
                    child: Text(notification.actionLabel),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    ),
  );
}
