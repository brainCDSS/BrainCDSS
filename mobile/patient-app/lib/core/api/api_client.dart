import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.message,
  });

  final int statusCode;
  final String message;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({
    String? accessToken,
  }) : _accessToken = accessToken;

  static const String baseUrl = String.fromEnvironment(
    'BACKEND_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  String? _accessToken;
  Future<String?> Function()? _tokenRefresher;
  Future<String?>? _refreshing;

  void setAccessToken(String? token) {
    _accessToken = token;
  }

  void setTokenRefresher(Future<String?> Function()? refresher) {
    _tokenRefresher = refresher;
  }

  Map<String, String> get _headers => {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (_accessToken != null)
          'Authorization': 'Bearer $_accessToken',
      };

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? query,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: query,
    );

    final response = await _requestWithRefresh(
      () => http.get(uri, headers: _headers),
    );

    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    bool retryOnUnauthorized = true,
  }) async {
    final uri = Uri.parse('$baseUrl$path');

    final response = await _requestWithRefresh(
      () => http.post(
        uri,
        headers: _headers,
        body: jsonEncode(body ?? {}),
      ),
      retryOnUnauthorized: retryOnUnauthorized,
    );

    // 실패할 때만 응답 본문 출력
    // 로그인 성공 응답에는 JWT가 있으므로 출력하지 않음
    if (response.statusCode < 200 ||
        response.statusCode >= 300) {
    }

    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> patch(
    String path, {
    Map<String, dynamic>? body,
    void Function(int statusCode, Map<String, dynamic> body)? onSuccess,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await _requestWithRefresh(
      () => http.patch(
        uri,
        headers: _headers,
        body: jsonEncode(body ?? {}),
      ),
    );
    final data = _decodeResponse(response);
    onSuccess?.call(response.statusCode, data);
    return data;
  }

  Future<void> delete(String path) async {
    final response = await _requestWithRefresh(
      () => http.delete(Uri.parse('$baseUrl$path'), headers: _headers),
    );
    _decodeResponse(response);
  }

  Future<http.Response> _requestWithRefresh(
    Future<http.Response> Function() request, {
    bool retryOnUnauthorized = true,
  }) async {
    final response = await request();
    if (response.statusCode != 401 || !retryOnUnauthorized) {
      return response;
    }

    final refresher = _tokenRefresher;
    if (refresher == null) return response;

    _refreshing ??= refresher().whenComplete(() => _refreshing = null);
    final refreshedToken = await _refreshing;
    if (refreshedToken == null || refreshedToken.isEmpty) return response;

    return request();
  }

  Map<String, dynamic> _decodeResponse(
    http.Response response,
  ) {
    Map<String, dynamic> data = {};

    if (response.bodyBytes.isNotEmpty) {
      try {
        final decoded = jsonDecode(
          utf8.decode(response.bodyBytes),
        );

        if (decoded is Map) {
          data = Map<String, dynamic>.from(decoded);
        }
      } catch (_) {
        if (response.statusCode < 200 ||
            response.statusCode >= 300) {
          throw ApiException(
            statusCode: response.statusCode,
            message:
                '서버 응답을 처리할 수 없습니다. (${response.statusCode})',
          );
        }

        rethrow;
      }
    }

    if (response.statusCode < 200 ||
        response.statusCode >= 300) {
      throw ApiException(
        statusCode: response.statusCode,
        message: _extractErrorMessage(data),
      );
    }

    return data;
  }

  String _extractErrorMessage(
    Map<String, dynamic> data,
  ) {
    // 현재 BrainOn Backend 공통 에러 구조:
    // {
    //   "error": {
    //     "code": "...",
    //     "message": "...",
    //     "details": ...
    //   },
    //   "trace_id": "..."
    // }

    final error = data['error'];

    if (error is Map) {
      final details = error['details'];

      if (details is Map) {
        final detail = details['detail'];

        if (detail is Map) {
          return detail['detail']?.toString() ??
              detail['code']?.toString() ??
              error['message']?.toString() ??
              'API 요청에 실패했습니다.';
        }

        if (detail != null) {
          return detail.toString();
        }
      }

      return error['message']?.toString() ??
          error['code']?.toString() ??
          'API 요청에 실패했습니다.';
    }

    // 이전 형식도 대응
    final detail = data['detail'];

    if (detail is Map) {
      return detail['detail']?.toString() ??
          detail['code']?.toString() ??
          'API 요청에 실패했습니다.';
    }

    if (detail != null) {
      return detail.toString();
    }

    return 'API 요청에 실패했습니다.';
  }
}
