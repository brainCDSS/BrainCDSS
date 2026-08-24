/// Public API for deliberately small, non-clinical mobile shared code.
library;
import 'package:flutter/widgets.dart';
/// Placeholder observer proving both apps consume the local shared package.
class NoopNavigationObserver extends NavigatorObserver {}
/// Central endpoint configuration; HTTP transport is added after contract approval.
class BrainOnEndpoints {
  const BrainOnEndpoints({required this.backendUrl});
  final Uri backendUrl;
}

