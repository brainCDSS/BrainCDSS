import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'clinician_session.dart';

class StoredClinicianSession {
  const StoredClinicianSession(this.refreshToken, this.user);
  final String refreshToken;
  final ClinicianUser user;
}

class ClinicianAuthStorage {
  ClinicianAuthStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _storage;
  static const _refresh = 'brainon.clinician.auth.refresh';
  static const _user = 'brainon.clinician.auth.user';

  Future<void> save(ClinicianSession session) async {
    await _storage.write(key: _refresh, value: session.refreshToken);
    await _storage.write(key: _user, value: jsonEncode(session.user.toJson()));
  }

  Future<StoredClinicianSession?> read() async {
    final refresh = await _storage.read(key: _refresh);
    final rawUser = await _storage.read(key: _user);
    if (refresh == null || refresh.isEmpty || rawUser == null) return null;
    try {
      return StoredClinicianSession(
        refresh,
        ClinicianUser.fromJson(Map<String, dynamic>.from(jsonDecode(rawUser))),
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> clear() async {
    await _storage.delete(key: _refresh);
    await _storage.delete(key: _user);
  }
}
