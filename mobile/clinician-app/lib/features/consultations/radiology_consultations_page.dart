import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_navigation_drawer.dart';
import '../radiology/widgets/radiology_ui.dart';

class RadiologyConsultation {
  const RadiologyConsultation({
    required this.id,
    required this.type,
    required this.priority,
    required this.status,
    required this.patientName,
    required this.requesterName,
    required this.requesterDepartment,
    required this.requestedAt,
  });

  factory RadiologyConsultation.fromJson(Map<String, dynamic> json) {
    final patient = json['patient_summary'] as Map?;
    final requester = json['requested_by'] as Map?;
    return RadiologyConsultation(
      id: json['consultation_id']?.toString() ?? '',
      type: json['type']?.toString() ?? '',
      priority: json['priority']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      patientName: patient?['name']?.toString() ?? '',
      requesterName: requester?['name']?.toString() ?? '',
      requesterDepartment: requester?['department']?.toString() ?? '',
      requestedAt: json['requested_at']?.toString(),
    );
  }

  final String id;
  final String type;
  final String priority;
  final String status;
  final String patientName;
  final String requesterName;
  final String requesterDepartment;
  final String? requestedAt;
}

class RadiologyConsultationsApi {
  RadiologyConsultationsApi(this._client);

  final ClinicianApiClient _client;

  Future<List<RadiologyConsultation>> list({
    String? status,
    String? viewerRelation = 'ASSIGNED_TO',
  }) async {
    final response = await _client.get(
      '/api/v1/consultations',
      query: {
        if (status != null) 'status': status,
        if (viewerRelation != null) 'viewer_relation': viewerRelation,
      },
    );
    return (response['results'] as List? ?? const [])
        .whereType<Map>()
        .map(
          (item) => RadiologyConsultation.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList(growable: false);
  }
}

enum _ConsultationFilter { all, requested, inProgress, completed }

class RadiologyConsultationsPage extends StatefulWidget {
  const RadiologyConsultationsPage({
    super.key,
    required this.apiClient,
    this.viewerRelation = 'ASSIGNED_TO',
  });

  final ClinicianApiClient apiClient;
  final String? viewerRelation;

  @override
  State<RadiologyConsultationsPage> createState() =>
      _RadiologyConsultationsPageState();
}

class _RadiologyConsultationsPageState
    extends State<RadiologyConsultationsPage> {
  _ConsultationFilter _filter = _ConsultationFilter.all;
  List<RadiologyConsultation> _consultations = const [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadConsultations();
  }

  Future<void> _loadConsultations() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final consultations = await RadiologyConsultationsApi(widget.apiClient)
          .list(
            status: _apiStatusFor(_filter),
            viewerRelation: widget.viewerRelation,
          );
      if (mounted) {
        setState(() => _consultations = consultations);
      }
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = '협진 목록을 불러오지 못했습니다.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  String? _apiStatusFor(_ConsultationFilter filter) => switch (filter) {
        _ConsultationFilter.requested => 'REQUESTED',
        _ConsultationFilter.inProgress => 'IN_PROGRESS',
        _ => null,
      };

  List<RadiologyConsultation> get _visibleConsultations {
    if (_filter != _ConsultationFilter.completed) {
      return _consultations;
    }
    return _consultations
        .where((item) => item.status == 'RESPONDED' || item.status == 'CLOSED')
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: [
          const RadiologySectionTitle(title: '협진'),
          const SizedBox(height: 14),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _ConsultationFilter.values
                  .map(
                    (filter) => Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(_filterLabel(filter)),
                        selected: _filter == filter,
                        onSelected: (_) {
                          setState(() => _filter = filter);
                          _loadConsultations();
                        },
                      ),
                    ),
                  )
                  .toList(),
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
            _ConsultationLoadError(
              message: _errorMessage!,
              onRetry: _loadConsultations,
            )
          else if (_visibleConsultations.isEmpty)
            const RadiologyEmptyState(
              icon: Icons.forum_outlined,
              message: '해당 상태의 협진이 없습니다.',
            )
          else
            ..._visibleConsultations.map(
              (consultation) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _ConsultationCard(
                  consultation: consultation,
                  onTap: () =>
                      RadiologyNavigation.openConsultation(consultation.id),
                ),
              ),
            ),
        ],
      );
}

class _ConsultationCard extends StatelessWidget {
  const _ConsultationCard({required this.consultation, required this.onTap});

  final RadiologyConsultation consultation;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: RadiologyInfoCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      consultation.patientName.isEmpty
                          ? '환자 정보 없음'
                          : consultation.patientName,
                      style: const TextStyle(
                        color: radiologyNavy,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  RadiologyStatusChip(
                    label: _statusLabel(consultation.status),
                    color: _statusColor(consultation.status),
                  ),
                ],
              ),
              const SizedBox(height: 11),
              _DetailLine(
                label: '요청 진료과',
                value: consultation.requesterDepartment,
              ),
              const SizedBox(height: 6),
              _DetailLine(label: '요청자', value: consultation.requesterName),
              const SizedBox(height: 6),
              _DetailLine(
                  label: '요청 시간',
                  value: _formatDateTime(consultation.requestedAt)),
            ],
          ),
        ),
      );
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          SizedBox(
            width: 76,
            child: Text(
              label,
              style: const TextStyle(color: radiologyMuted, fontSize: 12),
            ),
          ),
          Expanded(
            child: Text(
              value.isEmpty ? '정보 없음' : value,
              style: const TextStyle(
                color: radiologyNavy,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      );
}

class _ConsultationLoadError extends StatelessWidget {
  const _ConsultationLoadError({required this.message, required this.onRetry});

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

String _filterLabel(_ConsultationFilter filter) => switch (filter) {
      _ConsultationFilter.all => '전체',
      _ConsultationFilter.requested => '요청',
      _ConsultationFilter.inProgress => '진행중',
      _ConsultationFilter.completed => '완료',
    };

String _statusLabel(String status) => switch (status) {
      'REQUESTED' => '요청',
      'ACCEPTED' => '수락',
      'IN_PROGRESS' => '진행중',
      'RESPONDED' => '완료',
      'CLOSED' => '완료',
      'REJECTED' => '거절',
      'CANCELLED' => '취소',
      _ => status.isEmpty ? '정보 없음' : status,
    };

Color _statusColor(String status) => switch (status) {
      'REQUESTED' => const Color(0xFF2563B8),
      'ACCEPTED' || 'IN_PROGRESS' => const Color(0xFFB46912),
      'REJECTED' || 'CANCELLED' => const Color(0xFFCC4D5B),
      _ => const Color(0xFF208563),
    };

String _formatDateTime(String? value) {
  if (value == null || value.isEmpty) {
    return '정보 없음';
  }
  final dateTime = DateTime.tryParse(value)?.toLocal();
  if (dateTime == null) {
    return value;
  }
  return '${dateTime.year}.${dateTime.month.toString().padLeft(2, '0')}.'
      '${dateTime.day.toString().padLeft(2, '0')} '
      '${dateTime.hour.toString().padLeft(2, '0')}:'
      '${dateTime.minute.toString().padLeft(2, '0')}';
}
