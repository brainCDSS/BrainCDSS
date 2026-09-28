import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import 'auth_api.dart';
import 'auth_session.dart';
import 'signup_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.apiClient,
    required this.onLoginSuccess,
  });

  final ApiClient apiClient;
  final Future<void> Function(AuthSession) onLoginSuccess;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _loginIdController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  @override
  void dispose() {
    _loginIdController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final loginId = _loginIdController.text.trim();
    final password = _passwordController.text;

    if (loginId.isEmpty || password.isEmpty) {
      setState(() {
        _errorMessage = '아이디와 비밀번호를 입력해 주세요.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authApi = AuthApi(widget.apiClient);

      final session = await authApi.login(
        loginId: loginId,
        password: password,
      );

      if (!mounted) return;

      await widget.onLoginSuccess(session);
    } on ApiException catch (error) {
      if (!mounted) return;

      setState(() {
        if (error.statusCode == 401) {
          _errorMessage = '아이디 또는 비밀번호를 확인해 주세요.';
        } else {
          _errorMessage = error.message;
        }
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _errorMessage = '서버에 연결할 수 없습니다.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const brandBlue = Color(0xFF356FAF);
    const inputBorder = OutlineInputBorder(
      borderRadius: BorderRadius.all(Radius.circular(12)),
      borderSide: BorderSide(color: Color(0xFFC9DDF2)),
    );

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: 28,
              vertical: 32,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                maxWidth: 420,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: SizedBox(
                      width: 152,
                      height: 152,
                      child: Image.asset(
                        'assets/images/hojjang_main.png',
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'HODOC',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.headlineMedium?.copyWith(
                      color: brandBlue,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '내 건강을 더 가깝게, HODOC',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFF75849A),
                    ),
                  ),
                  const SizedBox(height: 36),
                  TextField(
                    controller: _loginIdController,
                    enabled: !_isLoading,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: '아이디',
                      hintText: '아이디를 입력하세요',
                      prefixIcon: Icon(
                        Icons.person_outline_rounded,
                      ),
                      border: inputBorder,
                      enabledBorder: inputBorder,
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.all(Radius.circular(12)),
                        borderSide: BorderSide(color: brandBlue, width: 1.5),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _passwordController,
                    enabled: !_isLoading,
                    obscureText: _obscurePassword,
                    onSubmitted: (_) {
                      if (!_isLoading) {
                        _login();
                      }
                    },
                    decoration: InputDecoration(
                      labelText: '비밀번호',
                      hintText: '비밀번호를 입력하세요',
                      prefixIcon: const Icon(
                        Icons.lock_outline_rounded,
                      ),
                      border: inputBorder,
                      enabledBorder: inputBorder,
                      focusedBorder: const OutlineInputBorder(
                        borderRadius: BorderRadius.all(Radius.circular(12)),
                        borderSide: BorderSide(color: brandBlue, width: 1.5),
                      ),
                      suffixIcon: IconButton(
                        onPressed: () {
                          setState(() {
                            _obscurePassword = !_obscurePassword;
                          });
                        },
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                      ),
                    ),
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 14),
                    Text(
                      _errorMessage!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _isLoading ? null : _login,
                    style: FilledButton.styleFrom(
                      backgroundColor: brandBlue,
                      foregroundColor: Colors.white,
                    ),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        vertical: 14,
                      ),
                      child: _isLoading
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Text(
                              '로그인',
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: _isLoading
                        ? null
                        : () async {
                            final signedUp = await Navigator.of(context)
                                .push<bool>(MaterialPageRoute(
                                    builder: (_) => SignupPage(
                                        apiClient: widget.apiClient)));
                            if (signedUp == true && mounted)
                              ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text('회원가입이 완료되었습니다.')));
                          },
                    style: TextButton.styleFrom(foregroundColor: brandBlue),
                    child: const Text('계정이 없으신가요? 회원가입'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
