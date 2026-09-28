import 'package:flutter/material.dart';

class ClinicianPolicyCenterPage extends StatelessWidget {
  const ClinicianPolicyCenterPage({super.key});

  static const _effectiveDate = '2026.09.29';
  static const _version = '1.0';

  static void openFromDrawer(BuildContext context) {
    final navigator = Navigator.of(context);
    navigator.pop();
    Future<void>.microtask(() {
      navigator.push(
        MaterialPageRoute(
          builder: (_) => const ClinicianPolicyCenterPage(),
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    const navy = Color(0xFF263247);
    const muted = Color(0xFF7183A0);
    const blue = Color(0xFF4F8FE8);
    const border = Color(0xFFE4EBF3);

    return Scaffold(
      appBar: AppBar(title: const Text('약관 및 정책')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 18, 18, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: border),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'BRAINON POLICY',
                  style: TextStyle(
                    color: blue,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.0,
                  ),
                ),
                SizedBox(height: 6),
                Text(
                  'BrainOn 의료정보시스템',
                  style: TextStyle(
                    color: navy,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  '의료정보시스템의 이용 기준과 개인정보 및 환자 의료정보 보호정책을 확인할 수 있습니다.',
                  style: TextStyle(
                    color: muted,
                    fontSize: 13,
                    height: 1.55,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  '시행일 $_effectiveDate  ·  버전 $_version',
                  style: TextStyle(
                    color: Color(0xFF8A94A6),
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const _PolicyTile(
            title: '의료정보시스템 이용약관',
            subtitle: 'BrainOn 시스템 이용에 관한 기본 기준',
            body: '1. 목적\n'
                'BrainOn은 승인된 의료진 및 시스템 운영자가 환자 진료와 관련된 업무를 안전하고 효율적으로 수행할 수 있도록 의료정보 및 임상 의사결정 지원 기능을 제공합니다.\n\n'
                '2. 사용자 계정 및 접근권한\n'
                '사용자는 본인에게 발급된 계정만 이용하여야 하며 계정을 다른 사용자와 공유하거나 타인의 계정을 사용해서는 안 됩니다. 시스템 기능과 환자정보에 대한 접근권한은 사용자의 직무와 역할에 따라 제한됩니다.\n\n'
                '3. 의료정보의 이용\n'
                '시스템에서 조회되는 환자의 개인정보, 건강정보, 진료기록 및 의료영상은 진료, 간호, 검사, 영상판독, 협진, 처방 및 승인된 시스템 운영 등 업무 수행에 필요한 범위에서만 이용하여야 합니다.\n\n'
                '업무와 관계없는 환자정보 조회, 무단 저장·복사·전송, 외부 제공 또는 접근권한의 부정사용을 금지합니다.\n\n'
                '4. 서비스 운영\n'
                '시스템 점검, 장애 대응, 보안조치 또는 서비스 개선을 위해 일부 기능의 이용이 일시적으로 제한될 수 있습니다.\n\n'
                '5. 약관 변경\n'
                'BrainOn은 관계 법령, 서비스 운영 방식 또는 정보보호 정책 변경에 따라 본 약관을 개정할 수 있으며 중요한 변경사항은 시스템을 통해 안내합니다.',
          ),
          const _PolicyTile(
            title: '개인정보 처리방침',
            subtitle: '개인정보 처리 목적과 보호조치 안내',
            body: '1. 개인정보의 처리 목적\n'
                'BrainOn은 의료정보시스템 제공, 사용자 인증, 접근권한 관리, 의료업무 지원, 시스템 운영, 서비스 보안, 장애 대응 및 감사 추적을 위해 필요한 개인정보를 처리합니다.\n\n'
                '2. 처리하는 개인정보\n'
                '시스템 사용자와 관련하여 성명, 로그인 식별정보, 소속 및 역할, 연락정보와 접속 IP, 접속일시, 시스템 이용기록, 오류 및 보안 관련 기록 등이 처리될 수 있습니다.\n\n'
                '의료업무 과정에서는 환자의 기본정보, 진료정보, 검사결과, 처방정보, 의료영상, 협진정보 및 AI 분석결과 등이 처리될 수 있습니다.\n\n'
                '3. 민감정보 보호\n'
                '환자의 건강정보 및 진료정보는 보호가 필요한 민감정보로 취급하며 일반 개인정보보다 강화된 접근통제와 보호조치를 적용합니다.\n\n'
                '4. 이용 및 제공\n'
                '개인정보는 처리 목적에 필요한 범위에서 이용하며 관계 법령에서 허용하거나 적법한 처리 근거가 있는 경우를 제외하고 목적 외로 이용하거나 제3자에게 제공하지 않습니다.\n\n'
                '5. 보유 및 파기\n'
                '개인정보는 처리 목적 달성 후 관계 법령상 보존 의무가 있는 경우를 제외하고 안전하게 파기합니다. 법령에 따라 보존이 필요한 의료기록은 정해진 기간 동안 별도로 안전하게 관리될 수 있습니다.\n\n'
                '6. 안전성 확보조치\n'
                'BrainOn은 사용자 인증, 역할 기반 접근통제, 최소권한 관리, 중요정보 보호, 접근기록 관리, 비인가 접근 차단 및 보안 모니터링 등을 통해 개인정보를 보호합니다.\n\n'
                '7. 정보주체의 권리\n'
                '정보주체는 관계 법령이 정하는 범위에서 자신의 개인정보에 대한 열람, 정정, 삭제 또는 처리정지 등을 요구할 수 있습니다. 다만 법령에 따라 보존이 필요한 의료기록은 제한될 수 있습니다.',
          ),
          const _PolicyTile(
            title: '환자 의료정보 보호 및 보안정책',
            subtitle: '환자정보 접근·조회·보안 준수사항',
            body: '1. 업무 목적에 따른 접근\n'
                '환자정보는 진료, 간호, 검사, 영상판독, 협진, 처방 및 승인된 시스템 운영 등 업무 수행에 필요한 경우에만 접근할 수 있습니다.\n\n'
                '2. 최소권한 원칙\n'
                '사용자는 자신의 직무와 역할에 따라 부여된 권한 범위 내에서만 환자정보를 조회하고 처리하여야 합니다.\n\n'
                '3. 목적 외 조회 금지\n'
                '업무와 관계없는 환자정보의 조회 또는 이용을 금지합니다.\n\n'
                '4. 외부 반출 금지\n'
                '환자정보를 개인 이메일, 개인 메신저, 승인되지 않은 클라우드 저장소 또는 외부 저장매체를 통해 전송하거나 저장해서는 안 됩니다.\n\n'
                '5. 접근 및 감사기록\n'
                'BrainOn에서 이루어지는 환자정보 조회, 변경 및 주요 시스템 이용행위는 개인정보 보호, 정보보안 및 감사 목적으로 기록될 수 있습니다.\n\n'
                '6. 계정 및 화면 보호\n'
                '사용자는 본인의 계정을 타인과 공유해서는 안 되며 환자정보가 표시된 상태로 자리를 비우지 않아야 합니다. 업무 종료 후에는 로그아웃하여야 합니다.\n\n'
                '7. 보안사고 대응\n'
                '비정상적인 접근, 개인정보 유출 또는 보안사고가 의심되는 경우 즉시 시스템 관리자 또는 개인정보 보호 담당자에게 알려야 합니다.',
          ),
          const _PolicyTile(
            title: 'AI·CDSS 이용 및 책임 안내',
            subtitle: 'AI 분석과 임상 의사결정 지원정보 이용 기준',
            body: '1. 보조정보의 성격\n'
                'BrainOn이 제공하는 AI 의료영상 분석, 임상 의사결정 지원시스템(CDSS) 및 DUR 정보는 의료진의 판단을 지원하기 위한 참고정보입니다.\n\n'
                '2. 최종 임상 판단\n'
                'AI 또는 CDSS의 분석결과만으로 환자의 최종 진단, 처방 또는 치료방법이 자동으로 결정되지 않습니다.\n\n'
                '최종적인 진단, 처방 및 치료 결정은 담당 의료진이 환자의 증상, 병력, 신체 및 신경학적 평가, 검사결과, 원본 의료영상, 영상 판독결과 및 투약내역 등을 종합적으로 검토하여 수행하여야 합니다.\n\n'
                '3. 원본자료 확인\n'
                'AI 분석결과와 실제 임상소견이 일치하지 않거나 결과의 정확성이 의심되는 경우 의료진의 전문적 검토와 원본자료 확인이 우선되어야 합니다.\n\n'
                '4. DUR 정보\n'
                '병용금기, 용량주의 및 기타 의약품 안전성 정보는 처방 검토를 지원하기 위한 정보이며 알림의 존재 또는 부재만으로 특정 처방의 적절성이 확정되는 것은 아닙니다.\n\n'
                '5. 시스템 결과 확인\n'
                '분석결과 또는 시스템 정보에 오류나 불일치가 의심되는 경우 해당 결과를 그대로 사용하지 말고 관련 임상정보와 원본자료를 확인하여야 합니다.',
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
        side: const BorderSide(color: Color(0xFFE4EBF3)),
      ),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(18, 0, 18, 20),
        title: Text(
          title,
          style: const TextStyle(
            color: Color(0xFF263247),
            fontSize: 14,
            fontWeight: FontWeight.w800,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            subtitle,
            style: const TextStyle(
              color: Color(0xFF7183A0),
              fontSize: 11,
            ),
          ),
        ),
        children: [
          const Divider(height: 20, color: Color(0xFFE4EBF3)),
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
