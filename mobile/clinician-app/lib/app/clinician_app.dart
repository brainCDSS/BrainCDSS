import 'package:brainon_mobile_core/brainon_mobile_core.dart';
import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../features/auth/clinician_auth_api.dart';
import '../features/auth/clinician_login_page.dart';
import '../features/auth/clinician_session.dart';
import '../features/auth/clinician_auth_storage.dart';
import '../features/notifications/push_service.dart';
import '../features/notifications/radiology_notifications_page.dart';
import 'neurology_main_shell.dart';
import 'radiology_main_shell.dart';
import 'clinical_role_main_shell.dart';

class ClinicianApp extends StatefulWidget {
  const ClinicianApp({super.key});

  @override
  State<ClinicianApp> createState() => _ClinicianAppState();
}

class _ClinicianAppState extends State<ClinicianApp> {
  final _apiClient = ClinicianApiClient();
  final _navigatorKey = GlobalKey<NavigatorState>();
  final _authStorage = ClinicianAuthStorage();
  ClinicianSession? _session;
  late final ClinicianPushService _pushService;
  bool _restoring = true;

  @override
  void initState() {
    super.initState();
    _pushService = ClinicianPushService(_apiClient, _navigatorKey);
    _apiClient.setTokenRefresher(_refreshAccessToken);
    _restoreSession();
  }

  Future<void> _onAuthenticated(ClinicianSession session) async {
    _apiClient.setAccessToken(session.accessToken);
    await _authStorage.save(session);
    setState(() => _session = session);
    await _pushService.connect();
  }

  Future<String?> _refreshAccessToken() async {
    try {
      final stored = await _authStorage.read();
      if (stored == null) return null;
      return await ClinicianAuthApi(_apiClient).refresh(stored.refreshToken);
    } catch (_) {
      await _clearSession();
      return null;
    }
  }

  Future<void> _restoreSession() async {
    try {
      final stored = await _authStorage.read();
      if (stored == null) return;
      final access =
          await ClinicianAuthApi(_apiClient).refresh(stored.refreshToken);
      if (!mounted) return;
      setState(() => _session = ClinicianSession(
            accessToken: access,
            refreshToken: stored.refreshToken,
            user: stored.user,
          ));
      await _pushService.connect();
    } catch (_) {
      await _clearSession();
    } finally {
      if (mounted) setState(() => _restoring = false);
    }
  }

  Future<void> _logout() async {
    await _pushService.disconnect();
    final stored = await _authStorage.read();
    if (stored != null) {
      try {
        await ClinicianAuthApi(_apiClient).logout(stored.refreshToken);
      } catch (_) {}
    }
    await _clearSession();
  }

  Future<void> _clearSession() async {
    await _authStorage.clear();
    _apiClient.setAccessToken(null);
    if (mounted) setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        navigatorKey: _navigatorKey,
        title: 'Brain On',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF2563B8),
            brightness: Brightness.light,
          ),
          scaffoldBackgroundColor: const Color(0xFFF6F8FC),
          appBarTheme: const AppBarTheme(
            backgroundColor: Colors.white,
            foregroundColor: Color(0xFF172B4D),
            surfaceTintColor: Colors.white,
            elevation: 0,
          ),
        ),
        home: _restoring
            ? const Scaffold(body: Center(child: CircularProgressIndicator()))
            : _home(),
        onGenerateRoute: (settings) {
          if (settings.name == '/notifications' && _session != null) {
            return MaterialPageRoute<void>(
              builder: (_) => RadiologyNotificationsPage(apiClient: _apiClient),
            );
          }
          return null;
        },
        navigatorObservers: [NoopNavigationObserver()],
      );

  Widget _home() {
    final session = _session;
    if (session == null) {
      return ClinicianLoginPage(
        authApi: ClinicianAuthApi(_apiClient),
        onAuthenticated: _onAuthenticated,
      );
    }
    if (session.user.role.code == 'RADIOLOGY') {
      return RadiologyMainShell(
        apiClient: _apiClient,
        user: session.user,
        onLogout: _logout,
      );
    }
    if (session.user.role.code == 'NEUROLOGIST') {
      return NeurologyMainShell(
          apiClient: _apiClient, user: session.user, onLogout: _logout);
    }
    if (session.user.role.code == 'NURSE' ||
        session.user.role.code == 'NEUROSURGEON') {
      return ClinicalRoleMainShell(
        apiClient: _apiClient,
        user: session.user,
        onLogout: _logout,
      );
    }
    return _UnsupportedRolePage(roleName: session.user.role.name);
  }
}

class _UnsupportedRolePage extends StatelessWidget {
  const _UnsupportedRolePage({required this.roleName});

  final String roleName;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              '$roleName 역할은 아직 이 앱에서 지원하지 않습니다.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
}
