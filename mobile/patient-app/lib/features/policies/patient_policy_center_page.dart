import 'package:flutter/material.dart';

class PatientPolicyCenterPage extends StatelessWidget {
  const PatientPolicyCenterPage({super.key});

  static const _effectiveDate = '2026.09.29';

  static void open(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => const PatientPolicyCenterPage(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('약관 및 정책')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 18, 18, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: const Color(0xFFF8F9FF),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFE5E8F5)),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'HoDoc',
                  style: TextStyle(
                    color: Color(0xFF5665B8),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 5),
                Text(
                  '약관 및 개인정보 안내',
                  style: TextStyle(
                    color: Color(0xFF263A5A),
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'HoDoc 서비스를 안전하게 이용하기 위한 약관과 개인정보 처리 내용을 확인할 수 있습니다.',
                  style: TextStyle(
                    color: Color(0xFF65758D),
                    fontSize: 13,
                    height: 1.55,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  '운영주체 BrainOn  ·  시행일 $_effectiveDate',
                  style: TextStyle(
                    color: Color(0xFF8A94A6),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const _PolicyTile(
            title: 'HoDoc 서비스 이용약관',
            subtitle: '환자용 의료정보 서비스 이용 기준',
            body: '1. 서비스 안내\n'
                'HoDoc(호닥)은 BrainOn이 제공하는 환자용 의료정보 서비스입니다. 이용자는 HoDoc을 통해 예약, 진료내역, 복약정보, 건강 관련 안내 및 기타 환자 편의 서비스를 이용할 수 있습니다.\n\n'
                '2. 계정 이용\n'
                '이용자는 자신의 계정을 안전하게 관리하여야 하며 다른 사람의 계정 또는 환자정보를 부정하게 이용해서는 안 됩니다.\n\n'
                '3. 의료정보 제공\n'
                'HoDoc에 표시되는 진료정보, 검사정보 및 처방정보는 의료서비스 이용을 돕기 위한 정보이며 시스템 연계상황이나 정보 갱신 시점에 따라 실제 의료기관의 최신 기록과 차이가 발생할 수 있습니다.\n\n'
                '4. 진료 및 치료에 관한 안내\n'
                'HoDoc에서 제공되는 정보만을 근거로 이용자가 임의로 약물 복용을 중단하거나 치료방법을 변경해서는 안 됩니다. 진료와 치료에 관한 사항은 담당 의료진에게 확인하시기 바랍니다.\n\n'
                '5. 서비스 운영\n'
                '시스템 점검, 통신환경, 장애 또는 의료정보 연계상황에 따라 일부 서비스가 일시적으로 제한되거나 정보 제공이 지연될 수 있습니다.\n\n'
                '6. 응급상황\n'
                'HoDoc은 응급의료서비스를 대신하지 않습니다. 갑작스러운 마비, 언어장애, 의식저하 등 응급 증상이 발생한 경우 앱의 결과를 기다리지 말고 즉시 119 또는 가까운 응급의료기관을 이용하시기 바랍니다.',
          ),
          const _PolicyTile(
            title: 'HoDoc 개인정보 처리방침',
            subtitle: '개인정보 및 의료정보 처리 안내',
            body: '1. 개인정보의 처리 목적\n'
                'BrainOn은 HoDoc 서비스 제공, 환자 본인 확인, 진료정보 제공, 예약 및 복약 서비스 제공, 의료정보 연계, 서비스 알림, 시스템 보안 및 장애 대응을 위해 필요한 개인정보를 처리합니다.\n\n'
                '2. 처리하는 개인정보\n'
                '서비스 이용 과정에서 성명, 생년월일, 성별, 환자 식별정보, 휴대전화번호, 이메일, 로그인 및 본인확인 정보 등이 처리될 수 있습니다.\n\n'
                '진료서비스와 연계되는 경우 진료 및 내원정보, 진단정보, 증상 및 병력, 알레르기, 활력징후, 검사정보와 검사결과, 처방·투약정보, 진료·간호기록, 협진정보 및 CT·MRI·MRA 등의 의료영상과 분석정보가 처리될 수 있습니다.\n\n'
                '3. 민감정보 보호\n'
                '건강정보와 진료정보는 보호가 필요한 민감정보로 취급하며 일반 개인정보보다 강화된 보호조치를 적용하여 관리합니다.\n\n'
                '4. 개인정보 이용 및 제공\n'
                'BrainOn은 개인정보를 서비스 제공에 필요한 범위에서 이용하며 관계 법령에서 허용하거나 적법한 처리 근거가 있는 경우를 제외하고 목적 외로 이용하거나 제3자에게 제공하지 않습니다.\n\n'
                '5. 서비스 이용기록\n'
                '서비스의 안정적인 운영과 보안을 위해 접속일시, 접속 IP, 로그인 기록, 서비스 이용기록, 앱 또는 기기정보, 오류 및 장애정보 등이 기록될 수 있습니다.\n\n'
                '6. 개인정보 보유 및 파기\n'
                '개인정보는 이용 목적이 달성되면 관계 법령상 보존 의무가 있는 경우를 제외하고 안전하게 파기합니다. 의료법 등 관계 법령에 따라 보존하여야 하는 진료기록은 해당 기간 동안 보관될 수 있습니다.\n\n'
                '7. 개인정보 보호조치\n'
                'BrainOn은 사용자 인증, 접근권한 관리, 중요정보 보호, 접근기록 관리, 비인가 접근 차단 및 시스템 보안 모니터링 등을 통해 개인정보와 의료정보를 보호합니다.\n\n'
                '8. 이용자의 권리\n'
                '이용자는 관계 법령이 정하는 범위에서 자신의 개인정보에 대한 열람, 정정, 삭제 또는 처리정지 등을 요구할 수 있습니다. 다만 관계 법령에 따라 보존이 필요한 진료기록은 제한될 수 있습니다.',
          ),
          const _PolicyTile(
            title: '의료정보 및 AI 서비스 안내',
            subtitle: 'AI 분석정보와 의료정보 이용 안내',
            body: '1. AI 분석정보\n'
                'HoDoc에서 제공되는 일부 의료정보에는 BrainOn의 AI 분석 및 임상 의사결정 지원시스템을 통해 생성된 결과가 포함될 수 있습니다.\n\n'
                '2. 참고정보의 성격\n'
                'AI 분석결과와 임상 의사결정 지원정보는 담당 의료진의 판단을 지원하기 위한 참고정보이며 환자의 최종 진단 또는 치료결정을 대신하지 않습니다.\n\n'
                '3. 최종 의료적 판단\n'
                '최종적인 진단, 치료 및 처방에 관한 판단은 담당 의료진이 환자의 상태, 병력, 검사결과, 의료영상 및 기타 임상정보를 종합적으로 검토하여 수행합니다.\n\n'
                '4. 치료 변경 금지\n'
                'HoDoc에 표시되는 AI 분석결과 또는 의료정보만을 근거로 약물 복용을 임의로 중단하거나 치료방법을 변경하지 마십시오.\n\n'
                '5. 응급상황\n'
                '건강상태가 급격하게 악화되거나 응급 증상이 발생한 경우 HoDoc의 AI 기능 또는 안내 결과를 기다리지 말고 즉시 119 또는 가까운 응급의료기관을 이용하십시오.',
          ),
        ],
      ),
    );
  }
}

class _PolicyTile extends StatelessWidget {
  const _PolicyTile({
    required this.title,
    required this.subtitle,
    required this.body,
  });

  final String title;
  final String subtitle;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFFE5E8F5)),
      ),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(18, 0, 18, 20),
        title: Text(
          title,
          style: const TextStyle(
            color: Color(0xFF263A5A),
            fontSize: 14,
            fontWeight: FontWeight.w800,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            subtitle,
            style: const TextStyle(
              color: Color(0xFF65758D),
              fontSize: 11,
            ),
          ),
        ),
        children: [
          const Divider(height: 20, color: Color(0xFFE5E8F5)),
          Align(
            alignment: Alignment.centerLeft,
            child: SelectableText(
              body,
              style: const TextStyle(
                color: Color(0xFF4A5568),
                fontSize: 13,
                height: 1.7,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
