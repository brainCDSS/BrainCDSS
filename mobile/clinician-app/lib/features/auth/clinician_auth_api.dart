import 'package:flutter/foundation.dart';

import '../../core/api/clinician_api_client.dart';
import 'clinician_session.dart';

class ClinicianAuthApi {
  ClinicianAuthApi(this._client);

  final ClinicianApiClient _client;

  Future<ClinicianSession> login({
    required String loginId,
    required String password,
  }) async {
    final response = await _client.post(
      '/api/v1/auth/login',
      authenticated: false,
      body: {'login_id': loginId, 'password': password},
    );
    try {
      final session = ClinicianSession.fromJson(response);
      debugPrint(
        'CLINICIAN LOGIN PARSE SUCCESS: role=${session.user.role.code}',
      );
      return session;
    } catch (error) {
      debugPrint('CLINICIAN LOGIN PARSE ERROR: $error');
      rethrow;
    }
  }
}
