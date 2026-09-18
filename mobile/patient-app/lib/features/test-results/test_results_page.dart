import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import 'test_results_api.dart';

const _primary = Color(0xFF7567C8);
const _soft = Color(0xFFEEEAFE);
const _border = Color(0xFFCFD7E8);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);

String _formatTestResultDate(DateTime? value) {
  if (value == null) return '-';
  final local = value.toLocal();
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '${local.year}.$month.$day $hour:$minute';
}

class TestResultsPage extends StatelessWidget {
  const TestResultsPage({
    super.key,
    required this.apiClient,
  });

  final ApiClient apiClient;

  static void openResults(BuildContext context, ApiClient apiClient) =>
      _openPage(context, _ResultsListPage(apiClient: apiClient));

  static void openVisits(BuildContext context) =>
      _openPage(context, const _VisitDetailPage());

  static void openPrescriptions(BuildContext context, ApiClient client) =>
      _openPage(context, const _PrescriptionDetailPage());

  static void _openPage(BuildContext context, Widget page) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => page),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
      children: [
        const _ResultsHeroBanner(),
        const SizedBox(height: 16),
        _MenuCard(
          icon: Icons.assignment_turned_in_outlined,
          title: '검사 결과',
          description: '검사 결과를 확인할 수 있어요.',
          onTap: () => openResults(context, apiClient),
        ),
        const SizedBox(height: 12),
        _MenuCard(
          icon: Icons.history_edu_outlined,
          title: '진료 내역',
          description: '진료 기록을 확인할 수 있어요.',
          onTap: () => openVisits(context),
        ),
        const SizedBox(height: 12),
        _MenuCard(
          icon: Icons.description_outlined,
          title: '처방 정보',
          description: '처방된 약 정보를 확인할 수 있어요.',
          onTap: () => openPrescriptions(context, apiClient),
        ),
      ],
    );
  }
}

class _ResultsHeroBanner extends StatelessWidget {
  const _ResultsHeroBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 156,
      decoration: BoxDecoration(
        color: _soft,
        borderRadius: BorderRadius.circular(24),
      ),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 10, 8),
        child: Row(
          children: [
            Expanded(
              flex: 6,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 9,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFDCD6FA),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: const Text(
                      '건강한 오늘, 더 든든한 내일',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: _primary,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '검사 결과와\n진료 기록을\n한눈에 확인하세요!',
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: _text,
                      fontSize: 17,
                      height: 1.18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    '호짱이와 함께\n더 건강한 하루를 만들어가요.',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: _muted,
                      fontSize: 10,
                      height: 1.35,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 105,
              height: 125,
              child: Image.asset(
                'assets/images/image2.png',
                fit: BoxFit.contain,
                alignment: Alignment.bottomCenter,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MenuCard extends StatelessWidget {
  const _MenuCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Ink(
        height: 82,
        padding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 10,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(
            color: const Color(0xFFDCD9F4),
          ),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: _soft,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                icon,
                color: _primary,
                size: 24,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: _text,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    description,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: _muted,
                      fontSize: 12,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(
              Icons.chevron_right_rounded,
              color: _primary,
              size: 25,
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultsListPage extends StatefulWidget {
  const _ResultsListPage({required this.apiClient});

  final ApiClient apiClient;

  @override
  State<_ResultsListPage> createState() => _ResultsListPageState();
}

class _ResultsListPageState extends State<_ResultsListPage> {
  late final TestResultsApi _api = TestResultsApi(widget.apiClient);
  List<TestResultSummary> _results = const [];
  String? _error;
  bool _loading = true;

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
      final results = await _api.list();
      if (!mounted) return;
      setState(() {
        _results = results;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = '검사 결과를 불러오지 못했습니다.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('검사 결과')),
        body: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
            children: [
              const _ResultsListNoticeBanner(),
              const SizedBox(height: 18),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(36),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error != null)
                _ResultsListErrorState(message: _error!, onRetry: _load)
              else if (_results.isEmpty)
                const _ResultsListEmptyState()
              else
                ..._results.map(
                  (result) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _TestResultListCard(
                      result: result,
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => _TestResultDetailPage(result: result),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
}

class _ResultsListNoticeBanner extends StatelessWidget {
  const _ResultsListNoticeBanner();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, color: _primary, size: 20),
            SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '검사 결과 안내',
                    style: TextStyle(
                      color: _text,
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    '등록된 검사 결과를 확인할 수 있어요.',
                    style: TextStyle(color: _muted, fontSize: 12, height: 1.35),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ResultsListEmptyState extends StatelessWidget {
  const _ResultsListEmptyState();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 42),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Column(
          children: [
            Icon(Icons.biotech_outlined, size: 38, color: _primary),
            SizedBox(height: 14),
            Text(
              '등록된 검사 결과가 없습니다.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _text, fontWeight: FontWeight.w700),
            ),
            SizedBox(height: 7),
            Text(
              '검사 결과가 등록되면 이곳에서 확인할 수 있습니다.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, height: 1.45),
            ),
          ],
        ),
      );
}

class _ResultsListErrorState extends StatelessWidget {
  const _ResultsListErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          children: [
            const Icon(Icons.error_outline_rounded, color: _primary, size: 36),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('다시 시도'),
            ),
          ],
        ),
      );
}

class _TestResultListCard extends StatelessWidget {
  const _TestResultListCard({required this.result, required this.onTap});

  final TestResultSummary result;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: const Color(0xFFDCD9F4)),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _formatTestResultDate(result.studyDatetime),
                      style: const TextStyle(color: _muted, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _ModalityBadge(modalities: result.modalities),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            result.studyDescription.isEmpty
                                ? '-'
                                : result.studyDescription,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: _text,
                              fontSize: 15,
                              height: 1.3,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right_rounded, color: _primary),
            ],
          ),
        ),
      );
}

class _TestResultDetailPage extends StatelessWidget {
  const _TestResultDetailPage({required this.result});

  final TestResultSummary result;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('검사 결과 상세')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            const _TestResultDetailBanner(),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: _border),
                borderRadius: BorderRadius.circular(22),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('검사명',
                      style: TextStyle(color: _muted, fontSize: 13)),
                  const SizedBox(height: 7),
                  Text(
                    result.studyDescription.isEmpty
                        ? '-'
                        : result.studyDescription,
                    style: const TextStyle(
                      color: _text,
                      fontSize: 21,
                      height: 1.3,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 20),
                  _TestResultDetailItem(
                    icon: Icons.calendar_month_outlined,
                    label: '검사 일시',
                    child: Text(
                      _formatTestResultDate(result.studyDatetime),
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _TestResultDetailItem(
                    icon: Icons.biotech_outlined,
                    label: '검사 종류',
                    child: _ModalityBadge(modalities: result.modalities),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _TestResultDetailBanner extends StatelessWidget {
  const _TestResultDetailBanner();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, color: _primary, size: 23),
            SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '검사 결과 안내',
                    style: TextStyle(
                      color: _text,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  SizedBox(height: 5),
                  Text(
                    '검사 결과를 확인해보세요.',
                    style: TextStyle(
                      color: _text,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  SizedBox(height: 3),
                  Text(
                    '검사 일시, 검사 종류, 검사명을 확인할 수 있어요.',
                    style: TextStyle(color: _muted, fontSize: 12, height: 1.4),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _TestResultDetailItem extends StatelessWidget {
  const _TestResultDetailItem({
    required this.icon,
    required this.label,
    required this.child,
  });

  final IconData icon;
  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFFAFAFF),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: _soft,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: _primary, size: 21),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(color: _muted, fontSize: 12)),
                  const SizedBox(height: 4),
                  child,
                ],
              ),
            ),
          ],
        ),
      );
}

class _ModalityBadge extends StatelessWidget {
  const _ModalityBadge({required this.modalities});

  final List<String> modalities;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        decoration: BoxDecoration(
          color: _soft,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(
          modalities.isEmpty ? '-' : modalities.join(' · '),
          style: const TextStyle(
            color: _primary,
            fontSize: 13,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _VisitDetailPage extends StatelessWidget {
  const _VisitDetailPage();

  @override
  Widget build(BuildContext context) {
    return const _DetailScaffold(
      title: '진료 내역 상세',
      icon: Icons.medical_information_outlined,
      emptyTitle: '등록된 진료 내역이 없습니다.',
      description: '진료 기록이 등록되면 이곳에서 확인할 수 있습니다.',
    );
  }
}

class _PrescriptionDetailPage extends StatelessWidget {
  const _PrescriptionDetailPage();

  @override
  Widget build(BuildContext context) {
    return const _DetailScaffold(
      title: '처방 정보',
      icon: Icons.receipt_long_outlined,
      emptyTitle: '등록된 처방 정보가 없습니다.',
      description: '처방 정보가 등록되면 이곳에서 확인할 수 있습니다.',
    );
  }
}

class _DetailScaffold extends StatelessWidget {
  const _DetailScaffold({
    required this.title,
    required this.icon,
    required this.emptyTitle,
    required this.description,
  });

  final String title;
  final IconData icon;
  final String emptyTitle;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
      body: Center(
        child: Container(
          margin: const EdgeInsets.all(20),
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: 24,
            vertical: 42,
          ),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: _border),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 38,
                color: _primary,
              ),
              const SizedBox(height: 14),
              Text(
                emptyTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: _text,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 7),
              Text(
                description,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: _muted,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
