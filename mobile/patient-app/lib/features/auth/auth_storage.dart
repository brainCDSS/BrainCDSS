import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_session.dart';

abstract class AuthStorage {
  Future<void> save(AuthSession session);

  Future<void> updateAccessToken(String accessToken);

  Future<StoredAuthSession?> read();

  Future<void> clear();
}

class StoredAuthSession {
  const StoredAuthSession({
    required this.refreshToken,
    required this.user,
  });

  final String refreshToken;
  final AuthUser user;
}

class SecureAuthStorage implements AuthStorage {
  SecureAuthStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _accessTokenKey = 'brainon.patient.auth.access';
  static const _refreshTokenKey = 'brainon.patient.auth.refresh';
  static const _userKey = 'brainon.patient.auth.user';

  final FlutterSecureStorage _storage;

  @override
  Future<void> save(AuthSession session) async {
    await _storage.write(key: _accessTokenKey, value: session.accessToken);
    await _storage.write(key: _refreshTokenKey, value: session.refreshToken);
    await _storage.write(
      key: _userKey,
      value: jsonEncode(session.user.toJson()),
    );
  }

  @override
  Future<void> updateAccessToken(String accessToken) =>
      _storage.write(key: _accessTokenKey, value: accessToken);

  @override
  Future<StoredAuthSession?> read() async {
    final values = await _storage.readAll();
    final refreshToken = values[_refreshTokenKey];
    final userValue = values[_userKey];

    if (refreshToken == null || refreshToken.isEmpty || userValue == null) {
      return null;
    }

    try {
      final decoded = jsonDecode(userValue);
      if (decoded is! Map) return null;
      final user = AuthUser.fromJson(Map<String, dynamic>.from(decoded));
      if (user.roleCode != 'PATIENT') return null;
      return StoredAuthSession(refreshToken: refreshToken, user: user);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> clear() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _refreshTokenKey),
      _storage.delete(key: _userKey),
    ]);
  }
}
