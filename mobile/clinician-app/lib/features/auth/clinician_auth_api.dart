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
    return ClinicianSession.fromJson(response);
  }
}
