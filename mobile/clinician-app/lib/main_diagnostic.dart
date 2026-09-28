import 'package:flutter/material.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const MaterialApp(
      home: Scaffold(
        backgroundColor: Colors.white,
        body: Center(
          child: Text(
            'Brain On 화면 테스트',
            style: TextStyle(
              color: Colors.black,
              fontSize: 26,
            ),
          ),
        ),
      ),
    ),
  );
}
