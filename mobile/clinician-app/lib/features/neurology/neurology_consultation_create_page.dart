import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class NeurologyConsultationCreatePage extends StatefulWidget {
  const NeurologyConsultationCreatePage({
    super.key,
    required this.apiClient,
    required this.patientId,
    required this.patientName,
    required this.patientNo,
    required this.demographics,
  });

  final ClinicianApiClient apiClient;
  final String patientId;
  final String patientName;
  final String patientNo;
  final String demographics;

  @override
  State<NeurologyConsultationCreatePage> createState() =>
      _NeurologyConsultationCreatePageState();
}

class _NeurologyConsultationCreatePageState
    extends State<NeurologyConsultationCreatePage> {
  static const _consultationTypes = <String, String>{
    'RADIOLOGY': '영상의학과',
    'NEUROSURGERY': '신경외과',
  };
  static const _priorities = <String, String>{
    'STAT': '긴급',
    'URGENT': '응급',
    'ROUTINE': '일반',
  };

  final _reasonController = TextEditingController();
  List<_EncounterOption> _encounters = const [];
  final Map<String, String> _departmentIds = {};
  List<_ClinicianOption> _clinicians = const [];
  String? _selectedEncounterId;
  String? _selectedType;
  String? _selectedAssigneeUserId;
  String _priority = 'ROUTINE';
  bool _loading = true;
  bool _loadingClinicians = false;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _reasonController.addListener(_onReasonChanged);
    _loadInitialData();
  }

  @override
  void dispose() {
    _reasonController
      ..removeListener(_onReasonChanged)
      ..dispose();
    super.dispose();
  }

  void _onReasonChanged() => setState(() {});

  Future<void> _loadInitialData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final responses = await Future.wait([
        widget.apiClient.getList(
          '/api/v1/encounters',
          query: {'patient_id': widget.patientId},
        ),
        widget.apiClient.get('/api/v1/hospitals'),
      ]);
      final encounters = (responses[0] as List)
          .whereType<Map>()
          .map((item) =>
              _EncounterOption.fromJson(Map<String, dynamic>.from(item)))
          .where((item) => item.isAvailable)
          .toList(growable: false);
      final hospitals =
          ((responses[1] as Map<String, dynamic>)['results'] as List? ??
                  const [])
              .whereType<Map>()
              .map((item) => item['id']?.toString() ?? '')
              .where((id) => id.isNotEmpty);
      final departmentIds = <String, String>{};
      for (final hospitalId in hospitals) {
        final detail =
            await widget.apiClient.get('/api/v1/hospitals/$hospitalId');
        for (final item in detail['departments'] as List? ?? const []) {
          if (item is! Map) continue;
          final code = item['code']?.toString() ?? '';
          final id = item['id']?.toString() ?? '';
          if (_consultationTypes.containsKey(code) && id.isNotEmpty) {
            departmentIds.putIfAbsent(code, () => id);
          }
        }
      }
      if (!mounted) return;
      setState(() {
        _encounters = encounters;
        _selectedEncounterId = encounters.isEmpty ? null : encounters.first.id;
        _departmentIds
          ..clear()
          ..addAll(departmentIds);
      });
    } on ClinicianApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = '협진 요청 정보를 불러오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _selectType(String? type) async {
    setState(() {
      _selectedType = type;
      _selectedAssigneeUserId = null;
      _clinicians = const [];
    });
    final departmentId = type == null ? null : _departmentIds[type];
    if (departmentId == null) return;
    setState(() => _loadingClinicians = true);
    try {
      final response = await widget.apiClient.get(
        '/api/v1/departments/$departmentId/clinicians',
      );
      final clinicians = (response['clinicians'] as List? ?? const [])
          .whereType<Map>()
          .map((item) =>
              _ClinicianOption.fromJson(Map<String, dynamic>.from(item)))
          .where((item) => item.userId.isNotEmpty)
          .toList(growable: false);
      if (mounted) setState(() => _clinicians = clinicians);
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } catch (_) {
      if (mounted) {
        const message = '배정 의료진을 불러오지 못했습니다.';
        setState(() => _error = message);
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text(message)));
      }
    } finally {
      if (mounted) setState(() => _loadingClinicians = false);
    }
  }

  bool get _canSubmit =>
      !_submitting &&
      _selectedEncounterId != null &&
      _selectedType != null &&
      _selectedAssigneeUserId != null &&
      _reasonController.text.trim().isNotEmpty;

  Future<void> _submit() async {
    if (!_canSubmit) return;
    setState(() => _submitting = true);
    try {
      final response = await widget.apiClient.post(
        '/api/v1/consultations',
        body: {
          'encounter_id': _selectedEncounterId,
          'consultation_type': _selectedType,
          'assigned_to_id': _selectedAssigneeUserId,
          'priority': _priority,
          'reason': _reasonController.text.trim(),
        },
      );
      final consultationId = response['consultation_id']?.toString() ?? '';
      if (consultationId.isEmpty) {
        throw const ClinicianApiException(
          statusCode: 201,
          message: '생성된 협진 정보를 확인하지 못했습니다.',
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('협진 요청이 전송되었습니다.')));
      Navigator.of(context).pop(consultationId);
    } on ClinicianApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('협진 요청을 전송하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('협진 요청')),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null && _encounters.isEmpty
                ? _CreateErrorState(message: _error!, onRetry: _loadInitialData)
                : SafeArea(
                    child: Column(
                      children: [
                        Expanded(
                          child: ListView(
                            padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
                            children: [
                              RadiologyInfoCard(
                                child: Row(
                                  children: [
                                    const CircleAvatar(
                                      backgroundColor: Color(0xFFEAF2FF),
                                      child: Icon(Icons.person_outline_rounded,
                                          color: radiologyBlue),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(widget.patientName,
                                              style: const TextStyle(
                                                  color: radiologyNavy,
                                                  fontWeight: FontWeight.w800)),
                                          const SizedBox(height: 3),
                                          Text(
                                            [
                                              if (widget.patientNo.isNotEmpty)
                                                widget.patientNo,
                                              if (widget
                                                  .demographics.isNotEmpty)
                                                widget.demographics,
                                            ].join(' · '),
                                            style: const TextStyle(
                                                color: radiologyMuted,
                                                fontSize: 13),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 18),
                              const RadiologySectionTitle(title: '협진 요청 내용'),
                              const SizedBox(height: 10),
                              _FieldCard(
                                label: '협진 대상 진료과',
                                requiredField: true,
                                child: DropdownButtonFormField<String>(
                                  initialValue: _selectedType,
                                  isExpanded: true,
                                  decoration: const InputDecoration(
                                      border: OutlineInputBorder()),
                                  items: _consultationTypes.entries
                                      .where((item) =>
                                          _departmentIds.containsKey(item.key))
                                      .map((item) => DropdownMenuItem(
                                          value: item.key,
                                          child: Text(item.value)))
                                      .toList(),
                                  onChanged: _selectType,
                                ),
                              ),
                              const SizedBox(height: 10),
                              _FieldCard(
                                label: '배정 의료진',
                                requiredField: true,
                                child: _loadingClinicians
                                    ? const Padding(
                                        padding: EdgeInsets.all(12),
                                        child: Center(
                                            child: CircularProgressIndicator()),
                                      )
                                    : DropdownButtonFormField<String>(
                                        initialValue: _selectedAssigneeUserId,
                                        isExpanded: true,
                                        decoration: const InputDecoration(
                                            border: OutlineInputBorder()),
                                        hint: const Text('의료진을 선택해 주세요.'),
                                        items: _clinicians
                                            .map((item) => DropdownMenuItem(
                                                value: item.userId,
                                                child: Text(item.name)))
                                            .toList(),
                                        onChanged: _selectedType == null
                                            ? null
                                            : (value) => setState(() =>
                                                _selectedAssigneeUserId =
                                                    value),
                                      ),
                              ),
                              const SizedBox(height: 10),
                              _FieldCard(
                                label: '우선순위',
                                requiredField: true,
                                child: DropdownButtonFormField<String>(
                                  initialValue: _priority,
                                  isExpanded: true,
                                  decoration: const InputDecoration(
                                      border: OutlineInputBorder()),
                                  items: _priorities.entries
                                      .map((item) => DropdownMenuItem(
                                          value: item.key,
                                          child: Text(item.value)))
                                      .toList(),
                                  onChanged: (value) {
                                    if (value != null) {
                                      setState(() => _priority = value);
                                    }
                                  },
                                ),
                              ),
                              const SizedBox(height: 10),
                              _FieldCard(
                                label: '협진 사유',
                                requiredField: true,
                                child: TextField(
                                  controller: _reasonController,
                                  minLines: 3,
                                  maxLines: 5,
                                  decoration: const InputDecoration(
                                    hintText: '협진 사유를 입력해 주세요.',
                                    border: OutlineInputBorder(),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        SafeArea(
                          top: false,
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                            child: Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton(
                                    onPressed: _submitting
                                        ? null
                                        : () => Navigator.of(context).pop(),
                                    child: const Text('취소'),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  flex: 2,
                                  child: FilledButton(
                                    onPressed: _canSubmit ? _submit : null,
                                    child: Text(
                                        _submitting ? '전송 중…' : '협진 요청 보내기'),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
      );
}

class _FieldCard extends StatelessWidget {
  const _FieldCard({
    required this.label,
    required this.requiredField,
    required this.child,
  });

  final String label;
  final bool requiredField;
  final Widget child;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            RichText(
              text: TextSpan(
                text: label,
                style: const TextStyle(
                    color: radiologyNavy, fontWeight: FontWeight.w800),
                children: requiredField
                    ? const [
                        TextSpan(
                            text: ' *', style: TextStyle(color: radiologyBlue)),
                      ]
                    : const [],
              ),
            ),
            const SizedBox(height: 8),
            child,
          ],
        ),
      );
}

class _CreateErrorState extends StatelessWidget {
  const _CreateErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 8),
              TextButton(onPressed: onRetry, child: const Text('다시 시도')),
            ],
          ),
        ),
      );
}

class _EncounterOption {
  const _EncounterOption({required this.id, required this.status});

  factory _EncounterOption.fromJson(Map<String, dynamic> json) =>
      _EncounterOption(
        id: json['id']?.toString() ?? json['encounter_id']?.toString() ?? '',
        status: json['status']?.toString() ?? '',
      );

  final String id;
  final String status;

  bool get isAvailable =>
      id.isNotEmpty && (status == 'REGISTERED' || status == 'IN_PROGRESS');
}

class _ClinicianOption {
  const _ClinicianOption({required this.userId, required this.name});

  factory _ClinicianOption.fromJson(Map<String, dynamic> json) =>
      _ClinicianOption(
        userId: json['user_id']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
      );

  final String userId;
  final String name;
}
