import 'package:flutter/material.dart';

import '../radiology/widgets/radiology_ui.dart';

/// API/RBAC contract가 마련되기 전 공통 AI 도우미 진입 화면입니다.
class ClinicianAiAssistantPage extends StatelessWidget {
  const ClinicianAiAssistantPage({super.key});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: RadiologyInfoCard(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: const Color(0xFFEAF2FF),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Icon(
                    Icons.smart_toy_outlined,
                    color: radiologyBlue,
                    size: 28,
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'AI 도우미',
                  style: TextStyle(
                    color: radiologyNavy,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'AI 도우미 기능을 준비하고 있습니다.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: radiologyMuted, height: 1.45),
                ),
              ],
            ),
          ),
        ),
      );
}
