class AuthUser {
  const AuthUser({
    required this.id,
    required this.loginId,
    required this.name,
    required this.email,
    required this.roleCode,
    required this.roleName,
    required this.permissions,
  });

  final String id;
  final String loginId;
  final String name;
  final String? email;
  final String roleCode;
  final String roleName;
  final List<String> permissions;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    final role = Map<String, dynamic>.from(
      json['role'] as Map,
    );

    return AuthUser(
      id: json['id'].toString(),
      loginId: json['login_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      email: json['email']?.toString(),
      roleCode: role['code']?.toString() ?? '',
      roleName: role['name']?.toString() ?? '',
      permissions: (json['permissions'] as List?)
              ?.map((item) => item.toString())
              .toList() ??
          const [],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'login_id': loginId,
        'name': name,
        'email': email,
        'role': {
          'code': roleCode,
          'name': roleName,
        },
        'permissions': permissions,
      };
}

class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
  });

  final String accessToken;
  final String refreshToken;
  final AuthUser user;

  factory AuthSession.fromJson(
    Map<String, dynamic> json,
  ) {
    return AuthSession(
      accessToken: json['access']?.toString() ?? '',
      refreshToken: json['refresh']?.toString() ?? '',
      user: AuthUser.fromJson(
        Map<String, dynamic>.from(
          json['user'] as Map,
        ),
      ),
    );
  }
}
