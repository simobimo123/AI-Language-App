import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';

class LessonTeachingPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;

  const LessonTeachingPage({
    super.key,
    required this.lesson,
    required this.languageController,
  });

  @override
  State<LessonTeachingPage> createState() => _LessonTeachingPageState();
}

class _Message {
  final String role;
  final String text;
  const _Message({required this.role, required this.text});
  bool get isUser => role == 'user';
}

class _LessonTeachingPageState extends State<LessonTeachingPage> {
  final ApiService _api = ApiService();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_Message> _messages = [];
  String? _conversationId;
  String? _error;
  bool _starting = true;
  bool _sending = false;
  bool _completed = false;

  String _t(String ar, String en) => widget.languageController.locale.languageCode == 'ar' ? ar : en;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _send('START_STAGE', showUser: false));
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
    await _send(text, showUser: true);
  }

  Future<void> _send(String text, {required bool showUser}) async {
    if (_sending) return;
    if (showUser) {
      setState(() {
        _messages.add(_Message(role: 'user', text: text));
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
        stage: 'teaching',
        message: text,
        conversationId: _conversationId,
      )) {
        if (!mounted) return;
        if (chunk.conversationId != null && chunk.conversationId!.isNotEmpty) {
          _conversationId = chunk.conversationId;
        }
        if (chunk.type == 'token' || chunk.type == 'chunk') {
          final part = chunk.text ?? '';
          if (part.isEmpty) continue;
          if (assistantIndex == -1) {
            _messages.add(const _Message(role: 'assistant', text: ''));
            assistantIndex = _messages.length - 1;
          }
          final old = _messages[assistantIndex];
          _messages[assistantIndex] = _Message(role: old.role, text: old.text + part);
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
          setState(() => _error = chunk.message ?? _t('تعذر الاتصال بالمدرّس الذكي.', 'Could not reach the AI tutor.'));
        }
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _t('تعذر إرسال الرسالة. حاول مرة أخرى.', 'Could not send the message. Please try again.'));
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
      _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 220), curve: Curves.easeOut);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(_t('المرحلة 2 · التعليم بالذكاء الاصطناعي', 'Stage 2 · AI teaching')),
        leading: IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.arrow_back_rounded)),
      ),
      body: Column(children: [
        Container(
          margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: theme.colorScheme.secondaryContainer, borderRadius: BorderRadius.circular(20)),
          child: Row(children: [
            Icon(Icons.psychology_rounded, color: theme.colorScheme.onSecondaryContainer),
            const SizedBox(width: 12),
            Expanded(child: Text(_t('المدرّس الذكي سيعلّمك أهداف الدرس، يصحح أخطاءك ويطلب منك المحاولة من جديد عند الحاجة.', 'The AI tutor teaches the lesson goals, corrects mistakes, and asks you to retry when needed.'), style: TextStyle(color: theme.colorScheme.onSecondaryContainer, height: 1.35, fontWeight: FontWeight.w600))),
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
                      alignment: message.isUser ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
                      child: Container(
                        constraints: const BoxConstraints(maxWidth: 650),
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(color: message.isUser ? theme.colorScheme.primaryContainer : theme.colorScheme.surfaceContainerHighest, borderRadius: BorderRadius.circular(18)),
                        child: Text(message.text, style: theme.textTheme.bodyLarge?.copyWith(height: 1.45)),
                      ),
                    );
                  },
                ),
        ),
        if (_error != null)
          Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4), child: Text(_error!, textAlign: TextAlign.center, style: TextStyle(color: theme.colorScheme.error))),
        if (_completed)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
            child: SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: () => Navigator.pop(context, true), icon: const Icon(Icons.arrow_forward_rounded), label: Text(_t('فتح المرحلة 3', 'Continue to stage 3')))),
          )
        else
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Row(children: [
                Expanded(child: TextField(controller: _input, enabled: !_sending, textInputAction: TextInputAction.send, onSubmitted: (_) => _sendCurrent(), decoration: InputDecoration(hintText: _t('اكتب إجابتك...', 'Write your answer...'), border: OutlineInputBorder(borderRadius: BorderRadius.circular(18))))),
                const SizedBox(width: 8),
                IconButton.filled(onPressed: _sending ? null : _sendCurrent, icon: const Icon(Icons.send_rounded)),
              ]),
            ),
          ),
      ]),
    );
  }
}
