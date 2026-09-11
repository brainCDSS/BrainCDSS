import 'package:flutter/material.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) => ListView(
        children: const [
          ListTile(leading: Icon(Icons.person_outline), title: Text('내 정보'), enabled: false),
          ListTile(leading: Icon(Icons.link_outlined), title: Text('연결 설정'), enabled: false),
          ListTile(leading: Icon(Icons.notifications_outlined), title: Text('알림 설정'), enabled: false),
          ListTile(leading: Icon(Icons.description_outlined), title: Text('동의 · 약관'), enabled: false),
          ListTile(leading: Icon(Icons.logout), title: Text('로그아웃'), enabled: false),
        ],
      );
}
