import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';
import '../services/api/api_service.dart';
import '../services/api/lesson_ai_api_service.dart';

class LessonPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LearningRepository? repository;
  final LanguageController languageController;

  const LessonPage({
    super.key,
    required this.lesson,
    required this.languageController,
    this.repository,
  });

  @override
  State<LessonPage> createState() => _LessonPageState();
}

class _TutorMessage {
  final String role;
  String text;

  _TutorMessage({
    required this.role,
    required this.text,
  });

  bool get isUser => role == 'user';
}

class _LessonPageState extends State<LessonPage> {
  late final LearningRepository _repository;
  late final ApiService _apiService;

  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_TutorMessage> _messages = [];

  String? _conversationId;
  String? _error;
  int? _dailyLimit;
  int? _dailyRemaining;

  bool _loading = true;
  bool _sending = false;
  bool _submitting = false;
  bool _lessonStarted = false;

  @override
  void initState() {
    super.initState();

    _repository = widget.repository ?? LearningRepository();
    _apiService = ApiService();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startTutor();
    });
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  String _locale() {
    return widget.languageController.locale.languageCode;
  }

  String _text({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? id,
    String? it,
    String? ja,
    String? ko,
    String? nl,
    String? pl,
    String? pt,
    String? ru,
    String? th,
    String? tr,
    String? uk,
    String? vi,
    String? zh,
  }) {
    switch (_locale()) {
      case 'fr':
        return fr ?? en;
      case 'es':
        return es ?? en;
      case 'de':
        return de ?? en;
      case 'id':
        return id ?? en;
      case 'it':
        return it ?? en;
      case 'ja':
        return ja ?? en;
      case 'ko':
        return ko ?? en;
      case 'nl':
        return nl ?? en;
      case 'pl':
        return pl ?? en;
      case 'pt':
        return pt ?? en;
      case 'ru':
        return ru ?? en;
      case 'th':
        return th ?? en;
      case 'tr':
        return tr ?? en;
      case 'uk':
        return uk ?? en;
      case 'vi':
        return vi ?? en;
      case 'zh':
        return zh ?? en;
      case 'ar':
      default:
        return ar;
    }
  }

  String _pageTitle() {
    return _text(
      ar: 'الدرس ${widget.lesson.lessonOrder}',
      en: 'Lesson ${widget.lesson.lessonOrder}',
      fr: 'Leçon ${widget.lesson.lessonOrder}',
      es: 'Lección ${widget.lesson.lessonOrder}',
      de: 'Lektion ${widget.lesson.lessonOrder}',
      it: 'Lezione ${widget.lesson.lessonOrder}',
      ja: 'レッスン ${widget.lesson.lessonOrder}',
      ko: '레슨 ${widget.lesson.lessonOrder}',
      zh: '课程 ${widget.lesson.lessonOrder}',
    );
  }

  String _subtitle() {
    return _text(
      ar: widget.lesson.title,
      en: widget.lesson.title,
      fr: widget.lesson.title,
      es: widget.lesson.title,
    );
  }

  String _inputHint() {
    return _text(
      ar: 'اكتب إجابتك...',
      en: 'Write your answer...',
      fr: 'Écrivez votre réponse...',
      es: 'Escribe tu respuesta...',
      de: 'Schreibe deine Antwort...',
      it: 'Scrivi la tua risposta...',
      ja: '答えを入力...',
      ko: '답변을 입력하세요...',
      zh: '输入你的回答...',
    );
  }

  String _sendLabel() {
    return _text(
      ar: 'إرسال',
      en: 'Send',
      fr: 'Envoyer',
      es: 'Enviar',
      de: 'Senden',
      it: 'Invia',
      ja: '送信',
      ko: '보내기',
      zh: '发送',
    );
  }

  String _finishLabel() {
    return _text(
      ar: 'إنهاء الدرس',
      en: 'Finish lesson',
      fr: 'Terminer la leçon',
      es: 'Terminar lección',
      de: 'Lektion beenden',
      it: 'Termina lezione',
      ja: 'レッスンを終了',
      ko: '레슨 완료',
      zh: '完成课程',
    );
  }

  String _startingLabel() {
    return _text(
      ar: 'يبدأ المدرّس الذكي الدرس...',
      en: 'Your AI tutor is starting the lesson...',
      fr: 'Votre tuteur IA démarre la leçon...',
      es: 'Tu tutor de IA está iniciando la lección...',
      de: 'Dein KI-Tutor startet die Lektion...',
      it: 'Il tuo tutor IA sta iniziando la lezione...',
      ja: 'AIチューターがレッスンを開始しています...',
      ko: 'AI 튜터가 레슨을 시작하고 있습니다...',
      zh: 'AI 导师正在开始课程...',
    );
  }

  String _errorLabel() {
    return _text(
      ar: 'حدث خطأ أثناء الاتصال بالمدرّس الذكي.',
      en: 'Something went wrong while connecting to the AI tutor.',
      fr: 'Une erreur est survenue avec le tuteur IA.',
      es: 'Ocurrió un error al conectar con el tutor de IA.',
      de: 'Beim Verbinden mit dem KI-Tutor ist ein Fehler aufgetreten.',
      it: 'Si è verificato un errore con il tutor IA.',
      ja: 'AIチューターへの接続中にエラーが発生しました。',
      ko: 'AI 튜터 연결 중 오류가 발생했습니다.',
      zh: '连接 AI 导师时发生错误。',
    );
  }

  String _finishQuestion() {
    return _text(
      ar: 'هل تريد إنهاء هذا الدرس؟ سيتم تسجيله كمكتمل.',
      en: 'Finish this lesson? It will be marked as completed.',
      fr: 'Terminer cette leçon ? Elle sera marquée comme terminée.',
      es: '¿Terminar esta lección? Se marcará como completada.',
      de: 'Diese Lektion beenden? Sie wird als abgeschlossen markiert.',
      it: 'Terminare questa lezione? Verrà segnata come completata.',
      ja: 'このレッスンを終了しますか？完了として記録されます。',
      ko: '이 레슨을 끝낼까요? 완료된 것으로 기록됩니다.',
      zh: '完成这节课程吗？课程将被标记为已完成。',
    );
  }

  String _cancelLabel() {
    return _text(
      ar: 'إلغاء',
      en: 'Cancel',
      fr: 'Annuler',
      es: 'Cancelar',
      de: 'Abbrechen',
      it: 'Annulla',
      ja: 'キャンセル',
      ko: '취소',
      zh: '取消',
    );
  }

  String _confirmLabel() {
    return _text(
      ar: 'إنهاء',
      en: 'Finish',
      fr: 'Terminer',
      es: 'Terminar',
      de: 'Beenden',
      it: 'Termina',
      ja: '終了',
      ko: '완료',
      zh: '完成',
    );
  }

  Future<void> _startTutor() async {
    if (_lessonStarted || _sending) return;

    setState(() {
      _lessonStarted = true;
      _loading = true;
      _error = null;
    });

    await _sendMessage(
      'START_LESSON',
      showUserMessage: false,
    );
  }

  Future<void> _sendCurrentMessage() async {
    final message = _messageController.text.trim();

    if (message.isEmpty || _sending || _submitting) return;

    _messageController.clear();
    await _sendMessage(message, showUserMessage: true);
  }

  Future<void> _sendMessage(
    String message, {
    required bool showUserMessage,
  }) async {
    if (_sending || _submitting) return;

    if (showUserMessage) {
      setState(() {
        _messages.add(
          _TutorMessage(
            role: 'user',
            text: message,
          ),
        );
        _error = null;
      });
      _scrollToBottom();
    }

    setState(() {
      _sending = true;
      _loading = !showUserMessage;
      _error = null;
    });

    var assistantIndex = -1;

    try {
      await for (final chunk in _apiService.lessonAiChat(
        lessonId: widget.lesson.id,
        message: message,
        conversationId: _conversationId,
      )) {
        if (!mounted) return;

        if (chunk.type == 'conversation' && chunk.conversationId != null) {
          _conversationId = chunk.conversationId;
        }

        if (chunk.type == 'chunk' && chunk.text.isNotEmpty) {
          if (assistantIndex == -1) {
            _messages.add(
              _TutorMessage(
                role: 'assistant',
                text: chunk.text,
              ),
            );
            assistantIndex = _messages.length - 1;
          } else {
            _messages[assistantIndex].text += chunk.text;
          }

          setState(() {});
          _scrollToBottom();
        }

        if (chunk.type == 'done') {
          _conversationId = chunk.conversationId ?? _conversationId;
          _dailyLimit = chunk.dailyLimit;
          _dailyRemaining = chunk.dailyRemaining;
        }

        if (chunk.type == 'error') {
          throw Exception(chunk.message ?? _errorLabel());
        }
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _error = e.toString();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorLabel())),
      );
    } finally {
      if (!mounted) return;

      setState(() {
        _sending = false;
        _loading = false;
      });

      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;

      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _finishLesson() async {
    if (_submitting || _sending) return;

    final shouldFinish = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_finishLabel()),
        content: Text(_finishQuestion()),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(_cancelLabel()),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(_confirmLabel()),
          ),
        ],
      ),
    );

    if (shouldFinish != true || !mounted) return;

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      await _repository.completeLesson(
        lessonId: widget.lesson.id,
        score: 100,
      );

      if (!mounted) return;

      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _submitting = false;
        _error = e.toString();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorLabel())),
      );
    }
  }

  Widget _buildMessage(
    _TutorMessage message,
    ThemeData theme,
  ) {
    final isUser = message.isUser;

    return Align(
      alignment: isUser ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 620),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
        decoration: BoxDecoration(
          color: isUser
              ? theme.colorScheme.primaryContainer
              : theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(
          message.text,
          textDirection: _textDirection(message.text),
          style: theme.textTheme.bodyLarge?.copyWith(
            height: 1.45,
          ),
        ),
      ),
    );
  }

  TextDirection _textDirection(String text) {
    final arabic = RegExp(r'[\u0600-\u06FF]').hasMatch(text);
    return arabic ? TextDirection.rtl : TextDirection.ltr;
  }

  Widget _buildComposer(ThemeData theme) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                enabled: !_sending && !_submitting,
                minLines: 1,
                maxLines: 5,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _sendCurrentMessage(),
                decoration: InputDecoration(
                  hintText: _inputHint(),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(18),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: _sending || _submitting
                  ? null
                  : _sendCurrentMessage,
              tooltip: _sendLabel(),
              icon: const Icon(Icons.send_rounded),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.smart_toy_outlined,
              size: 56,
            ),
            const SizedBox(height: 16),
            Text(
              _startingLabel(),
              textAlign: TextAlign.center,
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isRtl = _locale() == 'ar';

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Column(
          crossAxisAlignment:
              isRtl ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(
              _pageTitle(),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            if (_subtitle().isNotEmpty)
              Text(
                _subtitle(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall,
              ),
          ],
        ),
        actions: [
          if (_dailyRemaining != null)
            Padding(
              padding: const EdgeInsetsDirectional.only(end: 4),
              child: Center(
                child: Text(
                  '$_dailyRemaining/${_dailyLimit ?? ''}',
                  style: theme.textTheme.labelMedium,
                ),
              ),
            ),
          IconButton(
            onPressed: _sending || _submitting ? null : _finishLesson,
            tooltip: _finishLabel(),
            icon: const Icon(Icons.check_circle_outline_rounded),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty && _loading
                ? _buildEmptyState(theme)
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(16, 20, 16, 12),
                    itemCount: _messages.length + (_sending ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index >= _messages.length) {
                        return Align(
                          alignment: AlignmentDirectional.centerStart,
                          child: Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Text(_startingLabel()),
                              ],
                            ),
                          ),
                        );
                      }

                      return _buildMessage(
                        _messages[index],
                        theme,
                      );
                    },
                  ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                _errorLabel(),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: theme.colorScheme.error,
                ),
              ),
            ),
          _buildComposer(theme),
        ],
      ),
    );
  }
}
