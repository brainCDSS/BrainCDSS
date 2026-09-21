import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

const _screeningCodes = <String>[
  'BALANCE',
  'EYES',
  'FACE',
  'ARM',
  'SPEECH',
  'CONSCIOUSNESS',
];
const _fastCodes = <String>['FAST_FACE', 'FAST_ARM', 'FAST_SPEECH'];
const _vitalCodes = <String>['BP_SYS', 'BP_DIA', 'HEART_RATE', 'BODY_TEMP'];

class NurseAssessmentWorkItem {
  const NurseAssessmentWorkItem({
    required this.assessmentId,
    required this.encounterId,
    required this.patientName,
    required this.patientNo,
    required this.status,
    required this.triagePriority,
  });

  factory NurseAssessmentWorkItem.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    return NurseAssessmentWorkItem(
      assessmentId: json['assessment_id']?.toString(),
      encounterId: json['encounter_id']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      patientNo: patient?['patient_no']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      triagePriority: json['triage_priority']?.toString(),
    );
  }

  final String? assessmentId;
  final String encounterId;
  final String patientName;
  final String patientNo;
  final String status;
  final String? triagePriority;
}

class NurseAssessmentWorklistPage extends StatefulWidget {
  const NurseAssessmentWorklistPage({super.key, required this.apiClient});

  final ClinicianApiClient apiClient;

  @override
  State<NurseAssessmentWorklistPage> createState() =>
      _NurseAssessmentWorklistPageState();
}

class _NurseAssessmentWorklistPageState
    extends State<NurseAssessmentWorklistPage> {
  List<NurseAssessmentWorkItem> _items = const [];
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
      final response =
          await widget.apiClient.get('/api/v1/assessments/worklist');
      final items = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => NurseAssessmentWorkItem.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(growable: false);
      if (mounted) setState(() => _items = items);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '초기평가 Worklist를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _open(NurseAssessmentWorkItem item) async {
    var assessmentId = item.assessmentId;
    try {
      if (assessmentId == null || assessmentId.isEmpty) {
        final created = await widget.apiClient.post(
          '/api/v1/assessments',
          body: {'encounter_id': item.encounterId},
        );
        assessmentId = created['assessment_id']?.toString();
      }
      if (assessmentId == null || assessmentId.isEmpty) {
        throw const ClinicianApiException(
          statusCode: 500,
          message: '초기평가 식별자가 응답에 없습니다.',
        );
      }
      if (!mounted) return;
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => NurseAssessmentEditorPage(
            apiClient: widget.apiClient,
            assessmentId: assessmentId!,
          ),
        ),
      );
      await _load();
    } on ClinicianApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
            const RadiologySectionTitle(title: '초기평가 Worklist'),
            const SizedBox(height: 8),
            const Text(
              '대기 건은 눌러 평가를 시작하고, 작성 중 건은 이어서 작성합니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 13),
            ),
            const SizedBox(height: 16),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              RadiologyInfoCard(
                child: Column(children: [
                  Text(_error!, textAlign: TextAlign.center),
                  TextButton(onPressed: _load, child: const Text('다시 시도')),
                ]),
              )
            else if (_items.isEmpty)
              const RadiologyEmptyState(
                icon: Icons.fact_check_outlined,
                message: '평가 대상이 없습니다.',
              )
            else
              ..._items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: InkWell(
                    onTap: () => _open(item),
                    borderRadius: BorderRadius.circular(14),
                    child: RadiologyInfoCard(
                      child: Row(children: [
                        const Icon(Icons.fact_check_outlined,
                            color: radiologyBlue),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.patientName.isEmpty
                                    ? '환자 정보 없음'
                                    : item.patientName,
                                style: const TextStyle(
                                  color: radiologyNavy,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${item.patientNo} · ${item.status}',
                                style: const TextStyle(color: radiologyMuted),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right_rounded,
                            color: radiologyMuted),
                      ]),
                    ),
                  ),
                ),
              ),
          ],
        ),
      );
}

class _NeurologistOption {
  const _NeurologistOption(this.userId, this.name);
  final String userId;
  final String name;
}

class NurseAssessmentEditorPage extends StatefulWidget {
  const NurseAssessmentEditorPage({
    super.key,
    required this.apiClient,
    required this.assessmentId,
  });

  final ClinicianApiClient apiClient;
  final String assessmentId;

  @override
  State<NurseAssessmentEditorPage> createState() =>
      _NurseAssessmentEditorPageState();
}

class _NurseAssessmentEditorPageState extends State<NurseAssessmentEditorPage> {
  final _symptom = TextEditingController();
  final _screening = {
    for (final code in _screeningCodes) code: TextEditingController(),
  };
  final _fast = {
    for (final code in _fastCodes) code: TextEditingController(),
  };
  final _vitals = {
    for (final code in _vitalCodes) code: TextEditingController(),
  };
  DateTime? _onsetAt;
  DateTime? _lkwAt;
  List<_NeurologistOption> _neurologists = const [];
  String? _neurologistId;
  String? _triagePriority;
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _symptom.dispose();
    for (final controller in [
      ..._screening.values,
      ..._fast.values,
      ..._vitals.values,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final detail = await widget.apiClient.get(
        '/api/v1/assessments/${widget.assessmentId}',
      );
      _onsetAt = DateTime.tryParse(detail['onset_at']?.toString() ?? '');
      _lkwAt = DateTime.tryParse(detail['lkw_at']?.toString() ?? '');
      _symptom.text = detail['symptom_note']?.toString() ?? '';
      for (final raw in detail['items'] as List? ?? const []) {
        if (raw is! Map) continue;
        final item = Map<String, dynamic>.from(raw);
        final code = item['item_code']?.toString();
        if (code == null) continue;
        if (_screening.containsKey(code)) {
          _screening[code]!.text = item['value_numeric']?.toString() ?? '';
        } else if (_fast.containsKey(code)) {
          _fast[code]!.text = item['value_text']?.toString() ?? '';
        } else if (_vitals.containsKey(code)) {
          _vitals[code]!.text = item['value_numeric']?.toString() ?? '';
        }
      }
      final departmentId = detail['neurology_department_id']?.toString();
      if (departmentId != null && departmentId.isNotEmpty) {
        final response = await widget.apiClient.get(
          '/api/v1/departments/$departmentId/clinicians',
        );
        _neurologists = (response['clinicians'] as List? ?? const [])
            .whereType<Map>()
            .map((item) => _NeurologistOption(
                  item['user_id']?.toString() ?? '',
                  item['name']?.toString() ?? '',
                ))
            .where((item) => item.userId.isNotEmpty)
            .toList(growable: false);
      }
    } on ClinicianApiException catch (error) {
      _error = error.message;
    } catch (_) {
      _error = '평가 정보를 불러오지 못했습니다.';
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> _itemsPayload() => [
        for (final entry in _screening.entries)
          {
            'item_code': entry.key,
            'value_numeric': int.tryParse(entry.value.text),
          },
        for (final entry in _fast.entries)
          {'item_code': entry.key, 'value_text': entry.value.text.trim()},
        for (final entry in _vitals.entries)
          {
            'item_code': entry.key,
            'value_numeric': double.tryParse(entry.value.text),
            'unit': switch (entry.key) {
              'BP_SYS' || 'BP_DIA' => 'mmHg',
              'HEART_RATE' => 'bpm',
              'BODY_TEMP' => '°C',
              _ => '',
            },
          },
      ];

  Future<bool> _save() async {
    setState(() => _saving = true);
    try {
      await widget.apiClient.patch(
        '/api/v1/assessments/${widget.assessmentId}',
        body: {
          'onset_at': _onsetAt?.toIso8601String(),
          'lkw_at': _lkwAt?.toIso8601String(),
          'symptom_note': _symptom.text.trim(),
          'items': _itemsPayload(),
        },
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('임시저장했습니다.')),
        );
      }
      return true;
    } on ClinicianApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.message)),
        );
      }
      return false;
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _complete() async {
    if (_neurologistId == null || _triagePriority == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('담당 신경과와 triage priority를 선택하세요.')),
      );
      return;
    }
    if (!await _save()) return;
    try {
      await widget.apiClient.post(
        '/api/v1/assessments/${widget.assessmentId}/complete',
        body: {
          'assigned_neurologist_id': _neurologistId,
          'triage_priority': _triagePriority,
        },
      );
      if (mounted) Navigator.of(context).pop();
    } on ClinicianApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  Future<DateTime?> _pickDateTime(DateTime? initial) async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      firstDate: DateTime(now.year - 1),
      lastDate: now,
      initialDate: initial?.toLocal() ?? now,
    );
    if (date == null || !mounted) return null;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial?.toLocal() ?? now),
    );
    if (time == null) return null;
    return DateTime(date.year, date.month, date.day, time.hour, time.minute);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('초기평가')),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!, textAlign: TextAlign.center))
                : ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      const RadiologySectionTitle(title: '증상 시각'),
                      const SizedBox(height: 10),
                      _DateTimeField(
                        label: '증상 발생시각',
                        value: _onsetAt,
                        onTap: () async {
                          final value = await _pickDateTime(_onsetAt);
                          if (value != null) setState(() => _onsetAt = value);
                        },
                      ),
                      const SizedBox(height: 8),
                      _DateTimeField(
                        label: 'LKW',
                        value: _lkwAt,
                        onTap: () async {
                          final value = await _pickDateTime(_lkwAt);
                          if (value != null) setState(() => _lkwAt = value);
                        },
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _symptom,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: '증상 메모',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 22),
                      const RadiologySectionTitle(title: '초기 스크리닝 (1~5)'),
                      const SizedBox(height: 10),
                      ..._screening.entries.map(
                        (entry) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: TextField(
                            controller: entry.value,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: entry.key,
                              border: const OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      const RadiologySectionTitle(title: 'FAST'),
                      const SizedBox(height: 10),
                      ..._fast.entries.map(
                        (entry) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: DropdownButtonFormField<String>(
                            initialValue: entry.value.text.isEmpty
                                ? null
                                : entry.value.text,
                            decoration: InputDecoration(
                              labelText: entry.key,
                              border: const OutlineInputBorder(),
                            ),
                            items: const [
                              DropdownMenuItem(
                                  value: 'NORMAL', child: Text('NORMAL')),
                              DropdownMenuItem(
                                  value: 'ABNORMAL', child: Text('ABNORMAL')),
                            ],
                            onChanged: (value) =>
                                entry.value.text = value ?? '',
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      const RadiologySectionTitle(title: 'Vital'),
                      const SizedBox(height: 10),
                      ..._vitals.entries.map(
                        (entry) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: TextField(
                            controller: entry.value,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: InputDecoration(
                              labelText: entry.key,
                              border: const OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      DropdownButtonFormField<String>(
                        initialValue: _neurologistId,
                        decoration: const InputDecoration(
                          labelText: '담당 신경과',
                          border: OutlineInputBorder(),
                        ),
                        items: _neurologists
                            .map((item) => DropdownMenuItem(
                                  value: item.userId,
                                  child: Text(item.name),
                                ))
                            .toList(growable: false),
                        onChanged: (value) =>
                            setState(() => _neurologistId = value),
                      ),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<String>(
                        initialValue: _triagePriority,
                        decoration: const InputDecoration(
                          labelText: 'Triage priority (간호사 선택)',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                              value: 'EMERGENCY', child: Text('EMERGENCY')),
                          DropdownMenuItem(
                              value: 'URGENT', child: Text('URGENT')),
                          DropdownMenuItem(
                              value: 'NON_EMERGENCY',
                              child: Text('NON_EMERGENCY')),
                        ],
                        onChanged: (value) =>
                            setState(() => _triagePriority = value),
                      ),
                      const SizedBox(height: 18),
                      OutlinedButton(
                        onPressed: _saving ? null : _save,
                        child: const Text('임시저장'),
                      ),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: _saving ? null : _complete,
                        child: const Text('평가 완료'),
                      ),
                    ],
                  ),
      );
}

class _DateTimeField extends StatelessWidget {
  const _DateTimeField({
    required this.label,
    required this.value,
    required this.onTap,
  });
  final String label;
  final DateTime? value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ListTile(
        tileColor: Colors.white,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: radiologyBorder),
          borderRadius: BorderRadius.circular(12),
        ),
        title: Text(label),
        subtitle: Text(value?.toLocal().toString() ?? '선택하세요.'),
        trailing: const Icon(Icons.schedule_rounded),
        onTap: onTap,
      );
}
