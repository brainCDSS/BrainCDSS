import 'package:brainon_mobile_core/brainon_mobile_core.dart';
import 'package:flutter/material.dart';

import '../core/api/api_client.dart';
import '../features/auth/auth_session.dart';
import '../features/auth/auth_api.dart';
import '../features/auth/auth_storage.dart';
import '../features/auth/login_page.dart';
import 'patient_main_shell.dart';

class PatientApp extends StatefulWidget {
  const PatientApp({super.key, this.authStorage});

  final AuthStorage? authStorage;

  @override
  State<PatientApp> createState() => _PatientAppState();
}

class _PatientAppState extends State<PatientApp> {
  final ApiClient _apiClient = ApiClient();

  AuthSession? _session;
  late final AuthStorage _authStorage;
  bool _restoringSession = true;

  @override
  void initState() {
    super.initState();
    _authStorage = widget.authStorage ?? SecureAuthStorage();
    _apiClient.setTokenRefresher(_refreshAccessToken);
    _restoreSession();
  }

  Future<void> _handleLoginSuccess(AuthSession session) async {
    await _authStorage.save(session);
    if (!mounted) return;
    setState(() {
      _session = session;
    });
  }

  Future<void> _restoreSession() async {
    try {
      final stored = await _authStorage.read();
      if (stored == null) return;

      final accessToken = await AuthApi(_apiClient).refresh(
        stored.refreshToken,
      );
      await _authStorage.updateAccessToken(accessToken);
      if (!mounted) return;
      setState(() {
        _session = AuthSession(
          accessToken: accessToken,
          refreshToken: stored.refreshToken,
          user: stored.user,
        );
      });
    } catch (_) {
      await _authStorage.clear();
      _apiClient.setAccessToken(null);
    } finally {
      if (mounted) {
        setState(() => _restoringSession = false);
      }
    }
  }

  Future<String?> _refreshAccessToken() async {
    try {
      final stored = await _authStorage.read();
      if (stored == null) return null;
      final accessToken = await AuthApi(_apiClient).refresh(
        stored.refreshToken,
      );
      await _authStorage.updateAccessToken(accessToken);
      return accessToken;
    } catch (_) {
      await _clearAuthentication();
      return null;
    }
  }

  Future<void> _logout() async {
    final stored = await _authStorage.read();
    if (stored != null) {
      try {
        await AuthApi(_apiClient).logout(stored.refreshToken);
      } catch (_) {
        // 서버 로그아웃 실패와 무관하게 이 기기의 인증 정보는 제거한다.
      }
    }
    await _clearAuthentication();
  }

  Future<void> _clearAuthentication() async {
    await _authStorage.clear();
    _apiClient.setAccessToken(null);

    if (mounted) {
      setState(() => _session = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xFF8B96E8);
    const primaryDark = Color(0xFF5665B8);
    const background = Color(0xFFF8F9FC);
    const surface = Color(0xFFFFFFFF);
    const textPrimary = Color(0xFF263A5A);
    const textSecondary = Color(0xFF65758D);
    const border = Color(0xFFCFD7E8);
    const emergency = Color(0xFFE94E4E);

    final colorScheme = ColorScheme.fromSeed(
      seedColor: primary,
      brightness: Brightness.light,
    ).copyWith(
      primary: primary,
      onPrimary: Colors.white,
      secondary: primaryDark,
      surface: surface,
      error: emergency,
    );

    return MaterialApp(
      title: 'BrainOn Patient',
      debugShowCheckedModeBanner: false,
      color: primary,
      navigatorObservers: [
        NoopNavigationObserver(),
      ],
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: colorScheme,
        scaffoldBackgroundColor: background,
        textTheme: const TextTheme(
          headlineSmall: TextStyle(
            color: textPrimary,
            fontWeight: FontWeight.w800,
          ),
          titleLarge: TextStyle(
            color: textPrimary,
            fontWeight: FontWeight.w800,
          ),
          titleMedium: TextStyle(
            color: textPrimary,
            fontWeight: FontWeight.w700,
          ),
          bodyLarge: TextStyle(
            color: textPrimary,
          ),
          bodyMedium: TextStyle(
            color: textPrimary,
          ),
          bodySmall: TextStyle(
            color: textSecondary,
          ),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: surface,
          foregroundColor: textPrimary,
          elevation: 0,
          centerTitle: false,
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: surface,
          indicatorColor: primary.withValues(alpha: 0.20),
          labelTextStyle: WidgetStateProperty.resolveWith(
            (states) {
              if (states.contains(
                WidgetState.selected,
              )) {
                return const TextStyle(
                  color: primaryDark,
                  fontWeight: FontWeight.w700,
                );
              }

              return const TextStyle(
                color: textSecondary,
              );
            },
          ),
        ),
        cardTheme: const CardThemeData(
          color: surface,
          elevation: 0,
          margin: EdgeInsets.zero,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: surface,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 16,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(
              color: border,
            ),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(
              color: border,
            ),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(
              color: primaryDark,
              width: 1.5,
            ),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: primaryDark,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
      ),
      home: _restoringSession
          ? const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            )
          : _session == null
              ? LoginPage(
                  apiClient: _apiClient,
                  onLoginSuccess: _handleLoginSuccess,
                )
              : PatientMainShell(
                  apiClient: _apiClient,
                  session: _session!,
                  onLogout: _logout,
                ),
    );
  }
}
