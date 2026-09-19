import 'dart:convert';
import 'dart:io';

class ClinicianApiException implements Exception {
  const ClinicianApiException({
    required this.statusCode,
    required this.message,
  });

  final int statusCode;
  final String message;

  @override
  String toString() => message;
}

class ClinicianApiClient {
  ClinicianApiClient({String? accessToken}) : _accessToken = accessToken;

  static const baseUrl = String.fromEnvironment(
    'BACKEND_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  String? _accessToken;

  void setAccessToken(String? token) {
    _accessToken = token;
  }

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? query,
  }) async {
    final response = await _request(
      'GET',
      Uri.parse('$baseUrl$path').replace(queryParameters: query),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    bool authenticated = true,
  }) async {
    final response = await _request(
      'POST',
      Uri.parse('$baseUrl$path'),
      authenticated: authenticated,
      body: body,
    );
    return _decode(response);
  }

  Map<String, String> _headers({bool authenticated = true}) => {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (authenticated && _accessToken != null)
          'Authorization': 'Bearer $_accessToken',
      };

  Future<_ApiResponse> _request(
    String method,
    Uri uri, {
    Map<String, dynamic>? body,
    bool authenticated = true,
  }) async {
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, uri);
      _headers(authenticated: authenticated).forEach(
        request.headers.set,
      );
      if (body != null) {
        request.add(utf8.encode(jsonEncode(body)));
      }
      final response = await request.close();
      final bytes = <int>[];
      await for (final chunk in response) {
        bytes.addAll(chunk);
      }
      return _ApiResponse(response.statusCode, bytes);
    } finally {
      client.close(force: true);
    }
  }

  Map<String, dynamic> _decode(_ApiResponse response) {
    Map<String, dynamic> body = const <String, dynamic>{};
    if (response.bodyBytes.isNotEmpty) {
      try {
        final decoded = jsonDecode(utf8.decode(response.bodyBytes));
        if (decoded is Map) {
          body = Map<String, dynamic>.from(decoded);
        }
      } on FormatException {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          rethrow;
        }
      }
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ClinicianApiException(
        statusCode: response.statusCode,
        message: _message(body, response.statusCode),
      );
    }
    return body;
  }

  String _message(Map<String, dynamic> body, int statusCode) {
    final error = body['error'];
    if (error is Map) {
      return error['message']?.toString() ??
          error['detail']?.toString() ??
          error['code']?.toString() ??
          '요청을 처리하지 못했습니다. ($statusCode)';
    }
    return body['detail']?.toString() ??
        body['message']?.toString() ??
        '요청을 처리하지 못했습니다. ($statusCode)';
  }
}

class _ApiResponse {
  const _ApiResponse(this.statusCode, this.bodyBytes);

  final int statusCode;
  final List<int> bodyBytes;
}
