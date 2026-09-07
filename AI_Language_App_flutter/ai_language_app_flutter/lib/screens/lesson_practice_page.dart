import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';

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
  String? _translation;
  bool _starting = true;
  bool _sending = false;
  bool _completed = false;
  bool _translating = false;
  bool _suggesting = false;

  String _t(String ar, String en) =>
      widget.languageController.locale.languageCode == 'ar' ? ar : en;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _send('START_STAGE', showUser: false));
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _sendCurrent() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending || _completed) return;
    _input.clear();
    setState(() => _translation = null);
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
      await for (final chunk in _api.lessonStageAiChat(
        lessonId: widget.lesson.id,
        stage: 'practice',
        message: text,
        conversationId: _conversationId,
      )) {
        if (!mounted) return;
        if (chunk.conversationId != null &&
            chunk.conversationId!.isNotEmpty) {
          _conversationId = chunk.conversationId;
        }
        if (chunk.type == 'token' || chunk.type == 'chunk') {
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
        if (chunk.type == 'done' && chunk.axisCompleted) {
          setState(() => _completed = true);
        }
        if (chunk.type == 'error') {
          setState(() => _error = chunk.message ??
              _t('تعذر الاتصال بالمدرّس الذكي.',
                  'Could not reach the AI tutor.'));
        }
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _t('تعذر إرسال الرسالة. حاول مرة أخرى.',
          'Could not send the message. Please try again.'));
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
          _starting = false;
        });
      }
    }
  }

  String? _latestAssistantMessage() {
    for (var i = _messages.length - 1; i >= 0; i--) {
      if (!_messages[i].isUser && _messages[i].text.trim().isNotEmpty) {
        return _messages[i].text.trim();
      }
    }
    return null;
  }

  Future<void> _translateLatest() async {
    final text = _latestAssistantMessage();
    if (text == null || _translating || _sending) return;
    setState(() {
      _translating = true;
      _error = null;
    });
    try {
      final translation = await _api.translateText(text: text);
      if (!mounted) return;
      setState(() => _translation = translation);
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _t('تعذر ترجمة الرسالة.',
          'Could not translate the message.'));
    } finally {
      if (mounted) setState(() => _translating = false);
    }
  }

  Future<void> _suggestReply() async {
    if (_conversationId == null || _suggesting || _sending || _completed) return;
    setState(() {
      _suggesting = true;
      _error = null;
    });
    try {
      final hint = await _api.getLessonHint(
        lessonId: widget.lesson.id,
        conversationId: _conversationId,
      );
      if (!mounted) return;
      _input.value = TextEditingValue(
        text: hint.suggestion,
        selection: TextSelection.collapsed(offset: hint.suggestion.length),
      );
      setState(() => _translation = hint.translation);
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _t('تعذر إنشاء اقتراح للرد.',
          'Could not generate a reply suggestion.'));
    } finally {
      if (mounted) setState(() => _suggesting = false);
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
    final hasAssistantMessage = _latestAssistantMessage() != null;
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
            child: Row(children: [
              Icon(Icons.forum_rounded,
                  color: theme.colorScheme.onTertiaryContainer),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _t(
                    'استخدم أهداف الدرس الآن في محادثة طبيعية مع المدرّس الذكي.',
                    'Now use the lesson goals in a natural conversation with your AI tutor.',
                  ),
                  style: TextStyle(
                    color: theme.colorScheme.onTertiaryContainer,
                    height: 1.35,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ]),
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
                              horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: message.isUser
                                ? theme.colorScheme.primaryContainer
                                : theme.colorScheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Text(
                            message.text,
                            style: theme.textTheme.bodyLarge?.copyWith(height: 1.45),
                          ),
                        ),
                      );
                    },
                  ),
          ),
          if (_translation != null)
            Container(
              margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.translate_rounded,
                      size: 20, color: theme.colorScheme.onPrimaryContainer),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _translation!,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                        height: 1.35,
                      ),
                    ),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: () => setState(() => _translation = null),
                    icon: const Icon(Icons.close_rounded, size: 18),
                  ),
                ],
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
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: hasAssistantMessage &&
                                    !_translating &&
                                    !_sending
                                ? _translateLatest
                                : null,
                            icon: _translating
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.translate_rounded),
                            label: Text(_t('ترجمة', 'Translate')),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _conversationId != null &&
                                    !_suggesting &&
                                    !_sending
                                ? _suggestReply
                                : null,
                            icon: _suggesting
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.lightbulb_outline_rounded),
                            label: Text(_t('اقتراح رد', 'Suggest reply')),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _input,
                          enabled: !_sending,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _sendCurrent(),
                          decoration: InputDecoration(
                            hintText: _t('اكتب ردك...', 'Write your reply...'),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filled(
                        onPressed: _sending ? null : _sendCurrent,
                        icon: const Icon(Icons.send_rounded),
                      ),
                    ]),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
