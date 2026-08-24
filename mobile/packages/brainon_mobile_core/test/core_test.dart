// Shared endpoint configuration test without network access.
import 'package:flutter_test/flutter_test.dart';
import 'package:brainon_mobile_core/brainon_mobile_core.dart';
void main() {
  test('retains backend origin', () {
    final endpoints=BrainOnEndpoints(backendUrl: Uri.parse('http://localhost:8080'));
    expect(endpoints.backendUrl.port, 8080);
  });
}
