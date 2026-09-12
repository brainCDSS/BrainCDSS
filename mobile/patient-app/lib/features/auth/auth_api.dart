import '../../core/api/api_client.dart';
import 'auth_session.dart';

class AuthApi {
  AuthApi(this.apiClient);

  final ApiClient apiClient;

  Future<AuthSession> login({
    required String loginId,
    required String password,
  }) async {
    final response = await apiClient.post(
      '/api/v1/auth/login',
      body: {
        'login_id': loginId,
        'password': password,
      },
    );

    final session = AuthSession.fromJson(
      response,
    );

    if (session.user.roleCode != 'PATIENT') {
      throw const ApiException(
        statusCode: 403,
        message: '환자 계정으로 로그인해 주세요.',
      );
    }

    apiClient.setAccessToken(
      session.accessToken,
    );

    return session;
  }
}
