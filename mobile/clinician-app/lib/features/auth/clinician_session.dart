class ClinicianRoleInfo {
  const ClinicianRoleInfo({
    required this.id,
    required this.code,
    required this.name,
  });

  factory ClinicianRoleInfo.fromJson(Map<String, dynamic> json) =>
      ClinicianRoleInfo(
        id: json['id']?.toString() ?? '',
        code: json['code']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
      );

  final String id;
  final String code;
  final String name;
}

class ClinicianUser {
  const ClinicianUser({
    required this.id,
    required this.loginId,
    required this.name,
    required this.email,
    required this.role,
    required this.permissions,
  });

  factory ClinicianUser.fromJson(Map<String, dynamic> json) => ClinicianUser(
        id: json['id']?.toString() ?? '',
        loginId: json['login_id']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
        email: json['email']?.toString() ?? '',
        role: ClinicianRoleInfo.fromJson(
          Map<String, dynamic>.from(json['role'] as Map? ?? const {}),
        ),
        permissions: (json['permissions'] as List? ?? const [])
            .map((value) => value.toString())
            .toList(growable: false),
      );

  final String id;
  final String loginId;
  final String name;
  final String email;
  final ClinicianRoleInfo role;
  final List<String> permissions;
}

class ClinicianSession {
  const ClinicianSession({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
  });

  factory ClinicianSession.fromJson(Map<String, dynamic> json) => ClinicianSession(
        accessToken: json['access']?.toString() ?? '',
        refreshToken: json['refresh']?.toString() ?? '',
        user: ClinicianUser.fromJson(
          Map<String, dynamic>.from(json['user'] as Map? ?? const {}),
        ),
      );

  final String accessToken;
  final String refreshToken;
  final ClinicianUser user;
}
