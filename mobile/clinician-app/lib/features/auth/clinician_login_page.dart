import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import 'clinician_auth_api.dart';
import 'clinician_session.dart';

class ClinicianLoginPage extends StatefulWidget {
  const ClinicianLoginPage({
    super.key,
    required this.authApi,
    required this.onAuthenticated,
  });

  final ClinicianAuthApi authApi;
  final ValueChanged<ClinicianSession> onAuthenticated;

  @override
  State<ClinicianLoginPage> createState() => _ClinicianLoginPageState();
}

class _ClinicianLoginPageState extends State<ClinicianLoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _loginIdController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isSubmitting = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      debugPrint('BRAINON_LOGIN_PAGE_FIRST_FRAME');
    });
  }

  @override
  void dispose() {
    _loginIdController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || _isSubmitting) {
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      final session = await widget.authApi.login(
        loginId: _loginIdController.text.trim(),
        password: _passwordController.text,
      );

      if (!mounted) {
        return;
      }

      widget.onAuthenticated(session);
    } on ClinicianApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.message),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('로그인 중 오류가 발생했습니다.'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    debugPrint('BRAINON_LOGIN_PAGE_BUILD');
    return Scaffold(
      backgroundColor: const Color(0xFFF3F7FC),
      resizeToAvoidBottomInset: true,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 로그인 배경 이미지
          Opacity(
            opacity: 0.55,
            child: Transform.translate(
              offset: const Offset(0, 40), //하단 호랑이 이미지 위치
              child: Image.asset(
                'asset/images/login.png',
                fit: BoxFit.cover,
                width: double.infinity,
                height: double.infinity,
                alignment: Alignment.center,
                errorBuilder: (_, __, ___) => const SizedBox.shrink(),
              ),
            ),
          ),

          // 배경 이미지 위 오버레이
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0x55F3F7FC),
                  Color(0x99F3F7FC),
                ],
              ),
            ),
          ),

          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 24,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: 420,
                  ),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Brain On',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Color(0xFF172B4D),
                            fontSize: 32,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.8,
                          ),
                        ),

                        const SizedBox(height: 10),

                        const Text(
                          '의료진을 위한 통합 진료 지원 플랫폼',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Color(0xFF263247),
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),

                        const SizedBox(height: 5),

                        const Text(
                          '환자 · 영상 · AI · 협진을 하나의 워크플로우에서',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Color(0xFF667085),
                            fontSize: 13,
                          ),
                        ),

                        const SizedBox(height: 28),

                        // 로그인 카드
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.96),
                            borderRadius: BorderRadius.circular(22),
                            boxShadow: const [
                              BoxShadow(
                                color: Color(0x1A365D8D),
                                blurRadius: 24,
                                offset: Offset(0, 10),
                              ),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const Text(
                                '로그인',
                                style: TextStyle(
                                  color: Color(0xFF172B4D),
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 18),
                              TextFormField(
                                controller: _loginIdController,
                                textInputAction: TextInputAction.next,
                                decoration: _loginInputDecoration(
                                  labelText: '아이디',
                                ),
                                validator: (value) {
                                  if (value == null || value.trim().isEmpty) {
                                    return '아이디를 입력해 주세요.';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 14),
                              TextFormField(
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                onFieldSubmitted: (_) => _submit(),
                                decoration: _loginInputDecoration(
                                  labelText: '비밀번호',
                                  suffixIcon: IconButton(
                                    onPressed: () {
                                      setState(() {
                                        _obscurePassword = !_obscurePassword;
                                      });
                                    },
                                    icon: Icon(
                                      _obscurePassword
                                          ? Icons.visibility_off_outlined
                                          : Icons.visibility_outlined,
                                    ),
                                  ),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return '비밀번호를 입력해 주세요.';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 24),
                              FilledButton(
                                onPressed: _isSubmitting ? null : _submit,
                                style: FilledButton.styleFrom(
                                  minimumSize: const Size.fromHeight(52),
                                  backgroundColor: const Color(0xFF4F8FE8),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                ),
                                child: _isSubmitting
                                    ? const SizedBox(
                                        width: 20,
                                        height: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Text(
                                        '로그인',
                                        style: TextStyle(
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

InputDecoration _loginInputDecoration({
  required String labelText,
  Widget? suffixIcon,
}) {
  return InputDecoration(
    labelText: labelText,
    suffixIcon: suffixIcon,
    filled: true,
    fillColor: const Color(0xFFF9FBFE),
    contentPadding: const EdgeInsets.symmetric(
      horizontal: 14,
      vertical: 16,
    ),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(
        color: Color(0xFFE4EBF3),
      ),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(
        color: Color(0xFFE4EBF3),
      ),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(
        color: Color(0xFF4F8FE8),
        width: 1.5,
      ),
    ),
  );
}
