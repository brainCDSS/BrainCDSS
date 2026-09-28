import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';

import '../../core/api/clinician_api_client.dart';
import '../radiology/widgets/radiology_ui.dart';

class ClinicianAiAssistantPage extends StatefulWidget {
  const ClinicianAiAssistantPage({super.key, required this.apiClient});

  final ClinicianApiClient apiClient;

  @override
  State<ClinicianAiAssistantPage> createState() =>
      _ClinicianAiAssistantPageState();
}

class _ClinicianAiAssistantPageState extends State<ClinicianAiAssistantPage> {
  static const _quickPrompts = [
    '오늘 예약 환자 현황 알려줘',
    '현재 응급 환자 현황 알려줘',
    '대기 중 협진 현황 알려줘',
  ];
  static const _quickPromptIcons = [
    Icons.calendar_today_outlined,
    Icons.emergency_outlined,
    Icons.forum_outlined,
  ];

  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _sending = false;
  String? _conversationId;

  bool get _canSend => !_sending && _input.text.trim().isNotEmpty;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _sendFromInput() async {
    final message = _input.text.trim();
    if (message.isEmpty || _sending) return;
    _input.clear();
    await _send(message, addUserMessage: true);
  }

  Future<void> _sendQuickPrompt(String prompt) async {
    if (!_sending) await _send(prompt, addUserMessage: true);
  }

  Future<void> _retry(String message, int index) async {
    if (_sending) return;
    setState(() => _messages.removeAt(index));
    await _send(message, addUserMessage: false);
  }

  Future<void> _send(String message, {required bool addUserMessage}) async {
    if (_sending) return;
    setState(() {
      _sending = true;
      if (addUserMessage)
        _messages.add(_ChatMessage(text: message, isUser: true));
    });
    _scrollToBottom();

    try {
      final response = await widget.apiClient.post(
        '/api/v1/assistant/messages',
        body: {
          'message': message,
          // Patient context is resolved only by the server from natural language.
          'context': {'scope': 'TODAY'},
          if (_conversationId != null) 'conversation_id': _conversationId,
        },
      );
      final answer = response['answer']?.toString().trim();
      final conversationId = response['conversation_id']?.toString().trim();
      if (answer == null || answer.isEmpty) {
        throw const ClinicianApiException(
            statusCode: 502, message: 'AI 응답을 확인할 수 없습니다.');
      }
      if (conversationId != null && conversationId.isNotEmpty) {
        _conversationId = conversationId;
      }
      if (mounted)
        setState(
            () => _messages.add(_ChatMessage(text: answer, isUser: false)));
    } on ClinicianApiException catch (error) {
      if (mounted) {
        setState(() {
          _messages.add(_ChatMessage(
            text: _errorMessage(error),
            isUser: false,
            isError: true,
            retryMessage: message,
          ));
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _messages.add(const _ChatMessage(
            text: 'AI 어시스턴트 연결 중 오류가 발생했습니다.',
            isUser: false,
            isError: true,
          ));
        });
      }
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollToBottom();
    }
  }

  String _errorMessage(ClinicianApiException error) =>
      switch (error.statusCode) {
        400 => '환자 이름 또는 등록번호를 포함해 다시 질문해 주세요.',
        401 => '로그인이 만료되었거나 인증이 필요합니다. 다시 로그인해 주세요.',
        403 => '해당 환자 정보에 접근할 권한이 없습니다.',
        503 => 'AI 어시스턴트 서비스를 일시적으로 사용할 수 없습니다.',
        _ => error.message,
      };

  void _newConversation() {
    if (!_sending)
      setState(() {
        _conversationId = null;
        _messages.clear();
      });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        top: false,
        child: Column(
          children: [
            _conversationHeader(),
            Expanded(child: _messages.isEmpty ? _emptyState() : _messageList()),
            if (_sending) const _LoadingIndicator(),
            _inputBar(context),
          ],
        ),
      );

  Widget _conversationHeader() => Container(
        color: Colors.white,
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
        child: Row(
          children: [
            const Expanded(
              child: Text('BrainOn AI',
                  style: TextStyle(
                      color: radiologyNavy, fontWeight: FontWeight.w800)),
            ),
            TextButton.icon(
              onPressed: _sending ? null : _newConversation,
              icon: const Icon(Icons.add_comment_outlined, size: 18),
              label: const Text('새 대화'),
            ),
          ],
        ),
      );

  Widget _messageList() => ListView.builder(
        controller: _scroll,
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        itemCount: _messages.length,
        itemBuilder: (context, index) {
          final message = _messages[index];
          return _Bubble(
            message: message,
            onRetry: message.retryMessage == null
                ? null
                : () => _retry(message.retryMessage!, index),
          );
        },
      );

  Widget _emptyState() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: const Color(0xFFC8D8EC)),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                      color: const Color(0xFFEAF2FF),
                      borderRadius: BorderRadius.circular(14)),
                  child: Padding(
                    padding: const EdgeInsets.all(3),
                    child: Image.asset(
                      'asset/images/chat-avatar.png',
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('무엇을 도와드릴까요?',
                          style: TextStyle(
                              color: radiologyNavy,
                              fontWeight: FontWeight.w800)),
                      SizedBox(height: 5),
                      Text(
                        '오늘의 진료 및 협진 현황을 확인하거나 궁금한 내용을 질문해 보세요.',
                        style: TextStyle(
                            color: radiologyMuted, fontSize: 13, height: 1.4),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const Text('빠른 질문',
              style: TextStyle(
                  color: radiologyBlue,
                  fontSize: 13,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 10),
          ...List.generate(
            _quickPrompts.length,
            (index) => Padding(
              padding: EdgeInsets.only(
                bottom: index == _quickPrompts.length - 1 ? 0 : 10,
              ),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: _sending
                      ? null
                      : () => _sendQuickPrompt(_quickPrompts[index]),
                  style: OutlinedButton.styleFrom(
                    alignment: Alignment.centerLeft,
                    minimumSize: const Size.fromHeight(54),
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFFC8D8EC)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _quickPromptIcons[index],
                        color: radiologyBlue,
                        size: 18,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _quickPrompts[index],
                          textAlign: TextAlign.left,
                          style: const TextStyle(
                            color: radiologyNavy,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            height: 1.4,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Icon(
                        Icons.chevron_right_rounded,
                        color: radiologyMuted,
                        size: 20,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      );

  Widget _inputBar(BuildContext context) => AnimatedPadding(
        duration: const Duration(milliseconds: 150),
        padding:
            EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
          decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: radiologyBorder))),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: TextField(
                  controller: _input,
                  onChanged: (_) => setState(() {}),
                  enabled: !_sending,
                  minLines: 1,
                  maxLines: 4,
                  decoration: InputDecoration(
                    hintText: 'AI 도우미에게 질문하세요',
                    filled: true,
                    fillColor: const Color(0xFFF6F7FB),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(18),
                        borderSide: BorderSide.none),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                  onPressed: _canSend ? _sendFromInput : null,
                  tooltip: '전송',
                  icon: const Icon(Icons.send_rounded)),
            ],
          ),
        ),
      );
}

class _LoadingIndicator extends StatelessWidget {
  const _LoadingIndicator();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.only(left: 20, right: 20, bottom: 8),
        child: Row(children: [
          SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 8),
          Text('AI가 답변을 준비하고 있습니다.',
              style: TextStyle(color: radiologyMuted, fontSize: 12)),
        ]),
      );
}

class _ChatMessage {
  const _ChatMessage(
      {required this.text,
      required this.isUser,
      this.isError = false,
      this.retryMessage});

  final String text;
  final bool isUser;
  final bool isError;
  final String? retryMessage;
}

String _safeAiMarkdown(String markdown) =>
    markdown.replaceAll(RegExp(r'</?[a-zA-Z][^>]*>'), '');

MarkdownStyleSheet _aiMarkdownStyle(BuildContext context) =>
    MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
      p: const TextStyle(
        color: radiologyNavy,
        fontSize: 14,
        height: 1.55,
      ),
      h1: const TextStyle(
        color: radiologyNavy,
        fontSize: 18,
        fontWeight: FontWeight.w800,
        height: 1.35,
      ),
      h2: const TextStyle(
        color: radiologyNavy,
        fontSize: 16,
        fontWeight: FontWeight.w800,
        height: 1.4,
      ),
      h3: const TextStyle(
        color: radiologyBlue,
        fontSize: 14,
        fontWeight: FontWeight.w800,
        height: 1.45,
      ),
      strong: const TextStyle(
        color: radiologyNavy,
        fontWeight: FontWeight.w800,
      ),
      listBullet: const TextStyle(color: radiologyBlue, fontSize: 14),
      blockSpacing: 12,
      listIndent: 24,
    );

class _Bubble extends StatefulWidget {
  const _Bubble({required this.message, this.onRetry});

  final _ChatMessage message;
  final VoidCallback? onRetry;

  @override
  State<_Bubble> createState() => _BubbleState();
}

class _BubbleState extends State<_Bubble> {
  static const _collapsedAnswerHeight = 240.0;
  static const _expandableAnswerLength = 600;

  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final message = widget.message;
    final isAiAnswer = !message.isUser && !message.isError;
    final isExpandable =
        isAiAnswer && message.text.length > _expandableAnswerLength;
    final markdown = MarkdownBody(
      data: _safeAiMarkdown(message.text),
      selectable: true,
      softLineBreak: true,
      styleSheet: _aiMarkdownStyle(context),
      imageBuilder: (uri, title, alt) => const SizedBox.shrink(),
      onTapLink: (text, href, title) {},
    );
    final bubble = ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 340),
      child: Container(
        padding: message.isUser
            ? const EdgeInsets.symmetric(horizontal: 16, vertical: 14)
            : const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: message.isUser
              ? radiologyBlue
              : message.isError
                  ? const Color(0xFFFFF1F3)
                  : Colors.white,
          border:
              isAiAnswer ? Border.all(color: const Color(0xFFC8D8EC)) : null,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (message.isUser || message.isError)
              Text(
                message.text,
                style: TextStyle(
                  color:
                      message.isUser ? Colors.white : const Color(0xFFB34B58),
                  fontSize: 14,
                  height: 1.55,
                ),
              )
            else
              AnimatedSize(
                duration: const Duration(milliseconds: 180),
                alignment: Alignment.topCenter,
                child: isExpandable && !_isExpanded
                    ? SizedBox(
                        height: _collapsedAnswerHeight,
                        child: ClipRect(
                          child: SingleChildScrollView(
                            physics: const NeverScrollableScrollPhysics(),
                            child: markdown,
                          ),
                        ),
                      )
                    : markdown,
              ),
            if (isExpandable) ...[
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: () => setState(() => _isExpanded = !_isExpanded),
                icon: Icon(
                  _isExpanded
                      ? Icons.expand_less_rounded
                      : Icons.expand_more_rounded,
                  size: 18,
                ),
                label: Text(_isExpanded ? '접기' : '전체 답변 보기'),
              ),
            ],
            if (widget.onRetry != null) ...[
              const SizedBox(height: 6),
              TextButton(
                onPressed: widget.onRetry,
                child: const Text('재시도'),
              ),
            ],
          ],
        ),
      ),
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Align(
        alignment:
            message.isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: isAiAnswer
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: const Color(0xFFE2EDFF),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(2),
                      child: Image.asset(
                        'asset/images/chat-avatar.png',
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: bubble,
                    ),
                  ),
                ],
              )
            : bubble,
      ),
    );
  }
}
