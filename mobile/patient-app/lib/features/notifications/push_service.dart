import 'dart:io';
import 'dart:math';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/api/api_client.dart';

class PatientPushService {
  PatientPushService(this.client, this.navigatorKey) : _storage = const FlutterSecureStorage();
  final ApiClient client;
  final GlobalKey<NavigatorState> navigatorKey;
  final FlutterSecureStorage _storage;
  static const _deviceKey = 'brainon.patient.device.id';
  static const _tokenIdKey = 'brainon.patient.fcm.token-id';
  bool _listenersInstalled = false;

  Future<String> _deviceId() async {
    final existing = await _storage.read(key: _deviceKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final value = 'mobile-${DateTime.now().microsecondsSinceEpoch.toRadixString(16)}-${Random.secure().nextInt(1 << 32).toRadixString(16)}';
    await _storage.write(key: _deviceKey, value: value);
    return value;
  }

  Future<void> connect() async {
    await FirebaseMessaging.instance.requestPermission(alert: true, badge: true, sound: true);
    await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(alert: true, badge: true, sound: true);
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null && token.isNotEmpty) await _register(token);
    if (!_listenersInstalled) {
      _listenersInstalled = true;
      FirebaseMessaging.instance.onTokenRefresh.listen(_register);
      FirebaseMessaging.onMessage.listen((message) {
        // The navigator key remains owned by the live root MaterialApp.
        // ignore: use_build_context_synchronously
        final context = navigatorKey.currentContext;
        if (context == null) return;
        // ignore: use_build_context_synchronously
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(message.notification?.title ?? '새 알림이 도착했습니다.'),
          action: SnackBarAction(label: '보기', onPressed: () { _open(message.data); }),
        ));
      });
      FirebaseMessaging.onMessageOpenedApp.listen((message) { _open(message.data); });
    }
    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) WidgetsBinding.instance.addPostFrameCallback((_) => _open(initial.data));
  }

  Future<void> _register(String token) async {
    final response = await client.post('/api/v1/devices/fcm-tokens', body: {
      'device_id': await _deviceId(), 'platform': Platform.isIOS ? 'IOS' : 'ANDROID', 'token': token,
    });
    final id = response['token_id']?.toString();
    if (id != null && id.isNotEmpty) await _storage.write(key: _tokenIdKey, value: id);
  }

  Future<void> disconnect() async {
    final id = await _storage.read(key: _tokenIdKey);
    if (id != null && id.isNotEmpty) {
      try { await client.delete('/api/v1/devices/fcm-tokens/$id'); } catch (_) {}
    }
    await _storage.delete(key: _tokenIdKey);
  }

  Future<void> _open(Map<String, dynamic> data) async {
    final notificationId = data['notification_id']?.toString();
    if (notificationId != null && notificationId.isNotEmpty) {
      try { await client.patch('/api/v1/notifications/$notificationId/read'); } catch (_) {}
    }
    navigatorKey.currentState?.pushNamed('/notifications', arguments: data);
  }
}
