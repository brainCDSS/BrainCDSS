import 'package:flutter/material.dart';

// Brain On 웹 `styles/global.css` 공통 light theme 토큰과 동일한 값입니다.
const radiologyNavy = Color(0xFF263247);
const radiologyMuted = Color(0xFF667085);
const radiologyBlue = Color(0xFF4F8FE8);
const radiologyBorder = Color(0xFFE4EBF3);
const radiologyPageBackground = Color(0xFFF3F7FC);
const radiologySuccess = Color(0xFF2F7D4C);
const radiologyWarning = Color(0xFFB45309);
const radiologyDanger = Color(0xFFB42318);

class RadiologySectionTitle extends StatelessWidget {
  const RadiologySectionTitle({super.key, required this.title, this.action});

  final String title;
  final String? action;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                color: radiologyNavy,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          if (action != null)
            Text(
              action!,
              style: const TextStyle(
                color: radiologyBlue,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
        ],
      );
}

class RadiologyStatusChip extends StatelessWidget {
  const RadiologyStatusChip({super.key, required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.11),
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(
          label,
          style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w800),
        ),
      );
}

class RadiologyInfoCard extends StatelessWidget {
  const RadiologyInfoCard({super.key, required this.child, this.padding = const EdgeInsets.all(16)});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Card(
        margin: EdgeInsets.zero,
        elevation: 0,
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: radiologyBorder),
        ),
        child: Padding(padding: padding, child: child),
      );
}

class RadiologyEmptyState extends StatelessWidget {
  const RadiologyEmptyState({super.key, required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: radiologyMuted, size: 38),
              const SizedBox(height: 12),
              Text(message, style: const TextStyle(color: radiologyMuted)),
            ],
          ),
        ),
      );
}
