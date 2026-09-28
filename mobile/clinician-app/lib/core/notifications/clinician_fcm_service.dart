import 'dart:async';
import 'dart:math';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/clinician_api_client.dart';

class ClinicianFcmService {
  ClinicianFcmService._();

  static final instance = ClinicianFcmService._();
  static const _deviceIdKey = 'clinician_fcm_device_id';

  ClinicianApiClient? _apiClient;
  String? _tokenId;
  void Function(RemoteMessage message)? onForegroundMessage;
  void Function(String consultationId)? onConsultationTap;
  FutureOr<void> Function(String analysisId)? onAnalysisTap;
  VoidCallback? onNotificationsTap;
  String? _pendingConsultationId;
  String? _pendingAnalysisId;
  StreamSubscription<String>? _tokenRefreshSubscription;

  Future<void> register(ClinicianApiClient apiClient) async {
    _apiClient = apiClient;
    try {
      debugPrint('BRAINON_FCM_REGISTER_START');
      final token = await FirebaseMessaging.instance.getToken();
      if (token != null && token.isNotEmpty) await _registerToken(token);
      await _tokenRefreshSubscription?.cancel();
      _tokenRefreshSubscription = FirebaseMessaging.instance.onTokenRefresh.listen(
        (token) => _registerToken(token),
      );
      debugPrint('BRAINON_FCM_REGISTER_COMPLETE');
    } on Object catch (error, stackTrace) {
      debugPrint('BRAINON_FCM_REGISTER_FAILED=$error');
      debugPrintStack(stackTrace: stackTrace);
    }
  }

  Future<void> unregister() async {
    final apiClient = _apiClient;
    final tokenId = _tokenId;
    _apiClient = null;
    _tokenId = null;
    await _tokenRefreshSubscription?.cancel();
    _tokenRefreshSubscription = null;
    if (apiClient != null && tokenId != null && tokenId.isNotEmpty) {
      try {
        await apiClient.delete('/api/v1/devices/fcm-tokens/$tokenId');
      } on Object catch (error) {
        debugPrint('FCM token deactivation failed: $error');
      }
    }
  }

  void handleMessage(RemoteMessage message) {
    _logSafeMessageMetadata('foreground', message);
    onForegroundMessage?.call(message);
  }

  void handleMessageTap(RemoteMessage message) {
    _logSafeMessageMetadata('tap', message);
    final category = message.data['category']?.toString().trim().toUpperCase();
    final eventType = message.data['event_type']?.toString().trim().toUpperCase();
    if (category == 'AI_ANALYSIS' ||
        (eventType ?? '').startsWith('AI_ANALYSIS')) {
      final analysisId = analysisIdFromData(message.data);
      if (analysisId == null || analysisId.isEmpty) {
        openNotifications();
        return;
      }
      openAnalysis(analysisId);
      return;
    }

    final consultationId = message.data['consultation_id']?.toString();
    if (consultationId != null && consultationId.isNotEmpty) {
      final callback = onConsultationTap;
      if (callback == null) {
        _pendingConsultationId = consultationId;
      } else {
        callback(consultationId);
      }
    }
  }

  void bindConsultationNavigation(void Function(String consultationId) callback) {
    onConsultationTap = callback;
    final pending = _pendingConsultationId;
    _pendingConsultationId = null;
    if (pending != null) callback(pending);
  }

  void bindNotificationsNavigation(VoidCallback callback) {
    onNotificationsTap = callback;
  }

  void bindAnalysisNavigation(FutureOr<void> Function(String analysisId) callback) {
    onAnalysisTap = callback;
    final pending = _pendingAnalysisId;
    _pendingAnalysisId = null;
    if (pending != null) callback(pending);
  }

  void openNotifications() {
    onNotificationsTap?.call();
  }

  void openAnalysis(String analysisId) {
    if (analysisId.isEmpty) return;
    final callback = onAnalysisTap;
    if (callback == null) {
      _pendingAnalysisId = analysisId;
    } else {
      callback(analysisId);
    }
  }

  static String? analysisIdFromData(Map<String, dynamic> data) {
    final analysisId = data['analysis_id']?.toString().trim();
    if (analysisId != null && analysisId.isNotEmpty) return analysisId;
    final resourceType = data['resource_type']?.toString().trim();
    if (resourceType?.toUpperCase() != 'AIANALYSIS') return null;
    final resourceId = data['resource_id']?.toString().trim();
    return resourceId == null || resourceId.isEmpty ? null : resourceId;
  }

  void _logSafeMessageMetadata(String source, RemoteMessage message) {
    final data = message.data;
    final title = message.notification?.title;
    final body = message.notification?.body;
    debugPrint(
      'BRAINON_FCM_MESSAGE '
      'source=$source '
      'category=${data['category']?.toString().trim() ?? '<missing>'} '
      'event_type=${data['event_type']?.toString().trim() ?? '<missing>'} '
      'status=${data['status']?.toString().trim() ?? '<missing>'} '
      'analysis_status=${data['analysis_status']?.toString().trim() ?? '<missing>'} '
      'analysis_id_present=${data['analysis_id']?.toString().trim().isNotEmpty == true} '
      'resource_type=${data['resource_type']?.toString().trim() ?? '<missing>'} '
      'resource_id_present=${data['resource_id']?.toString().trim().isNotEmpty == true} '
      'notification_id_present=${data['notification_id']?.toString().trim().isNotEmpty == true} '
      'notification_title_present=${title?.trim().isNotEmpty == true} '
      'notification_body_present=${body?.trim().isNotEmpty == true}',
    );
  }

  Future<void> _registerToken(String token) async {
    final apiClient = _apiClient;
    if (apiClient == null || token.isEmpty) return;
    try {
      debugPrint('BRAINON_FCM_TOKEN_POST_START');
      final response = await apiClient.post('/api/v1/devices/fcm-tokens', body: {
        'device_id': await _deviceId(),
        'platform': 'ANDROID',
        'token': token,
      });
      _tokenId = response['token_id']?.toString();
      debugPrint('BRAINON_FCM_TOKEN_POST_COMPLETE');
    } on Object catch (error) {
      debugPrint('FCM token registration failed: $error');
    }
  }

  Future<String> _deviceId() async {
    final preferences = await SharedPreferences.getInstance();
    final existing = preferences.getString(_deviceIdKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final random = Random.secure();
    final value = List.generate(32, (_) => random.nextInt(16).toRadixString(16)).join();
    await preferences.setString(_deviceIdKey, value);
    return value;
  }
}
