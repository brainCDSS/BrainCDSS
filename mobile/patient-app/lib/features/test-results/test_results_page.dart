import 'package:flutter/material.dart';

class TestResultsPage extends StatelessWidget {
  const TestResultsPage({super.key});

  @override
  Widget build(BuildContext context) => const DefaultTabController(
        length: 3,
        child: Column(
          children: [
            TabBar(
              tabs: [
                Tab(text: '검사 결과'),
                Tab(text: '진료 내역'),
                Tab(text: '처방 정보'),
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  Center(child: Text('검사 결과가 표시될 영역입니다.')),
                  Center(child: Text('진료 내역이 표시될 영역입니다.')),
                  Center(child: Text('처방 정보가 표시될 영역입니다.')),
                ],
              ),
            ),
          ],
        ),
      );
}
