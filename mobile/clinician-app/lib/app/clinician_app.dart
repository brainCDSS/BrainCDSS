import 'package:brainon_mobile_core/brainon_mobile_core.dart';
import 'package:flutter/material.dart';

import '../core/api/clinician_api_client.dart';
import '../features/auth/clinician_auth_api.dart';
import '../features/auth/clinician_login_page.dart';
import '../features/auth/clinician_session.dart';
import 'neurology_main_shell.dart';
import 'radiology_main_shell.dart';

class ClinicianApp extends StatefulWidget {
  const ClinicianApp({super.key});

  @override
  State<ClinicianApp> createState() => _ClinicianAppState();
}

class _ClinicianAppState extends State<ClinicianApp> {
  final _apiClient = ClinicianApiClient();
  ClinicianSession? _session;

  void _onAuthenticated(ClinicianSession session) {
    _apiClient.setAccessToken(session.accessToken);
    setState(() => _session = session);
  }

  void _logout() {
    _apiClient.setAccessToken(null);
    setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
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
        home: _home(),
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
