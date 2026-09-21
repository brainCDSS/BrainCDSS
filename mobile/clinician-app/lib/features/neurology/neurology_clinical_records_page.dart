import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyPatientClinicalRecordsSection extends StatefulWidget {
  const NeurologyPatientClinicalRecordsSection({
    super.key,
    required this.apiClient,
    required this.patientId,
    required this.currentUserId,
  });

  final ClinicianApiClient apiClient;
  final String patientId;
  final String currentUserId;

  @override
  State<NeurologyPatientClinicalRecordsSection> createState() =>
      _NeurologyPatientClinicalRecordsSectionState();
}

class _NeurologyPatientClinicalRecordsSectionState
    extends State<NeurologyPatientClinicalRecordsSection> {
  List<Map<String, dynamic>> _encounters = const [];
  List<Map<String, dynamic>> _notes = const [];
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
      final encounters = (await widget.apiClient.getList(
        '/api/v1/encounters',
        query: {'patient_id': widget.patientId},
      ))
          .whereType<Map>()
          .map(Map<String, dynamic>.from)
          .toList();
      final notes = <Map<String, dynamic>>[];
      for (final encounter in encounters.take(5)) {
        final id = encounter['id']?.toString() ?? '';
        if (id.isEmpty) continue;
        final response = await widget.apiClient.get(
          '/api/v1/clinical-notes',
          query: {'encounter_id': id},
        );
        for (final item in response['results'] as List? ?? const []) {
          if (item is Map) {
            notes.add(
                {...Map<String, dynamic>.from(item), '_encounter': encounter});
          }
        }
      }
      notes.sort((a, b) => (b['updated_at']?.toString() ?? '')
          .compareTo(a['updated_at']?.toString() ?? ''));
      if (mounted)
        setState(() {
          _encounters = encounters;
          _notes = notes;
        });
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '진료기록을 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) =>
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const RadiologySectionTitle(title: '진료기록'),
        const SizedBox(height: 10),
        if (_loading)
          const Center(
              child: Padding(
                  padding: EdgeInsets.all(20),
                  child: CircularProgressIndicator()))
        else if (_error != null)
          RadiologyInfoCard(
              child: Column(children: [
            Text(_error!),
            TextButton(onPressed: _load, child: const Text('다시 시도'))
          ]))
        else if (_notes.isEmpty)
          const RadiologyEmptyState(
              icon: Icons.description_outlined, message: '등록된 진료기록이 없습니다.')
        else
          ..._notes.map((note) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: InkWell(
                borderRadius: BorderRadius.circular(18),
                onTap: () async {
                  final id = note['note_id']?.toString() ??
                      note['id']?.toString() ??
                      '';
                  if (id.isEmpty) return;
                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => NeurologyClinicalNoteDetailPage(
                        apiClient: widget.apiClient,
                        noteId: id,
                        currentUserId: widget.currentUserId,
                        readOnly: true,
                      ),
                    ),
                  );
                  if (mounted) _load();
                },
                child: RadiologyInfoCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(children: [
                      const Icon(Icons.description_outlined,
                          color: radiologyBlue),
                      const SizedBox(width: 12),
                      Expanded(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                            Text(
                                (note['assessment_summary'] ??
                                        note['assessment'] ??
                                        '진료기록')
                                    .toString(),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    color: radiologyNavy,
                                    fontWeight: FontWeight.w800)),
                            const SizedBox(height: 4),
                            Text(
                                (note['clinical_opinion_summary'] ??
                                        note['clinical_opinion'] ??
                                        '')
                                    .toString(),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    color: radiologyMuted, fontSize: 12)),
                            const SizedBox(height: 5),
                            Text(
                                _formatClinicalDateTime(
                                    note['updated_at']?.toString()),
                                style: const TextStyle(
                                    color: radiologyMuted, fontSize: 11)),
                          ])),
                      _ClinicalStatusChip(
                          status: note['status']?.toString() ?? ''),
                      const Icon(Icons.chevron_right_rounded,
                          color: radiologyMuted),
                    ])),
              ))),
      ]);
}

class NeurologyClinicalRecordsPage extends StatefulWidget {
  const NeurologyClinicalRecordsPage({
    super.key,
    required this.apiClient,
    required this.onOpenDetail,
  });

  final ClinicianApiClient apiClient;
  final ValueChanged<String> onOpenDetail;

  @override
  State<NeurologyClinicalRecordsPage> createState() =>
      _NeurologyClinicalRecordsPageState();
}

class _NeurologyClinicalRecordsPageState
    extends State<NeurologyClinicalRecordsPage> {
  List<_ClinicalPatient> _patients = const [];
  List<_ClinicalEncounter> _encounters = const [];
  List<_ClinicalNoteSummary> _notes = const [];
  _ClinicalPatient? _patient;
  _ClinicalEncounter? _encounter;
  bool _loadingPatients = true;
  bool _loadingNotes = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPatients();
  }

  Future<void> _loadPatients() async {
    setState(() {
      _loadingPatients = true;
      _error = null;
    });
    try {
      final response = await widget.apiClient.get('/api/v1/patients');
      final patients = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) =>
              _ClinicalPatient.fromJson(Map<String, dynamic>.from(item)))
          .where((item) => item.id.isNotEmpty)
          .toList(growable: false);
      if (mounted) setState(() => _patients = patients);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '환자 목록을 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loadingPatients = false);
    }
  }

  Future<void> _selectPatient(_ClinicalPatient? patient) async {
    setState(() {
      _patient = patient;
      _encounter = null;
      _encounters = const [];
      _notes = const [];
      _error = null;
      _loadingNotes = patient != null;
    });
    if (patient == null) return;
    try {
      final rows = await widget.apiClient
          .getList('/api/v1/encounters', query: {'patient_id': patient.id});
      final encounters = rows
          .whereType<Map>()
          .map((item) =>
              _ClinicalEncounter.fromJson(Map<String, dynamic>.from(item)))
          .where((item) => item.id.isNotEmpty)
          .toList(growable: false);
      if (!mounted) return;
      setState(() => _encounters = encounters);
      if (encounters.isNotEmpty) await _selectEncounter(encounters.first);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Encounter를 불러오지 못했습니다.');
    } finally {
      if (mounted && _encounters.isEmpty) setState(() => _loadingNotes = false);
    }
  }

  Future<void> _selectEncounter(_ClinicalEncounter? encounter) async {
    setState(() {
      _encounter = encounter;
      _notes = const [];
      _error = null;
      _loadingNotes = encounter != null;
    });
    if (encounter == null) return;
    try {
      final response = await widget.apiClient
          .get('/api/v1/clinical-notes', query: {'encounter_id': encounter.id});
      final notes = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) =>
              _ClinicalNoteSummary.fromJson(Map<String, dynamic>.from(item)))
          .where((item) => item.id.isNotEmpty)
          .toList(growable: false);
      if (mounted) setState(() => _notes = notes);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '진료기록을 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loadingNotes = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '진료기록'),
          const SizedBox(height: 8),
          const Text('환자와 Encounter를 선택해 진료기록을 확인합니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 13)),
          const SizedBox(height: 16),
          if (_loadingPatients)
            const Center(
                child: Padding(
                    padding: EdgeInsets.all(28),
                    child: CircularProgressIndicator()))
          else if (_error != null && _patients.isEmpty)
            _ClinicalRetryCard(message: _error!, onRetry: _loadPatients)
          else ...[
            _SelectorCard<_ClinicalPatient>(
              label: '환자',
              value: _patient,
              items: _patients,
              itemLabel: (item) => item.label,
              onChanged: _selectPatient,
            ),
            const SizedBox(height: 10),
            _SelectorCard<_ClinicalEncounter>(
              label: 'Encounter',
              value: _encounter,
              items: _encounters,
              itemLabel: (item) => item.label,
              onChanged: _selectEncounter,
            ),
            const SizedBox(height: 18),
            if (_loadingNotes)
              const Center(
                  child: Padding(
                      padding: EdgeInsets.all(28),
                      child: CircularProgressIndicator()))
            else if (_error != null)
              _ClinicalRetryCard(
                  message: _error!, onRetry: () => _selectEncounter(_encounter))
            else if (_patient == null)
              const RadiologyEmptyState(
                  icon: Icons.person_search_outlined, message: '환자를 선택해 주세요.')
            else if (_encounters.isEmpty)
              const RadiologyEmptyState(
                  icon: Icons.event_busy_outlined,
                  message: '조회 가능한 Encounter가 없습니다.')
            else if (_notes.isEmpty)
              const RadiologyEmptyState(
                  icon: Icons.description_outlined, message: '등록된 진료기록이 없습니다.')
            else
              ..._notes.map((note) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: InkWell(
                      onTap: () => widget.onOpenDetail(note.id),
                      borderRadius: BorderRadius.circular(18),
                      child: RadiologyInfoCard(
                        padding: const EdgeInsets.all(14),
                        child: Row(children: [
                          const Icon(Icons.description_outlined,
                              color: radiologyBlue),
                          const SizedBox(width: 12),
                          Expanded(
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                Text(
                                    note.assessmentSummary.isEmpty
                                        ? '진료기록'
                                        : note.assessmentSummary,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                        color: radiologyNavy,
                                        fontWeight: FontWeight.w800)),
                                if (note.clinicalOpinionSummary.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text(note.clinicalOpinionSummary,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                          color: radiologyMuted, fontSize: 12))
                                ],
                                const SizedBox(height: 5),
                                Text(_formatClinicalDateTime(note.updatedAt),
                                    style: const TextStyle(
                                        color: radiologyMuted, fontSize: 11)),
                              ])),
                          _ClinicalStatusChip(status: note.status),
                          const SizedBox(width: 4),
                          const Icon(Icons.chevron_right_rounded,
                              color: radiologyMuted),
                        ]),
                      ),
                    ),
                  )),
          ],
        ],
      );
}

class NeurologyClinicalNoteDetailPage extends StatefulWidget {
  const NeurologyClinicalNoteDetailPage(
      {super.key,
      required this.apiClient,
      required this.noteId,
      required this.currentUserId,
      this.readOnly = false});
  final ClinicianApiClient apiClient;
  final String noteId;
  final String currentUserId;
  final bool readOnly;
  @override
  State<NeurologyClinicalNoteDetailPage> createState() =>
      _NeurologyClinicalNoteDetailPageState();
}

class _NeurologyClinicalNoteDetailPageState
    extends State<NeurologyClinicalNoteDetailPage> {
  _ClinicalNoteDetail? _note;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  final _subjective = TextEditingController();
  final _objective = TextEditingController();
  final _assessment = TextEditingController();
  final _plan = TextEditingController();
  final _opinion = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _subjective.dispose();
    _objective.dispose();
    _assessment.dispose();
    _plan.dispose();
    _opinion.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response =
          await widget.apiClient.get('/api/v1/clinical-notes/${widget.noteId}');
      final note = _ClinicalNoteDetail.fromJson(response);
      if (!mounted) return;
      _subjective.text = note.subjective;
      _objective.text = note.objective;
      _assessment.text = note.assessment;
      _plan.text = note.plan;
      _opinion.text = note.clinicalOpinion;
      setState(() => _note = note);
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '진료기록 상세를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  bool get _editable =>
      !widget.readOnly &&
      _note?.status == 'DRAFT' &&
      _note?.authorId == widget.currentUserId;
  Map<String, dynamic> get _draft => {
        'subjective': _subjective.text,
        'objective': _objective.text,
        'assessment': _assessment.text,
        'plan': _plan.text,
        'clinical_opinion': _opinion.text
      };
  Future<void> _save() async => _submit(finalize: false);
  Future<void> _finalize() async => _submit(finalize: true);
  Future<void> _submit({required bool finalize}) async {
    final note = _note;
    if (!_editable || _saving || note == null) return;
    setState(() => _saving = true);
    try {
      if (finalize) {
        await widget.apiClient
            .patch('/api/v1/clinical-notes/${note.id}', body: _draft);
        await widget.apiClient
            .post('/api/v1/clinical-notes/${note.id}/finalize');
      } else {
        await widget.apiClient
            .patch('/api/v1/clinical-notes/${note.id}', body: _draft);
      }
      await _load();
    } on ClinicianApiException catch (error) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('진료기록을 저장하지 못했습니다.')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null)
      return Scaffold(
        body: _ClinicalRetryCard(
          message: _error ?? '진료기록 상세를 불러오지 못했습니다.',
          onRetry: _load,
        ),
      );
    final note = _note;
    if (note == null) {
      return const Scaffold(
        body: RadiologyEmptyState(
          icon: Icons.description_outlined,
          message: '등록된 진료기록이 없습니다.',
        ),
      );
    }
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
            Row(children: [
              const Expanded(
                child: RadiologySectionTitle(title: '진료기록 상세'),
              ),
              const SizedBox(width: 8),
              _ClinicalStatusChip(status: note.status)
            ]),
            const SizedBox(height: 12),
            ..._soapFields.map((field) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _SoapField(
                    label: field.label,
                    controller: field.controller(this),
                    enabled: _editable))),
            if (note.finalizedAt?.trim().isNotEmpty == true)
              Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                      '최종 확정 ${_formatClinicalDateTime(note.finalizedAt)}',
                      style: const TextStyle(
                          color: radiologySuccess, fontSize: 12))),
            if (_editable) ...[
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                    child: OutlinedButton(
                        onPressed: _saving ? null : _save,
                        child: Text(_saving ? '저장 중' : '임시저장'))),
                const SizedBox(width: 10),
                Expanded(
                    child: FilledButton(
                        onPressed: _saving ? null : _finalize,
                        child: const Text('최종확정')))
              ]),
            ] else ...[
              const SizedBox(height: 12),
              const Text('최종확정 기록 또는 다른 작성자의 기록은 읽기 전용입니다.',
                  style: TextStyle(color: radiologyMuted, fontSize: 12))
            ],
          ],
        ),
      ),
    );
  }
}

class _SoapFieldSpec {
  const _SoapFieldSpec(this.label, this.controller);
  final String label;
  final TextEditingController Function(_NeurologyClinicalNoteDetailPageState)
      controller;
}

final _soapFields = <_SoapFieldSpec>[
  _SoapFieldSpec('Subjective', (state) => state._subjective),
  _SoapFieldSpec('Objective', (state) => state._objective),
  _SoapFieldSpec('Assessment', (state) => state._assessment),
  _SoapFieldSpec('Plan', (state) => state._plan),
  _SoapFieldSpec('임상 소견', (state) => state._opinion),
];

class _SoapField extends StatelessWidget {
  const _SoapField(
      {required this.label, required this.controller, required this.enabled});
  final String label;
  final TextEditingController controller;
  final bool enabled;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: const TextStyle(
                color: radiologyNavy, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        if (enabled)
          TextField(
              controller: controller,
              minLines: 2,
              maxLines: 5,
              decoration: const InputDecoration(border: OutlineInputBorder()))
        else
          Text(
            _clinicalText(controller.text),
            style: const TextStyle(color: radiologyNavy, height: 1.5),
          )
      ]));
}

String _clinicalText(String value) => value.trim().isEmpty ? '기록 없음' : value;

class _SelectorCard<T> extends StatelessWidget {
  const _SelectorCard(
      {required this.label,
      required this.value,
      required this.items,
      required this.itemLabel,
      required this.onChanged});
  final String label;
  final T? value;
  final List<T> items;
  final String Function(T) itemLabel;
  final ValueChanged<T?> onChanged;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      child: DropdownButtonFormField<T>(
          value: value,
          isExpanded: true,
          decoration:
              InputDecoration(labelText: label, border: InputBorder.none),
          items: items
              .map((item) => DropdownMenuItem(
                  value: item,
                  child:
                      Text(itemLabel(item), overflow: TextOverflow.ellipsis)))
              .toList(),
          onChanged: items.isEmpty ? null : onChanged));
}

class _ClinicalStatusChip extends StatelessWidget {
  const _ClinicalStatusChip({required this.status});
  final String status;
  @override
  Widget build(BuildContext context) => RadiologyStatusChip(
      label: status == 'FINAL'
          ? '확정'
          : status == 'DRAFT'
              ? '작성 중'
              : status,
      color: status == 'FINAL' ? radiologySuccess : radiologyBlue);
}

class _ClinicalRetryCard extends StatelessWidget {
  const _ClinicalRetryCard({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
          child: Column(children: [
        Text(message),
        TextButton(onPressed: onRetry, child: const Text('다시 시도'))
      ]));
}

class _ClinicalPatient {
  const _ClinicalPatient(this.id, this.name, this.patientNo);
  factory _ClinicalPatient.fromJson(Map<String, dynamic> json) =>
      _ClinicalPatient(json['id']?.toString() ?? '',
          json['name']?.toString() ?? '', json['patient_no']?.toString() ?? '');
  final String id;
  final String name;
  final String patientNo;
  String get label => [
        if (name.isNotEmpty) name,
        if (patientNo.isNotEmpty) patientNo
      ].join(' · ');
}

class _ClinicalEncounter {
  const _ClinicalEncounter(this.id, this.no, this.status, this.arrivedAt);
  factory _ClinicalEncounter.fromJson(Map<String, dynamic> json) =>
      _ClinicalEncounter(
          json['id']?.toString() ?? '',
          json['encounter_no']?.toString() ?? '',
          json['status']?.toString() ?? '',
          json['arrived_at']?.toString());
  final String id;
  final String no;
  final String status;
  final String? arrivedAt;
  String get label => [
        if (no.isNotEmpty) no,
        if (status.isNotEmpty) status,
        if (arrivedAt != null) _formatClinicalDateTime(arrivedAt)
      ].join(' · ');
}

class _ClinicalNoteSummary {
  const _ClinicalNoteSummary(this.id, this.status, this.assessmentSummary,
      this.clinicalOpinionSummary, this.updatedAt);
  factory _ClinicalNoteSummary.fromJson(Map<String, dynamic> json) =>
      _ClinicalNoteSummary(
          json['note_id']?.toString() ?? json['id']?.toString() ?? '',
          json['status']?.toString() ?? '',
          json['assessment_summary']?.toString() ?? '',
          json['clinical_opinion_summary']?.toString() ?? '',
          json['updated_at']?.toString());
  final String id, status, assessmentSummary, clinicalOpinionSummary;
  final String? updatedAt;
}

class _ClinicalNoteDetail {
  const _ClinicalNoteDetail(
      {required this.id,
      required this.authorId,
      required this.status,
      required this.subjective,
      required this.objective,
      required this.assessment,
      required this.plan,
      required this.clinicalOpinion,
      required this.finalizedAt});
  factory _ClinicalNoteDetail.fromJson(Map<String, dynamic> json) {
    final author = json['author'];
    return _ClinicalNoteDetail(
        id: json['note_id']?.toString() ?? json['id']?.toString() ?? '',
        authorId: json['author_id']?.toString() ??
            (author is Map
                ? (author['id'] ?? author['user_id'])?.toString() ?? ''
                : author?.toString() ?? ''),
        status: json['status']?.toString() ?? '',
        subjective: json['subjective']?.toString() ?? '',
        objective: json['objective']?.toString() ?? '',
        assessment: json['assessment']?.toString() ?? '',
        plan: json['plan']?.toString() ?? '',
        clinicalOpinion: json['clinical_opinion']?.toString() ?? '',
        finalizedAt: json['finalized_at']?.toString());
  }
  final String id,
      authorId,
      status,
      subjective,
      objective,
      assessment,
      plan,
      clinicalOpinion;
  final String? finalizedAt;
}

String _formatClinicalDateTime(String? value) {
  final date = value == null ? null : DateTime.tryParse(value)?.toLocal();
  return date == null
      ? (value ?? '-')
      : '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
}
