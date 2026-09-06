import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';
import '../services/api/lesson_ai_api_service.dart';

class LessonPracticePage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;

  const LessonPracticePage({
    super.key,
    required this.lesson,
    required this.languageController,
  });

  @override
  State<LessonPracticePage> createState() => _LessonPracticePageState();
}

class _PracticeMessage {
  final String role;
  final String text;

  const _PracticeMessage({required this.role, required this.text});

  bool get isUser => role == 'user';
}

class _LessonPracticePageState extends State<LessonPracticePage> {
  final ApiService _api = ApiService();
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();
  final List<_PracticeMessage> _messages = [];

  String? _conversationId;
  String? _error;
  bool _starting = true;
  bool _sending = false;
  bool _completed = false;

  String _t(String ar, String en) =>
      widget.languageController.locale.languageCode == 'ar' ? ar : en;

  @override
  void initState() {
    super.initState();
    // Practice is a fresh AI conversation, separate from the teaching stage.
    LessonAiApiService.clearCache(widget.lesson.id);
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    await _send('START_LESSON', showUser: false);
  }

  Future<void> _sendCurrent() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending || _completed) return;
    _input.clear();
    await _send(text, showUser: true);
  }

  Future<void> _send(String text, {required bool showUser}) async {
    if (_sending) return;

    if (showUser) {
      setState(() {
        _messages.add(_PracticeMessage(role: 'user', text: text));
        _error = null;
      });
      _scrollToEnd();
    }

    setState(() {
      _sending = true;
      _starting = !showUser;
      _error = null;
    });

    var assistantIndex = -1;

    try {
      await for (final chunk in _api.lessonAiChat(
        lessonId: widget.lesson.id,
        message: text,
        conversationId: _conversationId,
      )) {
        if (!mounted) return;

        if (chunk.type == 'conversation') {
          final id = chunk.conversationId;
          if (id != null && id.isNotEmpty) _conversationId = id;
        }

        if (chunk.type == 'history' && chunk.history != null) {
          _messages
            ..clear()
            ..addAll(
              chunk.history!.map(
                (item) => _PracticeMessage(
                  role: item['role'] == 'user' ? 'user' : 'assistant',
                  text: item['text'] ?? '',
                ),
              ),
            );
          setState(() {
            _starting = false;
            _sending = false;
          });
          _scrollToEnd();
          continue;
        }

        if (chunk.type == 'chunk') {
          final part = chunk.text ?? '';
          if (part.isEmpty) continue;

          if (assistantIndex == -1) {
            _messages.add(const _PracticeMessage(role: 'assistant', text: ''));
            assistantIndex = _messages.length - 1;
          }

          final old = _messages[assistantIndex];
          _messages[assistantIndex] =
              _PracticeMessage(role: old.role, text: old.text + part);
          setState(() {
            _starting = false;
            _error = null;
          });
          _scrollToEnd();
        }

        if (chunk.type == 'done') {
          final done = chunk.lessonReady == true ||
              chunk.message == 'LESSON_COMPLETED';
          if (done) {
            setState(() => _completed = true);
          }
        }

        if (chunk.type == 'error') {
          setState(() {
            _error = chunk.message ??
                _t('تعذر الاتصال بالمدرّس الذكي.', 'Could not reach the AI tutor.');
          });
        }
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = _t(
          'تعذر إرسال الرسالة. حاول مرة أخرى.',
          'Could not send the message. Please try again.',
        );
      });
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
          _starting = false;
        });
      }
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(_t('المرحلة 3 · الممارسة', 'Stage 3 · Practice')),
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
      ),
      body: Column(
        children: [
          Container(
            margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.colorScheme.tertiaryContainer,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              children: [
                Icon(Icons.forum_rounded,
                    color: theme.colorScheme.onTertiaryContainer),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _t(
                      'الآن استخدم جمل الدرس في محادثة طبيعية مع المدرّس الذكي.',
                      'Now use the lesson sentences in a natural conversation with your AI tutor.',
                    ),
                    style: TextStyle(
                      color: theme.colorScheme.onTertiaryContainer,
                      height: 1.35,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _starting && _messages.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      return Align(
                        alignment: message.isUser
                            ? AlignmentDirectional.centerEnd
                            : AlignmentDirectional.centerStart,
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 650),
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: message.isUser
                                ? theme.colorScheme.primaryContainer
                                : theme.colorScheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Text(
                            message.text,
                            style: theme.textTheme.bodyLarge?.copyWith(
                              height: 1.45,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Text(
                _error!,
                textAlign: TextAlign.center,
                style: TextStyle(color: theme.colorScheme.error),
              ),
            ),
          if (_completed)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () => Navigator.pop(context, true),
                  icon: const Icon(Icons.check_circle_rounded),
                  label: Text(_t('إكمال الدرس', 'Complete lesson')),
                ),
              ),
            )
          else
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _input,
                        enabled: !_sending,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendCurrent(),
                        decoration: InputDecoration(
                          hintText: _t(
                            'اكتب ردك...',
                            'Write your reply...',
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      onPressed: _sending ? null : _sendCurrent,
                      icon: const Icon(Icons.send_rounded),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
