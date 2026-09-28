import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import 'clinical_history_api.dart';

const _primary = Color(0xFF7567C8);
const _hodocBlue = Color(0xFF356FAF);
const _soft = Color(0xFFEEEAFE);
const _border = Color(0xFFCFD7E8);
const _text = Color(0xFF263A5A);
const _muted = Color(0xFF65758D);

class TestResultsPage extends StatefulWidget {
  const TestResultsPage(
      {super.key,
      required this.apiClient,
      this.selectedEncounterId,
      this.onOpenDetail,
      this.onCloseDetail,
      this.onOpenMedications});
  final ApiClient apiClient;
  final String? selectedEncounterId;
  final ValueChanged<String>? onOpenDetail;
  final VoidCallback? onCloseDetail;
  final VoidCallback? onOpenMedications;
  @override
  State<TestResultsPage> createState() => _TestResultsPageState();
}

class _TestResultsPageState extends State<TestResultsPage> {
  late final ClinicalHistoryApi _api = ClinicalHistoryApi(widget.apiClient);
  List<ClinicalHistoryItem> _items = const [];
  String _query = '';
  String? _error;
  bool _loading = true;
  ClinicalHistoryDetail? _detail;
  String? _detailError;
  bool _detailLoading = false;

  @override
  void initState() {
    super.initState();
    _loadList();
    _loadDetail();
  }

  @override
  void didUpdateWidget(covariant TestResultsPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedEncounterId != widget.selectedEncounterId) {
      _loadDetail();
    }
  }

  Future<void> _loadList() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await _api.list();
      if (!mounted) {
        return;
      }
      setState(() {
        _items = items;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '진료내역을 불러오지 못했습니다.';
        _loading = false;
      });
    }
  }

  Future<void> _loadDetail() async {
    final id = widget.selectedEncounterId;
    if (id == null) {
      _detail = null;
      _detailError = null;
      _detailLoading = false;
      return;
    }
    setState(() {
      _detail = null;
      _detailError = null;
      _detailLoading = true;
    });
    try {
      final detail = await _api.detail(id);
      if (!mounted) {
        return;
      }
      setState(() {
        _detail = detail;
        _detailLoading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _detailError = error.message;
        _detailLoading = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _detailError = '진료내역 상세를 불러오지 못했습니다.';
        _detailLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) =>
      widget.selectedEncounterId == null ? _list() : _detailPage();

  Widget _list() {
    final query = _query.trim().toLowerCase();
    final shown = query.isEmpty
        ? _items
        : _items
            .where((item) => [
                  item.departmentName,
                  item.clinicianName,
                  ...item.examNames
                ].whereType<String>().join(' ').toLowerCase().contains(query))
            .toList();
    return RefreshIndicator(
        onRefresh: _loadList,
        child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
            children: [
              const _Banner(),
              const SizedBox(height: 16),
              TextField(
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                      hintText: '진료과, 담당 의료진, 검사명 검색',
                      prefixIcon: const Icon(Icons.search_rounded),
                      filled: true,
                      fillColor: Colors.white,
                      enabledBorder: _outline(),
                      border: _outline())),
              const SizedBox(height: 16),
              Row(children: [
                Text('진료내역 ${shown.length}건',
                    style: const TextStyle(
                        color: _text,
                        fontSize: 18,
                        fontWeight: FontWeight.w800)),
                const Spacer(),
                const Text('최신순', style: TextStyle(color: _muted, fontSize: 13))
              ]),
              const SizedBox(height: 10),
              if (_loading)
                const Padding(
                    padding: EdgeInsets.all(36),
                    child: Center(child: CircularProgressIndicator()))
              else if (_error != null)
                _StateCard(message: _error!, onRetry: _loadList)
              else if (shown.isEmpty)
                const _StateCard(
                    message: '등록된 진료내역이 없습니다.\n진료와 검사 기록이 등록되면 이곳에 표시됩니다.')
              else
                ...shown.map((item) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _ListCard(
                        item: item,
                        onTap: () =>
                            widget.onOpenDetail?.call(item.encounterId)))),
            ]));
  }

  Widget _detailPage() {
    if (_detailLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_detailError != null) {
      return Padding(
          padding: const EdgeInsets.all(20),
          child: _StateCard(message: _detailError!, onRetry: _loadDetail));
    }
    final detail = _detail;
    if (detail == null) {
      return const SizedBox.shrink();
    }
    final exams = detail.exams;
    return ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          _Group(title: '진료 정보', compact: true, children: [
            _row('진료일시', _date(detail.visitedAt)),
            _row('진료과', detail.departmentName ?? '진료과 정보 없음'),
            _row('담당 의료진', detail.clinicianName ?? '담당 의료진 정보 없음'),
            _row('진료 유형', _encounterType(detail.encounterType))
          ]),
          const SizedBox(height: 10),
          _Group(title: '검사 내역', children: [
            if (exams.isEmpty)
              const Text('검사 정보가 없습니다', style: TextStyle(color: _muted))
            else
              ...exams.map((exam) => _ExamRow(exam: exam))
          ]),
          const SizedBox(height: 10),
          _Group(title: '의사소견', compact: true, children: [
            Text(
                detail.clinicalOpinion?.trim().isNotEmpty == true
                    ? detail.clinicalOpinion!
                    : '정보 없음',
                style: const TextStyle(color: _text, height: 1.55))
          ]),
          const SizedBox(height: 10),
          _Group(title: '처방', children: [
            _PrescriptionStatus(
                hasPrescription: detail.hasPrescription,
                onOpenMedications: widget.onOpenMedications)
          ]),
        ]);
  }
}

OutlineInputBorder _outline() => OutlineInputBorder(
    borderRadius: BorderRadius.circular(16),
    borderSide: const BorderSide(color: _border));

class _Banner extends StatelessWidget {
  const _Banner();
  @override
  Widget build(BuildContext context) => Container(
      height: 142,
      padding: const EdgeInsets.fromLTRB(18, 18, 8, 10),
      decoration:
          BoxDecoration(color: _soft, borderRadius: BorderRadius.circular(22)),
      child: Row(children: [
        const Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('나의 진료내역',
              style: TextStyle(
                  color: _primary, fontSize: 13, fontWeight: FontWeight.w800)),
          SizedBox(height: 9),
          Text('진료 방문 기록과 관련\n검사·처방 정보를 확인하세요.',
              style: TextStyle(
                  color: _text,
                  fontSize: 19,
                  height: 1.25,
                  fontWeight: FontWeight.w800)),
          SizedBox(height: 6),
          Text('기록은 최신 진료 순으로 표시됩니다.',
              style: TextStyle(color: _muted, fontSize: 11))
        ])),
        Image(
            image: AssetImage('assets/images/image2.png'),
            width: 102,
            height: 112)
      ]));
}

class _ListCard extends StatelessWidget {
  const _ListCard({required this.item, required this.onTap});
  final ClinicalHistoryItem item;
  final VoidCallback onTap;
  String get _examSummary {
    if (item.examNames.isEmpty) {
      return '검사 없음';
    }
    if (item.examNames.length == 1) {
      return item.examNames.first;
    }
    return '${item.examNames.first} 외 ${item.examNames.length - 1}건';
  }

  @override
  Widget build(BuildContext context) => Material(
      color: Colors.transparent,
      child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Ink(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border.all(color: _border),
                  borderRadius: BorderRadius.circular(18)),
              child:
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                      Text(item.departmentName ?? '진료과 정보 없음',
                          style: const TextStyle(
                              color: _hodocBlue,
                              fontSize: 16,
                              fontWeight: FontWeight.w700)),
                      const SizedBox(height: 3),
                      Text(item.clinicianName ?? '담당 의료진 정보 없음',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: _muted, fontSize: 13)),
                      const SizedBox(height: 12),
                      _ListMeta(label: '진료일시', value: _date(item.visitedAt)),
                      const SizedBox(height: 5),
                      Row(children: [
                        Expanded(
                            child: _ListMeta(
                                label: '검사', value: _examSummary)),
                        const SizedBox(width: 10),
                        _PrescriptionBadge(
                            hasPrescription: item.hasPrescription),
                      ])
                    ])),
                const Padding(
                    padding: EdgeInsets.only(top: 18),
                    child: Icon(Icons.chevron_right_rounded, color: _hodocBlue))
              ]))));
}

class _ListMeta extends StatelessWidget {
  const _ListMeta({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(children: [
        Text('$label ', style: const TextStyle(color: _muted, fontSize: 12)),
        Expanded(
            child: Text(value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: _text, fontSize: 13))),
      ]);
}

class _Group extends StatelessWidget {
  const _Group(
      {required this.title, required this.children, this.compact = false});
  final String title;
  final List<Widget> children;
  final bool compact;
  @override
  Widget build(BuildContext context) => Container(
      padding: EdgeInsets.all(compact ? 14 : 16),
      decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title,
            style: const TextStyle(
                color: _text, fontSize: 16, fontWeight: FontWeight.w800)),
        SizedBox(height: compact ? 8 : 10),
        ...children
      ]));
}

Widget _row(String label, String value) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
          width: 78,
          child:
              Text(label, style: const TextStyle(color: _muted, fontSize: 12))),
      Expanded(
          child: Text(value,
              style: const TextStyle(color: _text, fontSize: 14, height: 1.35)))
    ]));

class _ExamRow extends StatelessWidget {
  const _ExamRow({required this.exam});
  final ClinicalHistoryExam exam;
  @override
  Widget build(BuildContext context) => Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 7),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
          color: const Color(0xFFFAFAFF),
          borderRadius: BorderRadius.circular(13)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(exam.name.isEmpty ? '검사명 정보 없음' : exam.name,
            style: const TextStyle(
                color: _text, fontSize: 15, fontWeight: FontWeight.w800)),
        const SizedBox(height: 3),
        Text(_date(exam.examDate),
            style: const TextStyle(color: _muted, fontSize: 12))
      ]));
}

class _PrescriptionStatus extends StatelessWidget {
  const _PrescriptionStatus(
      {required this.hasPrescription, this.onOpenMedications});
  final bool hasPrescription;
  final VoidCallback? onOpenMedications;
  @override
  Widget build(BuildContext context) {
    if (hasPrescription) {
      return Row(children: [
        const _PrescriptionBadge(hasPrescription: true),
        const Spacer(),
        if (onOpenMedications != null)
          FilledButton.icon(
              onPressed: onOpenMedications,
              icon: const Icon(Icons.medication_outlined, size: 18),
              label: const Text('복약 정보 보기'))
      ]);
    }
    return const Row(children: [
      Icon(Icons.medication_outlined, color: _muted, size: 21),
      SizedBox(width: 9),
      Expanded(
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('처방된 약이 없습니다.',
            style: TextStyle(color: _text, fontWeight: FontWeight.w700)),
        SizedBox(height: 2),
        Text('이번 진료에서 등록된 처방이 없습니다.',
            style: TextStyle(color: _muted, fontSize: 12))
      ]))
    ]);
  }
}

class _PrescriptionBadge extends StatelessWidget {
  const _PrescriptionBadge({required this.hasPrescription});
  final bool hasPrescription;
  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
          color: hasPrescription ? const Color(0xFFE6F5EE) : _soft,
          borderRadius: BorderRadius.circular(99)),
      child: Text(hasPrescription ? '처방 있음' : '처방 없음',
          style: TextStyle(
              color: hasPrescription ? const Color(0xFF2E8B64) : _primary,
              fontSize: 12,
              fontWeight: FontWeight.w700)));
}

class _StateCard extends StatelessWidget {
  const _StateCard({required this.message, this.onRetry});
  final String message;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: _border),
          borderRadius: BorderRadius.circular(20)),
      child: Column(children: [
        const Icon(Icons.medical_information_outlined,
            color: _primary, size: 34),
        const SizedBox(height: 12),
        Text(message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: _muted, height: 1.45)),
        if (onRetry != null) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('다시 시도'))
        ]
      ]));
}

String _encounterType(String? value) {
  switch (value) {
    case 'ER':
    case 'EMERGENCY':
      return '응급 진료';
    case 'OUTPATIENT':
      return '외래 진료';
    default:
      return value ?? '정보 없음';
  }
}

String _date(DateTime? value) {
  if (value == null) {
    return '정보 없음';
  }
  final local = value.toLocal();
  return '${local.year}.${local.month.toString().padLeft(2, '0')}.${local.day.toString().padLeft(2, '0')} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
}
