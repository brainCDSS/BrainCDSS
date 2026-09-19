import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class _PatientDetail {
  const _PatientDetail({
    required this.name,
    required this.patientNo,
    required this.birthDate,
    required this.estimatedAge,
    required this.sex,
    required this.phone,
    required this.status,
  });

  factory _PatientDetail.fromJson(Map<String, dynamic> json) => _PatientDetail(
        name: json['name']?.toString() ?? '',
        patientNo: json['patient_no']?.toString() ?? '',
        birthDate: json['birth_date']?.toString(),
        estimatedAge: json['estimated_age'] as int?,
        sex: json['sex']?.toString(),
        phone: json['phone']?.toString(),
        status: json['status']?.toString() ?? '',
      );

  final String name;
  final String patientNo;
  final String? birthDate;
  final int? estimatedAge;
  final String? sex;
  final String? phone;
  final String status;
}

class RadiologyPatientDetailPage extends StatefulWidget {
  const RadiologyPatientDetailPage({
    super.key,
    required this.apiClient,
    required this.patientId,
  });

  final ClinicianApiClient apiClient;
  final String patientId;

  @override
  State<RadiologyPatientDetailPage> createState() =>
      _RadiologyPatientDetailPageState();
}

class _RadiologyPatientDetailPageState
    extends State<RadiologyPatientDetailPage> {
  _PatientDetail? _patient;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final response = await widget.apiClient.get(
        '/api/v1/patients/${widget.patientId}',
      );
      if (mounted) {
        setState(() => _patient = _PatientDetail.fromJson(response));
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '환자 정보를 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('환자 상세')),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(_errorMessage!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          TextButton(onPressed: _load, child: const Text('다시 시도')),
                        ],
                      ),
                    ),
                  )
                : _PatientDetailBody(patient: _patient!),
      );
}

class _PatientDetailBody extends StatelessWidget {
  const _PatientDetailBody({required this.patient});

  final _PatientDetail patient;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
          RadiologyInfoCard(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: const Color(0xFFEAF2FF),
                  child: Text(
                    patient.name.isEmpty ? '?' : patient.name.substring(0, 1),
                    style: const TextStyle(
                      color: radiologyBlue,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        patient.name.isEmpty ? '이름 정보 없음' : patient.name,
                        style: const TextStyle(
                          color: radiologyNavy,
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        patient.patientNo.isEmpty ? '환자번호 정보 없음' : patient.patientNo,
                        style: const TextStyle(color: radiologyMuted),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const RadiologySectionTitle(title: '기본 정보'),
          const SizedBox(height: 10),
          RadiologyInfoCard(
            child: Column(
              children: [
                _InfoRow(label: '생년월일', value: patient.birthDate),
                _InfoRow(
                  label: '나이',
                  value: patient.estimatedAge == null ? null : '${patient.estimatedAge}세',
                ),
                _InfoRow(label: '성별', value: patient.sex),
                _InfoRow(label: '연락처', value: patient.phone),
                _InfoRow(label: '환자 상태', value: patient.status),
              ],
            ),
          ),
        ],
      );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(
          children: [
            SizedBox(
              width: 88,
              child: Text(
                label,
                style: const TextStyle(color: radiologyMuted, fontSize: 13),
              ),
            ),
            Expanded(
              child: Text(
                value == null || value!.isEmpty ? '정보 없음' : value!,
                style: const TextStyle(
                  color: radiologyNavy,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
}
