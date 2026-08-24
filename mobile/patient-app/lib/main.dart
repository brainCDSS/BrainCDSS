// Entry point for the independently released patient application.
import 'package:flutter/material.dart';
import 'package:brainon_mobile_core/brainon_mobile_core.dart';
void main() => runApp(const PatientApp());
class PatientApp extends StatelessWidget {
  const PatientApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'BrainOn Patient',
    home: Scaffold(
      appBar: AppBar(title: const Text('BrainOn Patient')),
      body: const Center(child: Text('Patient app shell is ready.')),
    ),
    navigatorObservers: [NoopNavigationObserver()],
  );
}
