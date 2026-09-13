import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/widgets.dart';

import 'app/patient_app.dart';
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

  final token =
      await FirebaseMessaging.instance.getToken();

  debugPrint('BRAINON_FCM_TOKEN=$token');

  FirebaseMessaging.instance.onTokenRefresh.listen(
    (newToken) {
      debugPrint(
        'BRAINON_FCM_TOKEN_REFRESH=$newToken',
      );
    },
  );

  FirebaseMessaging.onMessage.listen(
    (message) {
      debugPrint(
        'BRAINON_FCM_FOREGROUND_MESSAGE='
        '${message.messageId}',
      );

      debugPrint(
        'BRAINON_FCM_TITLE='
        '${message.notification?.title}',
      );

      debugPrint(
        'BRAINON_FCM_BODY='
        '${message.notification?.body}',
      );
    },
  );
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await initializeFirebaseMessaging();

  runApp(
    const PatientApp(),
  );
}
