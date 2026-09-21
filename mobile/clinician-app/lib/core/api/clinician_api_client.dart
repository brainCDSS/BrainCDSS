import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

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
  Future<String?> Function()? _tokenRefresher;
  Future<String?>? _refreshing;

  void setAccessToken(String? token) {
    _accessToken = token;
  }

  void setTokenRefresher(Future<String?> Function()? refresher) => _tokenRefresher = refresher;

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? query,
  }) async {
    final response = await _requestWithRefresh(
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
    final response = await _requestWithRefresh(
      'POST',
      Uri.parse('$baseUrl$path'),
      authenticated: authenticated,
      body: body,
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> patch(String path, {Map<String, dynamic>? body}) async =>
      _decode(await _requestWithRefresh('PATCH', Uri.parse('$baseUrl$path'), body: body));

  Future<void> delete(String path) async {
    _decode(await _requestWithRefresh('DELETE', Uri.parse('$baseUrl$path')));
  }

  Future<_ApiResponse> _requestWithRefresh(String method, Uri uri,
      {Map<String, dynamic>? body, bool authenticated = true, bool retry = true}) async {
    final response = await _request(method, uri, body: body, authenticated: authenticated);
    if (response.statusCode != 401 || !authenticated || !retry || _tokenRefresher == null) return response;
    _refreshing ??= _tokenRefresher!().whenComplete(() => _refreshing = null);
    final token = await _refreshing;
    if (token == null || token.isEmpty) return response;
    _accessToken = token;
    return _request(method, uri, body: body, authenticated: authenticated);
  }

  Map<String, String> _headers({bool authenticated = true}) => {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
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
    final isLoginRequest = uri.path == '/api/v1/auth/login';
    try {
      if (isLoginRequest) {
        debugPrint('CLINICIAN LOGIN REQUEST URL: $uri');
      }
      final request = await client.openUrl(method, uri);
      _headers(authenticated: authenticated).forEach(
        request.headers.set,
      );
      if (body != null) {
        final bodyBytes = utf8.encode(jsonEncode(body));
        request.contentLength = bodyBytes.length;
        request.add(bodyBytes);
      }
      final response = await request.close();
      final bytes = <int>[];
      await for (final chunk in response) {
        bytes.addAll(chunk);
      }
      if (isLoginRequest) {
        debugPrint('CLINICIAN LOGIN HTTP STATUS: ${response.statusCode}');
        debugPrint(
          'CLINICIAN LOGIN RESPONSE BODY: ${_redactedResponseBody(bytes)}',
        );
      }
      return _ApiResponse(response.statusCode, bytes);
    } catch (error) {
      if (isLoginRequest) {
        debugPrint('CLINICIAN LOGIN NETWORK ERROR: $error');
      }
      rethrow;
    } finally {
      client.close(force: true);
    }
  }

  String _redactedResponseBody(List<int> bytes) {
    final text = utf8.decode(bytes, allowMalformed: true);
    try {
      final decoded = jsonDecode(text);
      if (decoded is Map) {
        final body = Map<String, dynamic>.from(decoded);
        if (body.containsKey('access')) {
          body['access'] = '[REDACTED]';
        }
        if (body.containsKey('refresh')) {
          body['refresh'] = '[REDACTED]';
        }
        return jsonEncode(body);
      }
    } on FormatException {
      // Error responses are logged as received when they are not JSON.
    }
    return text;
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
