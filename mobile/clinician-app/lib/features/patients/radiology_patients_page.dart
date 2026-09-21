import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';
import '../radiology/widgets/radiology_ui.dart';
import 'radiology_patient_detail_page.dart';

class RadiologyPatient {
  const RadiologyPatient({
    required this.id,
    required this.patientNo,
    required this.name,
    required this.birthDate,
    required this.estimatedAge,
    required this.sex,
    required this.phone,
    required this.status,
  });

  factory RadiologyPatient.fromJson(Map<String, dynamic> json) =>
      RadiologyPatient(
        id: json['id']?.toString() ?? '',
        patientNo: json['patient_no']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
        birthDate: json['birth_date']?.toString(),
        estimatedAge: json['estimated_age'] as int?,
        sex: json['sex']?.toString(),
        phone: json['phone']?.toString(),
        status: json['status']?.toString() ?? '',
      );

  final String id;
  final String patientNo;
  final String name;
  final String? birthDate;
  final int? estimatedAge;
  final String? sex;
  final String? phone;
  final String status;
}

class RadiologyPatientsApi {
  RadiologyPatientsApi(this._client);

  final ClinicianApiClient _client;

  Future<List<RadiologyPatient>> list({String? search}) async {
    final response = await _client.get(
      '/api/v1/patients',
      query: {
        if (search != null && search.isNotEmpty) 'search': search,
      },
    );
    return (response['results'] as List? ?? const [])
        .whereType<Map>()
        .map((item) =>
            RadiologyPatient.fromJson(Map<String, dynamic>.from(item)))
        .toList(growable: false);
  }
}

class RadiologyPatientsPage extends StatefulWidget {
  const RadiologyPatientsPage({
    super.key,
    required this.apiClient,
    this.roleCode = 'RADIOLOGY',
  });

  final ClinicianApiClient apiClient;
  final String roleCode;

  @override
  State<RadiologyPatientsPage> createState() => _RadiologyPatientsPageState();
}

class _RadiologyPatientsPageState extends State<RadiologyPatientsPage> {
  Timer? _searchDebounce;
  List<RadiologyPatient> _patients = const [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadPatients();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    super.dispose();
  }

  Future<void> _loadPatients([String? search]) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final patients = await RadiologyPatientsApi(widget.apiClient).list(
        search: search,
      );
      if (mounted) {
        setState(() => _patients = patients);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '환자 목록을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _onSearchChanged(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(
      const Duration(milliseconds: 350),
      () => _loadPatients(value.trim()),
    );
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '환자'),
          const SizedBox(height: 14),
          TextField(
            onChanged: _onSearchChanged,
            decoration: InputDecoration(
              hintText: '환자명 또는 환자번호 검색',
              prefixIcon: const Icon(Icons.search_rounded),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: radiologyBorder),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: radiologyBorder),
              ),
            ),
          ),
          const SizedBox(height: 18),
          if (_isLoading)
            const Center(
                child: Padding(
              padding: EdgeInsets.all(32),
              child: CircularProgressIndicator(),
            ))
          else if (_errorMessage != null)
            _LoadError(message: _errorMessage!, onRetry: _loadPatients)
          else if (_patients.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.person_search_outlined,
              message: '표시할 환자가 없습니다.',
            )
          else
            ..._patients.map(
              (patient) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _PatientCard(
                  patient: patient,
                  onTap: () {
                    if (widget.roleCode == 'RADIOLOGY') {
                      RadiologyNavigation.openPatient(patient.id);
                      return;
                    }

                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => RadiologyPatientDetailPage(
                          apiClient: widget.apiClient,
                          patientId: patient.id,
                          roleCode: widget.roleCode,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
        ],
      );
}

class _PatientCard extends StatelessWidget {
  const _PatientCard({required this.patient, required this.onTap});

  final RadiologyPatient patient;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: RadiologyInfoCard(
          child: Row(
            children: [
              CircleAvatar(
                radius: 23,
                backgroundColor: const Color(0xFFEAF2FF),
                child: Text(
                  patient.name.isEmpty ? '?' : patient.name.substring(0, 1),
                  style: const TextStyle(
                    color: radiologyBlue,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      patient.name.isEmpty ? '이름 정보 없음' : patient.name,
                      style: const TextStyle(
                        color: radiologyNavy,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      _demographics(patient),
                      style:
                          const TextStyle(color: radiologyMuted, fontSize: 12),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      patient.status.isEmpty ? '상태 정보 없음' : patient.status,
                      style: const TextStyle(
                        color: radiologyBlue,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: radiologyMuted),
            ],
          ),
        ),
      );

  String _demographics(RadiologyPatient patient) {
    final values = <String>[
      if (patient.sex != null && patient.sex!.isNotEmpty) patient.sex!,
      if (patient.estimatedAge != null) '${patient.estimatedAge}세',
      if (patient.patientNo.isNotEmpty) patient.patientNo,
    ];
    return values.isEmpty ? '기본 정보 없음' : values.join(' · ');
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => RadiologyInfoCard(
        child: Column(
          children: [
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 10),
            TextButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ),
      );
}
