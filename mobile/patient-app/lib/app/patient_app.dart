import 'package:brainon_mobile_core/brainon_mobile_core.dart';
import 'package:flutter/material.dart';
import 'patient_main_shell.dart';

class PatientApp extends StatelessWidget {
  const PatientApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'BrainOn Patient',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF356FAF)),
          scaffoldBackgroundColor: const Color(0xFFF6F8FB),
          useMaterial3: true,
        ),
        home: const PatientMainShell(),
        navigatorObservers: [NoopNavigationObserver()],
      );
}
