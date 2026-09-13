import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';

// Practice completion is intentionally explicit: the learner can finish only
// after sending at least one real message. The backend validates the
// conversation, lesson, stage, and ownership before marking it complete.
class LessonChatPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;
  final String stage;

  const LessonChatPage({super.key, required this.lesson, required this.languageController, required this.stage});

  bool get isTeaching => stage == 'teaching';

  @override
  State<LessonChatPage> createState() => _LessonChatPageState();
}

class _LessonChatPageState extends State<LessonChatPage> {
  final ApiService _api = ApiService();
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scroll = ScrollController();
  final List<_ChatMessage> _messages = [];
  StreamSubscription<LessonStageAiChunk>? _subscription;
  String? _conversationId;
  String? _error;
  bool _sending = false;
  bool _completed = false;
  bool _hasLearnerMessage = false;

  String _locale() => widget.languageController.locale.languageCode;

  String _t({required String ar, required String en, String? fr, String? es, String? de}) {
    switch (_locale()) {
      case 'fr': return fr ?? en;
      case 'es': return es ?? en;
      case 'de': return de ?? en;
      default: return ar;
    }
  }

  String get _completionLabel => widget.isTeaching
      ? _t(ar: 'متابعة إلى الممارسة', en: 'Continue to practice', fr: 'Continuer vers la pratique', es: 'Continuar a la práctica', de: 'Weiter zur Übung')
      : _t(ar: 'إنهاء الدرس', en: 'Finish lesson', fr: 'Terminer la leçon', es: 'Terminar la lección', de: 'Lektion beenden');

  @override
  void dispose() {
    _subscription?.cancel();
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _addMessage(String role, String text) {
    if (text.trim().isEmpty) return;
    setState(() => _messages.add(_ChatMessage(role: role, text: text)));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending || _completed) return;

    setState(() {
      _sending = true;
      _error = null;
      _hasLearnerMessage = true;
    });
    _controller.clear();
    _addMessage('learner', text);

    try {
      await _subscription?.cancel();
      _subscription = _api.lessonStageAiChat(
        lessonId: widget.lesson.id,
        stage: widget.stage,
        message: text,
        conversationId: _conversationId,
      ).listen(
        (chunk) {
          if (!mounted) return;
          if (chunk.conversationId != null && chunk.conversationId!.isNotEmpty) {
            _conversationId = chunk.conversationId;
          }
          if (chunk.text != null && chunk.text!.trim().isNotEmpty) {
            _addMessage('assistant', chunk.text!);
          }
          // Teaching completion is produced by the backend only after all
          // required targets are complete. Practice is completed explicitly
          // through _finishPractice and therefore does not depend on an AI
          // completion marker that the Practice route does not generate.
          if (widget.isTeaching && chunk.axisCompleted) {
            setState(() => _completed = true);
          }
        },
        onError: (Object error) {
          if (!mounted) return;
          setState(() {
            _sending = false;
            _error = error.toString();
          });
        },
        onDone: () {
          if (!mounted) return;
          setState(() => _sending = false);
        },
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _finishPractice() async {
    if (widget.isTeaching || !_hasLearnerMessage || _conversationId == null || _sending || _completed) return;
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await _api.completeLessonStage(
        lessonId: widget.lesson.id,
        stage: 'practice',
        conversationId: _conversationId,
      );
      if (!mounted) return;
      setState(() {
        _sending = false;
        _completed = true;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _error = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(widget.isTeaching ? _t(ar: 'التعليم', en: 'Teaching') : _t(ar: 'الممارسة', en: 'Practice'))),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? Center(child: Padding(padding: const EdgeInsets.all(32), child: Text(_t(ar: 'ابدأ بإرسال إجابتك.', en: 'Start by sending your answer.'), textAlign: TextAlign.center)))
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      final isLearner = message.role == 'learner';
                      return Align(
                        alignment: isLearner ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                          constraints: const BoxConstraints(maxWidth: 680),
                          decoration: BoxDecoration(
                            color: isLearner ? theme.colorScheme.primaryContainer : theme.colorScheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Text(message.text),
                        ),
                      );
                    },
                  ),
          ),
          if (_error != null)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: theme.colorScheme.errorContainer, borderRadius: BorderRadius.circular(16)),
              child: Row(children: [Icon(Icons.error_outline_rounded, color: theme.colorScheme.error, size: 20), const SizedBox(width: 8), Expanded(child: Text(_error!))]),
            ),
          if (_completed)
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => Navigator.pop(context, true),
                    icon: Icon(widget.isTeaching ? Icons.arrow_forward_rounded : Icons.check_rounded),
                    label: Text(_completionLabel, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                  ),
                ),
              ),
            )
          else
            SafeArea(
              top: false,
              child: Row(
                children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 8, 16),
                      child: TextField(
                        controller: _controller,
                        minLines: 1,
                        maxLines: 5,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _send(),
                        decoration: InputDecoration(
                          hintText: _t(ar: 'اكتب إجابتك...', en: 'Write your answer...'),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
                        ),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(right: 16, bottom: 16),
                    child: IconButton.filled(
                      onPressed: _sending ? null : _send,
                      icon: _sending ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.send_rounded),
                    ),
                  ),
                  if (!widget.isTeaching)
                    Padding(
                      padding: const EdgeInsets.only(right: 8, bottom: 16),
                      child: TextButton(
                        onPressed: (_sending || !_hasLearnerMessage || _conversationId == null) ? null : _finishPractice,
                        child: Text(_t(ar: 'إنهاء', en: 'Finish')),
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _ChatMessage {
  final String role;
  final String text;
  const _ChatMessage({required this.role, required this.text});
}
