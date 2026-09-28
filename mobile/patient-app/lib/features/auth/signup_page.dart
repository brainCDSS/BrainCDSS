import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import 'auth_api.dart';

class SignupPage extends StatefulWidget {
  const SignupPage({
    super.key,
    required this.apiClient,
  });

  final ApiClient apiClient;

  @override
  State<SignupPage> createState() => _SignupPageState();
}

class _SignupPageState extends State<SignupPage> {
  final _accountForm = GlobalKey<FormState>();
  final _profileForm = GlobalKey<FormState>();

  final _name = TextEditingController();
  final _rrn = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _id = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  int _step = 0;
  bool _loading = false;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  String? _error;

  @override
  void dispose() {
    for (final controller in [
      _name,
      _rrn,
      _email,
      _phone,
      _id,
      _password,
      _confirm,
    ]) {
      controller.dispose();
    }

    super.dispose();
  }

  void _next() {
    if (_accountForm.currentState!.validate()) {
      setState(() {
        _step = 1;
        _error = null;
      });
    }
  }

  Future<void> _submit() async {
    if (!_profileForm.currentState!.validate() || _loading) {
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await AuthApi(widget.apiClient).patientSignup(
        name: _name.text.trim(),
        residentRegistrationNumber: _rrn.text.trim(),
        email: _email.text.trim(),
        phone: _phone.text.trim(),
        loginId: _id.text.trim(),
        password: _password.text,
      );

      if (!mounted) {
        return;
      }

      Navigator.pop(context, true);
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = _signupErrorMessage(error);
      });
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = '회원가입을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  String _signupErrorMessage(ApiException error) {
    final message = error.message.toLowerCase();

    if (message.contains('resident registration') ||
        message.contains('resident_registration_number')) {
      return '주민등록번호를 다시 확인해 주세요.';
    }

    if (message.contains('login_id') ||
        message.contains('login id') ||
        message.contains('username')) {
      return '이미 사용 중인 아이디이거나 사용할 수 없는 아이디입니다.';
    }

    if (message.contains('email')) {
      return '이메일 정보를 다시 확인해 주세요.';
    }

    if (message.contains('password')) {
      return '비밀번호 형식을 다시 확인해 주세요.';
    }

    if (message.contains('phone')) {
      return '휴대폰 번호를 다시 확인해 주세요.';
    }

    if (message.contains('required') ||
        message.contains('blank') ||
        message.contains('validation')) {
      return '필수 입력 항목을 다시 확인해 주세요.';
    }

    if (error.statusCode == 409) {
      return '이미 등록된 정보가 있습니다. 입력한 내용을 확인해 주세요.';
    }

    if (error.statusCode >= 500) {
      return '회원가입을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.';
    }

    return '입력한 정보를 다시 확인해 주세요.';
  }

  @override
  Widget build(BuildContext context) {
    final isAccountStep = _step == 0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('회원가입'),
        leading: isAccountStep
            ? null
            : IconButton(
                icon: const Icon(
                  Icons.arrow_back_rounded,
                ),
                onPressed: () {
                  setState(() {
                    _step = 0;
                    _error = null;
                  });
                },
              ),
      ),
      body: SafeArea(
        child: Form(
          key: isAccountStep ? _accountForm : _profileForm,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              24,
              18,
              24,
              28,
            ),
            children: [
              Row(
                children: [
                  Text(
                    '${_step + 1}/2',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: LinearProgressIndicator(
                      value: (_step + 1) / 2,
                      borderRadius: BorderRadius.circular(99),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),
              Text(
                isAccountStep ? '계정 정보' : '기본 정보',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                isAccountStep ? '로그인에 사용할 정보를 입력해 주세요.' : '환자 기본 정보를 입력해 주세요.',
                style: const TextStyle(
                  color: Color(0xFF65758D),
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                '* 필수 입력 항목',
                style: TextStyle(
                  color: Color(0xFF8A97A8),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 26),
              if (isAccountStep) ...[
                _field(
                  _id,
                  '아이디 *',
                ),
                _field(
                  _password,
                  '비밀번호 *',
                  obscure: _obscurePassword,
                  suffix: _eye(
                    () {
                      setState(() {
                        _obscurePassword = !_obscurePassword;
                      });
                    },
                    _obscurePassword,
                  ),
                ),
                _field(
                  _confirm,
                  '비밀번호 확인 *',
                  obscure: _obscureConfirm,
                  suffix: _eye(
                    () {
                      setState(() {
                        _obscureConfirm = !_obscureConfirm;
                      });
                    },
                    _obscureConfirm,
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return '비밀번호 확인을 입력해 주세요.';
                    }

                    if (value != _password.text) {
                      return '비밀번호가 일치하지 않습니다.';
                    }

                    return null;
                  },
                ),
              ] else ...[
                _field(
                  _name,
                  '이름 *',
                ),
                _field(
                  _rrn,
                  '주민등록번호 *',
                  keyboard: TextInputType.number,
                  formatters: [
                    _HyphenFormatter([6, 7]),
                  ],
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return '주민등록번호를 입력해 주세요.';
                    }

                    if (!RegExp(
                      r'^\d{6}-\d{7}$',
                    ).hasMatch(value)) {
                      return '주민등록번호를 확인해 주세요.';
                    }

                    return null;
                  },
                ),
                _field(
                  _phone,
                  '휴대폰 번호 *',
                  keyboard: TextInputType.phone,
                  formatters: [
                    _HyphenFormatter([3, 4, 4]),
                  ],
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return '휴대폰 번호를 입력해 주세요.';
                    }

                    if (!RegExp(
                      r'^01[0-9]-\d{3,4}-\d{4}$',
                    ).hasMatch(value)) {
                      return '휴대폰 번호를 확인해 주세요.';
                    }

                    return null;
                  },
                ),
                _field(
                  _email,
                  '이메일 (선택)',
                  keyboard: TextInputType.emailAddress,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return null;
                    }

                    if (!RegExp(
                      r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
                    ).hasMatch(value.trim())) {
                      return '이메일 형식을 확인해 주세요.';
                    }

                    return null;
                  },
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: Theme.of(context)
                        .colorScheme
                        .errorContainer
                        .withValues(alpha: 0.45),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.info_outline_rounded,
                        size: 18,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _error!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            height: 1.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 22),
              FilledButton(
                onPressed: _loading
                    ? null
                    : isAccountStep
                        ? _next
                        : _submit,
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(
                    _loading
                        ? '처리 중...'
                        : isAccountStep
                            ? '다음'
                            : '회원가입',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _eye(
    VoidCallback onPressed,
    bool obscure,
  ) {
    return IconButton(
      icon: Icon(
        obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
      ),
      onPressed: onPressed,
    );
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    String? Function(String?)? validator,
    TextInputType? keyboard,
    bool obscure = false,
    Widget? suffix,
    List<TextInputFormatter>? formatters,
  }) {
    return Padding(
      padding: const EdgeInsets.only(
        bottom: 14,
      ),
      child: TextFormField(
        controller: controller,
        obscureText: obscure,
        keyboardType: keyboard,
        inputFormatters: formatters,
        validator: validator ??
            (value) {
              if (value == null || value.trim().isEmpty) {
                final cleanLabel = label.replaceAll(' *', '');

                return '$cleanLabel을 입력해 주세요.';
              }

              return null;
            },
        decoration: InputDecoration(
          labelText: label,
          suffixIcon: suffix,
        ),
      ),
    );
  }
}

class _HyphenFormatter extends TextInputFormatter {
  _HyphenFormatter(this.groups);

  final List<int> groups;

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(
      RegExp(r'\D'),
      '',
    );

    var offset = 0;
    final buffer = StringBuffer();

    for (final length in groups) {
      if (offset >= digits.length) {
        break;
      }

      if (buffer.isNotEmpty) {
        buffer.write('-');
      }

      final end =
          offset + length > digits.length ? digits.length : offset + length;

      buffer.write(
        digits.substring(
          offset,
          end,
        ),
      );

      offset = end;
    }

    final text = buffer.toString();

    return TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(
        offset: text.length,
      ),
    );
  }
}
