// Entry point for the independently released clinician application.
import 'package:flutter/material.dart';
import 'package:brainon_mobile_core/brainon_mobile_core.dart';
void main() => runApp(const ClinicianApp());
class ClinicianApp extends StatelessWidget {
  const ClinicianApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'BrainOn Clinician',
    home: Scaffold(
      appBar: AppBar(title: const Text('BrainOn Clinician')),
      body: const Center(child: Text('Clinician app shell is ready.')),
    ),
    navigatorObservers: [NoopNavigationObserver()],
  );
}
