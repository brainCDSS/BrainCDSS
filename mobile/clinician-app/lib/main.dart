import 'dart:async';
import 'dart:ui';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';

import 'app/clinician_app.dart';
import 'core/notifications/clinician_fcm_service.dart';
import 'firebase_options.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(
  RemoteMessage message,
) async {
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  debugPrint(
    'BRAINON_FCM_BACKGROUND_MESSAGE=${message.messageId}',
  );
}

Future<void> initializeFirebaseMessaging() async {
  debugPrint('BRAINON_FCM_INIT_START');
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  FirebaseMessaging.onBackgroundMessage(
    firebaseMessagingBackgroundHandler,
  );

  final settings =
      await FirebaseMessaging.instance.requestPermission(
    alert: true,
    badge: true,
    sound: true,
  );

  debugPrint(
    'BRAINON_FCM_PERMISSION=${settings.authorizationStatus}',
  );

  FirebaseMessaging.onMessage.listen(
    ClinicianFcmService.instance.handleMessage,
  );
  FirebaseMessaging.onMessageOpenedApp.listen(
    ClinicianFcmService.instance.handleMessageTap,
  );
  final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
  if (initialMessage != null) {
    ClinicianFcmService.instance.handleMessageTap(initialMessage);
  }
  debugPrint('BRAINON_FCM_INIT_COMPLETE');
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    debugPrint('BRAINON_FLUTTER_ERROR=${details.exceptionAsString()}');
    debugPrintStack(stackTrace: details.stack);
  };
  PlatformDispatcher.instance.onError = (error, stackTrace) {
    debugPrint('BRAINON_PLATFORM_ERROR=$error');
    debugPrintStack(stackTrace: stackTrace);
    return true;
  };
  debugPrint('BRAINON_APP_RUN');
  runApp(const ClinicianApp());
  debugPrint('BRAINON_APP_RUN_COMPLETE');
  WidgetsBinding.instance.addPostFrameCallback((_) {
    debugPrint('BRAINON_FIRST_FRAME_COMPLETE');
  });
  unawaited(_initializeFirebaseMessagingSafely());
}
Future<void> _initializeFirebaseMessagingSafely() async {
  try {
    await initializeFirebaseMessaging();
  } catch (error, stackTrace) {
    debugPrint('BRAINON_FCM_INIT_FAILED=$error');
    debugPrintStack(stackTrace: stackTrace);
  }
}
