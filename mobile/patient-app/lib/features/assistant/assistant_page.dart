import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';

import '../../core/api/api_client.dart';

class AssistantPage extends StatefulWidget {
  const AssistantPage({
    super.key,
    required this.apiClient,
  });

  final ApiClient apiClient;

  @override
  State<AssistantPage> createState() => _AssistantPageState();
}

class _AssistantPageState extends State<AssistantPage> {
  final TextEditingController _messageController =
      TextEditingController();

  final ScrollController _scrollController =
      ScrollController();

  final List<_AssistantChatMessage> _messages = [];

  bool _sending = false;
  String? _conversationId;

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  bool get _canSend =>
      !_sending &&
      _messageController.text.trim().isNotEmpty;

  Future<void> _sendMessage() async {
    final message =
        _messageController.text.trim();

    if (message.isEmpty || _sending) {
      return;
    }

    setState(() {
      _sending = true;

      _messages.add(
        _AssistantChatMessage(
          text: message,
          isUser: true,
        ),
      );

      _messageController.clear();
    });

    _scrollToBottom();

    try {
      final response =
          await widget.apiClient.post(
        '/api/v1/assistant/messages',
        body: {
          'message': message,

          // Patient App에서는 patient_id를 보내지 않는다.
          //
          // Backend가 JWT request.user를 기준으로
          // Patient.user를 찾아 본인 patient_id를 확정한다.
          'context': {
            'scope': 'PATIENT',
          },

          if (_conversationId != null)
            'conversation_id':
                _conversationId,
        },
      );

      final answer =
          response['answer']?.toString().trim();

      final conversationId =
          response['conversation_id']
              ?.toString()
              .trim();

      if (answer == null || answer.isEmpty) {
        throw const ApiException(
          statusCode: 502,
          message:
              'AI 응답을 확인할 수 없습니다.',
        );
      }

      if (conversationId != null &&
          conversationId.isNotEmpty) {
        _conversationId =
            conversationId;
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _messages.add(
          _AssistantChatMessage(
            text: answer,
            isUser: false,
          ),
        );
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _messages.add(
          _AssistantChatMessage(
            text:
                '요청을 처리하지 못했습니다.\n${error.message}',
            isUser: false,
            isError: true,
          ),
        );
      });
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _messages.add(
          const _AssistantChatMessage(
            text:
                'AI 도우미 연결 중 오류가 발생했습니다.',
            isUser: false,
            isError: true,
          ),
        );
      });
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });

        _scrollToBottom();
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback(
      (_) {
        if (!_scrollController.hasClients) {
          return;
        }

        _scrollController.animateTo(
          _scrollController
              .position
              .maxScrollExtent,
          duration:
              const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          tooltip: '뒤로가기',
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: Row(
          children: [
            ClipOval(
              child: SizedBox(
                width: 32,
                height: 32,
                child: Image.asset(
                  'assets/images/image1.png',
                  fit: BoxFit.contain,
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text('AI 건강도우미'),
          ],
        ),
      ),
      body: SafeArea(
        top: false,
        child: Column(
          children: [
            Expanded(
              child: _messages.isEmpty
                  ? _buildEmptyState()
                  : ListView.builder(
                      controller:
                          _scrollController,
                      padding:
                          const EdgeInsets.all(16),
                      itemCount:
                          _messages.length,
                      itemBuilder:
                          (context, index) {
                        return _MessageBubble(
                          message:
                              _messages[index],
                        );
                      },
                    ),
            ),

            if (_sending)
              const Padding(
                padding:
                    EdgeInsets.only(
                  left: 20,
                  right: 20,
                  bottom: 8,
                ),
                child: Row(
                  children: [
                    SizedBox(
                      width: 16,
                      height: 16,
                      child:
                          CircularProgressIndicator(
                        strokeWidth: 2,
                      ),
                    ),
                    SizedBox(width: 8),
                    Text(
                      '호짱이 답변을 확인하고 있어요.',
                      style: TextStyle(
                        color:
                            Color(0xFF65758D),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),

            _buildInput(),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding:
            const EdgeInsets.all(28),
        child: Column(
          mainAxisSize:
              MainAxisSize.min,
          children: [
            Image.asset(
              'assets/images/image1.png',
              width: 120,
              height: 120,
              fit: BoxFit.contain,
            ),
            const SizedBox(height: 16),
            const Text(
              '호짱에게 궁금한 점을 물어보세요.',
              textAlign:
                  TextAlign.center,
              style: TextStyle(
                color:
                    Color(0xFF263A5A),
                fontSize: 16,
                fontWeight:
                    FontWeight.w800,
              ),
            ),
            const SizedBox(height: 7),
            const Text(
              '예약, 복약, 검사 결과 등 '
              '내 의료정보를 확인할 수 있어요.',
              textAlign:
                  TextAlign.center,
              style: TextStyle(
                color:
                    Color(0xFF65758D),
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInput() {
    return Container(
      padding:
          const EdgeInsets.fromLTRB(
        16,
        10,
        16,
        16,
      ),
      decoration:
          const BoxDecoration(
        color: Colors.white,
        border: Border(
          top: BorderSide(
            color:
                Color(0xFFE0E4F1),
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller:
                  _messageController,
              onChanged: (_) {
                setState(() {});
              },
              minLines: 1,
              maxLines: 3,
              textInputAction:
                  TextInputAction.newline,
              decoration:
                  InputDecoration(
                hintText:
                    '메시지를 입력해 주세요.',
                filled: true,
                fillColor:
                    const Color(
                  0xFFF6F7FB,
                ),
                contentPadding:
                    const EdgeInsets
                        .symmetric(
                  horizontal: 14,
                  vertical: 11,
                ),
                border:
                    OutlineInputBorder(
                  borderRadius:
                      BorderRadius
                          .circular(18),
                  borderSide:
                      BorderSide.none,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed:
                _canSend
                    ? _sendMessage
                    : null,
            icon: const Icon(
              Icons.send_rounded,
            ),
            tooltip: '전송',
          ),
        ],
      ),
    );
  }
}

class _AssistantChatMessage {
  const _AssistantChatMessage({
    required this.text,
    required this.isUser,
    this.isError = false,
  });

  final String text;
  final bool isUser;
  final bool isError;
}

class _MessageBubble
    extends StatelessWidget {
  const _MessageBubble({
    required this.message,
  });

  final _AssistantChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final bubble = Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: isUser
            ? const Color(0xFF356FAF)
            : message.isError
                ? const Color(0xFFFFF1F3)
                : Colors.white,
        border: isUser
            ? null
            : Border.all(
                color: message.isError
                    ? const Color(0xFFFFD5DA)
                    : const Color(0xFFD7E4F4),
              ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: isUser
          ? Text(
              message.text,
              style: const TextStyle(color: Colors.white, height: 1.5),
            )
          : MarkdownBody(
              data: _safeAiMarkdown(message.text),
              selectable: true,
              softLineBreak: true,
              styleSheet: _patientAiMarkdownStyle(message.isError),
              imageBuilder: (uri, title, alt) => const SizedBox.shrink(),
              onTapLink: (text, href, title) {},
            ),
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final maxBubbleWidth = isUser
            ? 320.0
            : (constraints.maxWidth - 42).clamp(0.0, 320.0).toDouble();

        if (isUser) {
          return Align(
            alignment: Alignment.centerRight,
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: maxBubbleWidth),
              child: Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: bubble,
              ),
            ),
          );
        }

        return Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipOval(
                child: SizedBox(
                  width: 34,
                  height: 34,
                  child: Image.asset(
                    'assets/images/image1.png',
                    fit: BoxFit.contain,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxBubbleWidth),
                child: bubble,
              ),
            ],
          ),
        );
      },
    );
  }
}

String _safeAiMarkdown(String markdown) =>
    markdown.replaceAll(RegExp(r'</?[a-zA-Z][^>]*>'), '');

MarkdownStyleSheet _patientAiMarkdownStyle(bool isError) {
  final color = isError ? const Color(0xFFCC3A4B) : const Color(0xFF263A5A);
  return MarkdownStyleSheet(
    p: TextStyle(color: color, fontSize: 14, height: 1.55),
    strong: TextStyle(color: color, fontWeight: FontWeight.w800),
    h1: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.w800),
    h2: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.w800),
    h3: TextStyle(color: color, fontSize: 15, fontWeight: FontWeight.w700),
    listBullet: TextStyle(color: color, fontSize: 14),
    blockSpacing: 10,
    listIndent: 20,
  );
}
