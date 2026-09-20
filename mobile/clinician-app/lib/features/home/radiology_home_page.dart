import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../analysis/radiology_analysis_requests_page.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';
import '../radiology/widgets/radiology_ui.dart';

class RadiologyHomePage extends StatefulWidget {
  const RadiologyHomePage({
    super.key,
    required this.apiClient,
    this.userName = '의료진',
  });

  final ClinicianApiClient apiClient;

  /// 로그인한 의료진 이름
  final String userName;

  @override
  State<RadiologyHomePage> createState() => _RadiologyHomePageState();
}

class _RadiologyHomePageState extends State<RadiologyHomePage> {
  List<_HomeAnalysis> _items = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final requests = await RadiologyAnalysisApi(widget.apiClient).list();

      final items = await Future.wait(
        requests.asMap().entries.map((entry) async {
          final request = entry.value;

          Map<String, dynamic>? study;

          // 최근 3건만 Study 상세를 추가 조회해서
          // 환자명 / 환자번호를 보강합니다.
          if (entry.key < 3 && request.studyId.isNotEmpty) {
            try {
              study = await widget.apiClient.get(
                '/api/v1/imaging-studies/${request.studyId}',
              );
            } on ClinicianApiException {
              // Study 조회 실패가
              // 분석 목록 표시 자체를 막지 않도록 합니다.
            }
          }

          return _HomeAnalysis(
            request,
            study,
          );
        }),
      );

      if (mounted) {
        setState(() {
          _items = items;
        });
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _error = '분석 요청을 불러오지 못했습니다.';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    int count(String status) {
      return _items
          .where(
            (item) => item.request.status == status,
          )
          .length;
    }

    // 아직 완료되지 않은 분석
    final pendingCount =
        count('QUEUED') + count('PROCESSING') + count('RETRYING');

    // 긴급 분석
    final urgentCount = _items
        .where(
          (item) => item.request.priority == 'CRITICAL',
        )
        .length;

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        20,
        16,
        20,
        28,
      ),
      children: [
        // ==========================================================
        // 상단 인사
        // ==========================================================

        _GreetingBanner(
          userName: widget.userName,
        ),

        // ==========================================================
        // 긴급 분석
        // 긴급 건이 실제로 있을 때만 표시
        // ==========================================================

        if (!_loading && _error == null && urgentCount > 0) ...[
          const SizedBox(height: 14),
          _UrgentAnalysisBanner(
            count: urgentCount,
          ),
        ],

        const SizedBox(height: 24),

        // ==========================================================
        // 오늘 업무 요약
        // ==========================================================

        const RadiologySectionTitle(
          title: '오늘 업무 요약',
        ),

        const SizedBox(height: 10),

        if (_loading)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(28),
              child: CircularProgressIndicator(),
            ),
          )
        else if (_error != null)
          _Retry(
            message: _error!,
            onRetry: _load,
          )
        else
          SizedBox(
            height: 88,
            child: Row(
              children: [
                Expanded(
                  child: _Summary(
                    icon: Icons.analytics_outlined,
                    label: '미처리 분석요청',
                    count: pendingCount,
                    color: radiologyBlue,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _Summary(
                    icon: Icons.priority_high_rounded,
                    label: '긴급 분석',
                    count: urgentCount,
                    color: radiologyDanger,
                  ),
                ),
              ],
            ),
          ),

        const SizedBox(height: 27),

        // ==========================================================
        // 최근 분석
        // ==========================================================

        const RadiologySectionTitle(
          title: '최근 분석',
          action: '전체보기 ›',
        ),

        const SizedBox(height: 10),

        if (!_loading && _error == null)
          _RecentAnalysisList(
            items: _items.take(3).toList(),
            apiClient: widget.apiClient,
          ),

        // ==========================================================
        // 의료진 응원 배너
        // ==========================================================

        const SizedBox(height: 24),

        const _SupportBanner(),

        const SizedBox(height: 12),
      ],
    );
  }
}

// ============================================================================
// 상단 인사 배너
// ============================================================================

class _GreetingBanner extends StatelessWidget {
  const _GreetingBanner({
    required this.userName,
  });

  final String userName;

  @override
  Widget build(BuildContext context) {
    final rawName = userName.trim();

    // 세션 이름이 "영상의학과 윤지호" 형태여도
    // 홈에서는 "윤지호님,"으로 표시
    final displayName = rawName.isEmpty
        ? '의료진'
        : rawName
            .replaceFirst(
              RegExp(r'^영상의학과\s*'),
              '',
            )
            .replaceFirst(
              RegExp(r'^신경과\s*'),
              '',
            );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        18,
        21,
        14,
        21,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: radiologyBorder,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(
              0xFF263247,
            ).withValues(
              alpha: 0.035,
            ),
            blurRadius: 14,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$displayName님,',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    height: 1.2,
                  ),
                ),
                const SizedBox(
                  height: 6,
                ),
                const Text(
                  '좋은 하루 되세요.',
                  style: TextStyle(
                    color: radiologyNavy,
                    fontSize: 22,
                    height: 1.15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(
                  height: 9,
                ),
                const Text(
                  '오늘도 정확한 판독이\n'
                  '환자의 치료에 큰 힘이 됩니다.',
                  style: TextStyle(
                    color: radiologyMuted,
                    fontSize: 12,
                    height: 1.45,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 124,
            height: 100,
            child: OverflowBox(
              maxWidth: 140,
              maxHeight: 140,
              child: Transform.translate(
                offset: const Offset(4, 6),
                child: Image.asset(
                  'asset/images/main1.png',
                  width: 140,
                  height: 140,
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) {
                    return const SizedBox.shrink();
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
// ============================================================================
// 긴급 분석 배너
// ============================================================================

class _UrgentAnalysisBanner extends StatelessWidget {
  const _UrgentAnalysisBanner({
    required this.count,
  });

  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 15,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF0EF),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFFFD8D5),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: const Color(
                0xFFFFDEDB,
              ),
              borderRadius: BorderRadius.circular(
                13,
              ),
            ),
            child: const Icon(
              Icons.emergency_rounded,
              color: radiologyDanger,
              size: 24,
            ),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '긴급 분석이 $count건 있습니다.',
                  style: const TextStyle(
                    color: radiologyDanger,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(
                  height: 3,
                ),
                const Text(
                  'CRITICAL · 우선 확인이 필요한 분석 요청',
                  style: TextStyle(
                    color: radiologyMuted,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          const Icon(
            Icons.chevron_right_rounded,
            color: radiologyMuted,
            size: 22,
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// 업무 요약 카드
// ============================================================================

class _Summary extends StatelessWidget {
  const _Summary({
    required this.icon,
    required this.label,
    required this.count,
    required this.color,
  });

  final IconData icon;
  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return RadiologyInfoCard(
      padding: const EdgeInsets.symmetric(
        horizontal: 13,
        vertical: 14,
      ),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: color.withValues(
                alpha: 0.12,
              ),
              borderRadius: BorderRadius.circular(
                12,
              ),
            ),
            child: Icon(
              icon,
              color: color,
              size: 20,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: radiologyMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(
                  height: 3,
                ),
                Text(
                  '$count건',
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    height: 1,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// 홈 분석 데이터
// ============================================================================

class _HomeAnalysis {
  const _HomeAnalysis(
    this.request,
    this.study,
  );

  final RadiologyAnalysisRequest request;
  final Map<String, dynamic>? study;

  String? get patientName => (study?['patient'] as Map?)?['name']?.toString();

  String? get patientNo =>
      (study?['patient'] as Map?)?['patient_no']?.toString();
}

// ============================================================================
// 최근 분석 목록
// ============================================================================

class _RecentAnalysisList extends StatelessWidget {
  const _RecentAnalysisList({
    required this.items,
    required this.apiClient,
  });

  final List<_HomeAnalysis> items;
  final ClinicianApiClient apiClient;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const RadiologyInfoCard(
        child: _CompactEmpty(
          icon: Icons.analytics_outlined,
          message: '최근 분석 요청이 없습니다.',
        ),
      );
    }

    return RadiologyInfoCard(
      padding: const EdgeInsets.symmetric(
        horizontal: 14,
        vertical: 3,
      ),
      child: Column(
        children: [
          for (var index = 0; index < items.length; index++) ...[
            _AnalysisRow(
              item: items[index],
              apiClient: apiClient,
            ),
            if (index < items.length - 1)
              const Divider(
                height: 1,
                color: radiologyBorder,
              ),
          ],
        ],
      ),
    );
  }
}

// ============================================================================
// 최근 분석 한 행
// ============================================================================

class _AnalysisRow extends StatelessWidget {
  const _AnalysisRow({
    required this.item,
    required this.apiClient,
  });

  final _HomeAnalysis item;
  final ClinicianApiClient apiClient;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => RadiologyNavigation.openAnalysis(item.request),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          vertical: 12,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: const Color(
                  0xFFEAF2FF,
                ),
                borderRadius: BorderRadius.circular(
                  12,
                ),
              ),
              child: const Icon(
                Icons.analytics_outlined,
                color: radiologyBlue,
                size: 20,
              ),
            ),

            const SizedBox(
              width: 11,
            ),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          item.patientName ?? '환자 정보 없음',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: radiologyNavy,
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      if (item.patientNo != null &&
                          item.patientNo!.isNotEmpty) ...[
                        const SizedBox(
                          width: 8,
                        ),
                        Flexible(
                          child: Text(
                            item.patientNo!,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: radiologyMuted,
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(
                    height: 4,
                  ),
                  Text(
                    _analysisType(
                      item.request.analysisType,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: radiologyMuted,
                      fontSize: 11,
                    ),
                  ),
                  const SizedBox(
                    height: 2,
                  ),
                  Text(
                    _time(
                      item.request.completedAt ?? item.request.requestedAt,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: radiologyMuted,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),

            // 상태 chip과 chevron이
            // 오른쪽 벽에 너무 붙지 않도록 간격 조정
            const SizedBox(width: 10),

            RadiologyStatusChip(
              label: _statusLabel(
                item.request.status,
              ),
              color: _statusColor(
                item.request.status,
              ),
            ),

            const SizedBox(width: 8),

            const Icon(
              Icons.chevron_right_rounded,
              color: radiologyMuted,
              size: 19,
            ),

            const SizedBox(width: 2),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// 의료진 응원 자동 배너
// ============================================================================

class _SupportBanner extends StatefulWidget {
  const _SupportBanner();

  @override
  State<_SupportBanner> createState() => _SupportBannerState();
}

class _SupportBannerState extends State<_SupportBanner> {
  static const List<String> _messages = [
    '오늘도 수고 많으셨습니다.\n'
        '당신의 판독이 환자의 치료에 큰 힘이 됩니다.',
    '정확한 판독 하나가\n'
        '환자의 다음 치료를 바꿉니다.',
    '보이지 않는 곳의 세심한 판단이\n'
        '더 나은 치료를 만듭니다.',
    '오늘의 한 번 더 확인이\n'
        '환자에게는 큰 차이를 만듭니다.',
  ];

  int _currentIndex = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();

    _timer = Timer.periodic(
      const Duration(seconds: 5),
      (_) {
        if (!mounted) {
          return;
        }

        setState(() {
          _currentIndex = (_currentIndex + 1) % _messages.length;
        });
      },
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        16,
        16,
        16,
        13,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFF7FAFF),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: radiologyBorder,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: const Color(
                    0xFFEAF2FF,
                  ),
                  borderRadius: BorderRadius.circular(
                    13,
                  ),
                ),
                child: const Icon(
                  Icons.favorite_outline_rounded,
                  color: radiologyBlue,
                  size: 22,
                ),
              ),
              const SizedBox(
                width: 13,
              ),
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(
                    milliseconds: 350,
                  ),
                  transitionBuilder: (
                    child,
                    animation,
                  ) {
                    return FadeTransition(
                      opacity: animation,
                      child: child,
                    );
                  },
                  child: Text(
                    _messages[_currentIndex],
                    key: ValueKey(
                      _currentIndex,
                    ),
                    style: const TextStyle(
                      color: radiologyNavy,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      height: 1.5,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(
            height: 11,
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(
              _messages.length,
              (index) {
                final selected = index == _currentIndex;

                return AnimatedContainer(
                  duration: const Duration(
                    milliseconds: 250,
                  ),
                  width: selected ? 16 : 6,
                  height: 6,
                  margin: const EdgeInsets.symmetric(
                    horizontal: 3,
                  ),
                  decoration: BoxDecoration(
                    color: selected
                        ? radiologyBlue
                        : const Color(
                            0xFFD5DFEC,
                          ),
                    borderRadius: BorderRadius.circular(
                      20,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// Empty
// ============================================================================

class _CompactEmpty extends StatelessWidget {
  const _CompactEmpty({
    required this.icon,
    required this.message,
  });

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        vertical: 10,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon,
            color: radiologyMuted,
            size: 20,
          ),
          const SizedBox(width: 8),
          Text(
            message,
            style: const TextStyle(
              color: radiologyMuted,
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// Retry
// ============================================================================

class _Retry extends StatelessWidget {
  const _Retry({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return RadiologyInfoCard(
      child: Column(
        children: [
          Text(
            message,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 6),
          TextButton(
            onPressed: onRetry,
            child: const Text(
              '다시 시도',
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// 분석 유형 한글화
// ============================================================================

String _analysisType(String value) {
  return switch (value) {
    'HEMORRHAGIC_STROKE_CT' => 'CT 뇌출혈 분석',
    'ISCHEMIC_STROKE_DWI_ADC' => 'MRI 허혈성 뇌졸중 분석',
    'CEREBRAL_ANEURYSM_MRA' => 'MRA 뇌동맥류 분석',
    _ => value.isEmpty ? '분석 유형 정보 없음' : value,
  };
}

// ============================================================================
// 상태 한글화
// ============================================================================

String _statusLabel(String value) {
  return switch (value) {
    'QUEUED' => '분석 대기',
    'PROCESSING' => '분석 중',
    'RETRYING' => '재시도 중',
    'COMPLETED' => '분석 완료',
    'FAILED' => '분석 실패',
    'CANCELLED' => '분석 취소',
    _ => value.isEmpty ? '상태 미확인' : value,
  };
}

// ============================================================================
// 상태 색상
// ============================================================================

Color _statusColor(String value) {
  return switch (value) {
    'COMPLETED' => radiologySuccess,
    'PROCESSING' || 'RETRYING' => radiologyWarning,
    'FAILED' || 'CANCELLED' => radiologyDanger,
    _ => radiologyBlue,
  };
}

// ============================================================================
// 날짜/시간
// ============================================================================

String _time(String? value) {
  final date = value == null
      ? null
      : DateTime.tryParse(
          value,
        )?.toLocal();

  if (date == null) {
    return value ?? '시간 정보 없음';
  }

  String two(int number) {
    return number.toString().padLeft(
          2,
          '0',
        );
  }

  return '${date.year}.'
      '${two(date.month)}.'
      '${two(date.day)} '
      '${two(date.hour)}:'
      '${two(date.minute)}';
}
