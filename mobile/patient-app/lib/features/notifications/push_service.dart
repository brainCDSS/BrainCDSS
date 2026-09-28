import 'dart:io';
import 'dart:convert';
import 'dart:math';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/api/api_client.dart';
import '../medications/patient_prescriptions_api.dart';
import 'notifications_api.dart';

class PatientPushService {
  PatientPushService(
    this.client,
    this.navigatorKey, {
    this.onOpenMedicationReminder,
    this.onOpenAppointmentReminder,
  }) : _storage = const FlutterSecureStorage();

  final ApiClient client;
  final GlobalKey<NavigatorState> navigatorKey;
  final Future<void> Function([DateTime? scheduledAt])? onOpenMedicationReminder;
  final Future<void> Function()? onOpenAppointmentReminder;
  final FlutterSecureStorage _storage;
  static const _deviceKey = 'brainon.patient.device.id';
  static const _tokenIdKey = 'brainon.patient.fcm.token-id';
  bool _listenersInstalled = false;
  bool _medicationDialogOpen = false;

  Future<String> _deviceId() async {
    final existing = await _storage.read(key: _deviceKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final value =
        'mobile-${DateTime.now().microsecondsSinceEpoch.toRadixString(16)}-${Random.secure().nextInt(1 << 32).toRadixString(16)}';
    await _storage.write(key: _deviceKey, value: value);
    return value;
  }

  Future<void> connect() async {
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null && token.isNotEmpty) await _register(token);
    if (!_listenersInstalled) {
      _listenersInstalled = true;
      FirebaseMessaging.instance.onTokenRefresh.listen(_register);
      FirebaseMessaging.onMessage.listen((message) {
        notificationRefreshNotifier.value++;
        final context = navigatorKey.currentContext;
        if (context == null) return;
        if (_isMedicationReminder(message.data)) {
          _showMedicationReminderDialog(context, message.data);
          return;
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              message.notification?.body ?? '새 알림이 도착했습니다.',
            ),
            action: SnackBarAction(
              label: '보기',
              onPressed: () => _open(message.data),
            ),
          ),
        );
      });
      FirebaseMessaging.onMessageOpenedApp.listen((message) => _open(message.data));
    }
    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _open(initial.data));
    }
  }

  Future<void> _register(String token) async {
    final response = await client.post('/api/v1/devices/fcm-tokens', body: {
      'device_id': await _deviceId(),
      'platform': Platform.isIOS ? 'IOS' : 'ANDROID',
      'token': token,
    });
    final id = response['token_id']?.toString();
    if (id != null && id.isNotEmpty) {
      await _storage.write(key: _tokenIdKey, value: id);
    }
  }

  Future<void> disconnect() async {
    final id = await _storage.read(key: _tokenIdKey);
    if (id != null && id.isNotEmpty) {
      try {
        await client.delete('/api/v1/devices/fcm-tokens/$id');
      } catch (_) {}
    }
    await _storage.delete(key: _tokenIdKey);
  }

  Future<void> _open(Map<String, dynamic> data) async {
    final notificationId = data['notification_id']?.toString();
    if (notificationId != null && notificationId.isNotEmpty) {
      try {
        await client.patch('/api/v1/notifications/$notificationId/read');
        notificationRefreshNotifier.value++;
      } catch (_) {}
    }
    if (_opensMedicationManagement(data) && onOpenMedicationReminder != null) {
      await onOpenMedicationReminder!(_scheduledAt(data));
      return;
    }
    if (_opensAppointmentManagement(data) && onOpenAppointmentReminder != null) {
      await onOpenAppointmentReminder!();
      return;
    }
    navigatorKey.currentState?.pushNamed('/notifications', arguments: data);
  }

  Future<void> _showMedicationReminderDialog(
    BuildContext context,
    Map<String, dynamic> data,
  ) async {
    if (_medicationDialogOpen) return;
    _medicationDialogOpen = true;
    final count = _medicationReminderCount(data);
    final message = count == null
        ? '지금 복용할 약이 있어요.\n복약 일정을 확인해 주세요.'
        : '지금 복용할 약이 ${count}개 있어요.\n복약 일정을 확인해 주세요.';
    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('복약 시간이에요'),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('나중에'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
                _open(data);
              },
              child: const Text('확인하기'),
            ),
          ],
        ),
      );
    } finally {
      _medicationDialogOpen = false;
    }
  }

  bool _isMedicationReminder(Map<String, dynamic> data) =>
      data['category']?.toString().toUpperCase() == 'MEDICATION' &&
      data['event_type']?.toString() == 'MEDICATION_REMINDER';

  int? _medicationReminderCount(Map<String, dynamic> data) {
    final raw = data['medication_schedules'];
    if (raw is List) return raw.length;
    if (raw is String) {
      try {
        final parsed = jsonDecode(raw);
        if (parsed is List) return parsed.length;
      } catch (_) {}
    }
    return null;
  }

  bool _opensMedicationManagement(Map<String, dynamic> data) {
    final category = data['category']?.toString().toUpperCase();
    final eventType = data['event_type']?.toString();
    if (category == 'PRESCRIPTION' && eventType == 'PRESCRIPTION_FINALIZED') {
      final prescriptionId = data['prescription_id']?.toString().trim();
      return prescriptionId != null && prescriptionId.isNotEmpty;
    }

    if (category != 'MEDICATION' || eventType != 'MEDICATION_REMINDER') {
      return false;
    }

    final scheduleId = data['medication_schedule_id']?.toString().trim();
    return scheduleId != null && scheduleId.isNotEmpty;
  }

  bool _opensAppointmentManagement(Map<String, dynamic> data) =>
      data['category']?.toString().toUpperCase() == 'APPOINTMENT' &&
      data['event_type']?.toString() == 'APPOINTMENT_REMINDER';

  DateTime? _scheduledAt(Map<String, dynamic> data) =>
      parseSeoulDateTime(data['scheduled_at']);
}
