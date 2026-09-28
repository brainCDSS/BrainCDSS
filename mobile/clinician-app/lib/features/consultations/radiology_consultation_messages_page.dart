import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class ConsultationMessage {
  const ConsultationMessage({
    required this.messageId,
    required this.consultationId,
    required this.senderName,
    required this.senderDepartment,
    required this.content,
    required this.createdAt,
    required this.isMine,
  });

  factory ConsultationMessage.fromJson(Map<String, dynamic> json) {
    final sender = json['sender'] as Map?;
    return ConsultationMessage(
      messageId: json['message_id']?.toString() ?? '',
      consultationId: json['consultation_id']?.toString() ?? '',
      senderName: sender?['name']?.toString() ?? '',
      senderDepartment: sender?['department']?.toString(),
      content: json['content']?.toString() ?? '',
      createdAt: json['created_at']?.toString(),
      isMine: json['is_mine'] == true,
    );
  }

  final String messageId;
  final String consultationId;
  final String senderName;
  final String? senderDepartment;
  final String content;
  final String? createdAt;
  final bool isMine;
}

class RadiologyConsultationMessagesPage extends StatefulWidget {
  const RadiologyConsultationMessagesPage({
    super.key,
    required this.apiClient,
    required this.consultationId,
    required this.patientName,
    required this.patientNo,
    required this.consultationStatus,
  });

  final ClinicianApiClient apiClient;
  final String consultationId;
  final String patientName;
  final String patientNo;
  final String consultationStatus;

  @override
  State<RadiologyConsultationMessagesPage> createState() =>
      _RadiologyConsultationMessagesPageState();
}

class _RadiologyConsultationMessagesPageState
    extends State<RadiologyConsultationMessagesPage> {
  static const _pollingInterval = Duration(seconds: 2);

  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final List<ConsultationMessage> _messages = [];

  Timer? _pollingTimer;
  bool _isLoading = true;
  bool _isRefreshing = false;
  bool _isSending = false;
  String? _errorMessage;

  bool get _canSend => const {'REQUESTED', 'ACCEPTED', 'IN_PROGRESS'}
      .contains(widget.consultationStatus);

  @override
  void initState() {
    super.initState();
    _loadMessages();
    _pollingTimer = Timer.periodic(_pollingInterval, (_) {
      _loadMessages(incremental: true);
    });
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadMessages({bool incremental = false}) async {
    if (_isRefreshing || widget.consultationId.isEmpty) {
      return;
    }
    _isRefreshing = true;
    if (!incremental && mounted) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final response = await widget.apiClient.get(
        '/api/v1/consultations/${widget.consultationId}/messages',
        query: incremental && _messages.isNotEmpty
            ? {'after': _messages.last.messageId}
            : null,
      );
      final received = (response['results'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (item) => ConsultationMessage.fromJson(
              Map<String, dynamic>.from(item),
            ),
          )
          .where((item) => item.messageId.isNotEmpty)
          .toList(growable: false);
      final knownIds = _messages.map((item) => item.messageId).toSet();
      final added = received
          .where((item) => knownIds.add(item.messageId))
          .toList(growable: false);

      if (mounted) {
        setState(() {
          _messages.addAll(added);
          _messages.sort((left, right) => _dateForSort(left.createdAt)
              .compareTo(_dateForSort(right.createdAt)));
          _errorMessage = null;
        });
        if (!incremental || added.isNotEmpty) {
          _scrollToLatest();
        }
      }
    } on ClinicianApiException catch (error) {
      if (mounted && !incremental) {
        setState(() => _errorMessage = error.message);
      }
    } catch (_) {
      if (mounted && !incremental) {
        setState(() => _errorMessage = '협진 메시지를 불러오지 못했습니다.');
      }
    } finally {
      _isRefreshing = false;
      if (mounted && !incremental) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _sendMessage() async {
    final content = _inputController.text.trim();
    if (!_canSend || _isSending || content.isEmpty) {
      return;
    }
    setState(() => _isSending = true);
    try {
      final response = await widget.apiClient.post(
        '/api/v1/consultations/${widget.consultationId}/messages',
        body: {'content': content},
      );
      final message = ConsultationMessage.fromJson(response);
      if (!mounted) {
        return;
      }
      setState(() {
        if (message.messageId.isNotEmpty &&
            !_messages.any((item) => item.messageId == message.messageId)) {
          _messages.add(message);
        }
      });
      _inputController.clear();
      _scrollToLatest();
    } on ClinicianApiException catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('메시지를 전송하지 못했습니다.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('메시지를 전송하지 못했습니다.')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }
  }

  void _scrollToLatest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) => Column(
        children: [
          _ConversationHeader(
            patientName: widget.patientName,
            patientNo: widget.patientNo,
          ),
          Expanded(child: _buildMessageArea()),
          _MessageComposer(
            controller: _inputController,
            enabled: _canSend && !_isSending,
            isSending: _isSending,
            onSend: _sendMessage,
            onChanged: () => setState(() {}),
            helperText: _canSend
                ? null
                : '종료된 협진에서는 메시지를 보낼 수 없습니다.',
          ),
        ],
      );

  Widget _buildMessageArea() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              TextButton(
                onPressed: _loadMessages,
                child: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }
    if (_messages.isEmpty) {
      return const _EmptyMessageState();
    }
    return ListView.separated(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 16),
      itemCount: _messages.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, index) => _MessageBubble(message: _messages[index]),
    );
  }
}

class _ConversationHeader extends StatelessWidget {
  const _ConversationHeader({required this.patientName, required this.patientNo});

  final String patientName;
  final String patientNo;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 11),
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(bottom: BorderSide(color: radiologyBorder)),
        ),
        child: Text(
          [
            if (patientName.trim().isNotEmpty) patientName.trim(),
            if (patientNo.trim().isNotEmpty) '(${patientNo.trim()})',
          ].join(' '),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: radiologyMuted,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ConsultationMessage message;

  @override
  Widget build(BuildContext context) {
    final alignment = message.isMine
        ? CrossAxisAlignment.end
        : CrossAxisAlignment.start;
    final maximumBubbleWidth = MediaQuery.sizeOf(context).width * 0.76;
    return Column(
      crossAxisAlignment: alignment,
      children: [
        if (!message.isMine && message.senderName.trim().isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 4),
            child: Text(
              [
                message.senderName.trim(),
                if (message.senderDepartment?.trim().isNotEmpty ?? false)
                  message.senderDepartment!.trim(),
              ].join(' · '),
              style: const TextStyle(
                color: radiologyMuted,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        Row(
          mainAxisAlignment: message.isMine
              ? MainAxisAlignment.end
              : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (!message.isMine) ...[
              _SenderAvatar(name: message.senderName),
              const SizedBox(width: 8),
            ],
            Flexible(
              child: Container(
                constraints: BoxConstraints(maxWidth: maximumBubbleWidth),
                padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                decoration: BoxDecoration(
                  color: message.isMine ? const Color(0xFFDCEBFF) : Colors.white,
                  border: Border.all(
                    color: message.isMine
                        ? const Color(0xFFC7DDFB)
                        : radiologyBorder,
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Text(
                  message.content,
                  style: const TextStyle(
                    color: radiologyNavy,
                    fontSize: 14,
                    height: 1.42,
                  ),
                ),
              ),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.only(top: 4, left: 4, right: 4),
          child: Text(
            _formatTime(message.createdAt),
            style: const TextStyle(color: radiologyMuted, fontSize: 10),
          ),
        ),
      ],
    );
  }
}

class _SenderAvatar extends StatelessWidget {
  const _SenderAvatar({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) => Container(
        width: 32,
        height: 32,
        alignment: Alignment.center,
        decoration: const BoxDecoration(
          color: Color(0xFFEAF2FF),
          shape: BoxShape.circle,
        ),
        child: Text(
          name.trim().isEmpty ? '?' : name.trim().substring(0, 1),
          style: const TextStyle(
            color: radiologyBlue,
            fontSize: 13,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _EmptyMessageState extends StatelessWidget {
  const _EmptyMessageState();

  @override
  Widget build(BuildContext context) => const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.forum_outlined, size: 34, color: radiologyMuted),
              SizedBox(height: 12),
              Text(
                '아직 협진 메시지가 없습니다.',
                style: TextStyle(
                  color: radiologyNavy,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(height: 5),
              Text(
                '필요한 내용을 의료진에게 전달해보세요.',
                textAlign: TextAlign.center,
                style: TextStyle(color: radiologyMuted, fontSize: 13),
              ),
            ],
          ),
        ),
      );
}

class _MessageComposer extends StatelessWidget {
  const _MessageComposer({
    required this.controller,
    required this.enabled,
    required this.isSending,
    required this.onSend,
    required this.onChanged,
    required this.helperText,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool isSending;
  final VoidCallback onSend;
  final VoidCallback onChanged;
  final String? helperText;

  @override
  Widget build(BuildContext context) => SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(top: BorderSide(color: radiologyBorder)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (helperText != null) ...[
                Text(
                  helperText!,
                  style: const TextStyle(color: radiologyMuted, fontSize: 11),
                ),
                const SizedBox(height: 7),
              ],
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller,
                      enabled: enabled,
                      onChanged: (_) => onChanged(),
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.newline,
                      decoration: InputDecoration(
                        hintText: '메시지를 입력해 주세요.',
                        hintStyle: const TextStyle(color: radiologyMuted, fontSize: 13),
                        isDense: true,
                        filled: true,
                        fillColor: const Color(0xFFF7F9FC),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 11,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(22),
                          borderSide: const BorderSide(color: radiologyBorder),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(22),
                          borderSide: const BorderSide(color: radiologyBorder),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: enabled && controller.text.trim().isNotEmpty
                        ? onSend
                        : null,
                    icon: isSending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.send_rounded),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
}

DateTime _dateForSort(String? value) =>
    DateTime.tryParse(value ?? '')?.toLocal() ?? DateTime.fromMillisecondsSinceEpoch(0);

String _formatTime(String? value) {
  final dateTime = DateTime.tryParse(value ?? '')?.toLocal();
  if (dateTime == null) {
    return '';
  }
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(dateTime.hour)}:${two(dateTime.minute)}';
}
