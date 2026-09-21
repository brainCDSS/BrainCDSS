import 'package:flutter/material.dart';

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
        title: const Text('AI 건강도우미'),
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

    return Align(
      alignment:
          isUser
              ? Alignment.centerRight
              : Alignment.centerLeft,
      child: Container(
        constraints:
            const BoxConstraints(
          maxWidth: 320,
        ),
        margin:
            const EdgeInsets.only(
          bottom: 12,
        ),
        padding:
            const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 11,
        ),
        decoration:
            BoxDecoration(
          color: isUser
              ? const Color(
                  0xFF5665B8,
                )
              : message.isError
                  ? const Color(
                      0xFFFFF1F3,
                    )
                  : const Color(
                      0xFFF3F5FA,
                    ),
          borderRadius:
              BorderRadius.circular(
            16,
          ),
        ),
        child: Text(
          message.text,
          style: TextStyle(
            color: isUser
                ? Colors.white
                : message.isError
                    ? const Color(
                        0xFFCC3A4B,
                      )
                    : const Color(
                        0xFF263A5A,
                      ),
            height: 1.45,
          ),
        ),
      ),
    );
  }
}