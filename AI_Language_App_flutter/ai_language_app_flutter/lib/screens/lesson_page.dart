import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';
import '../services/api/api_service.dart';
import '../services/api/lesson_ai_api_service.dart';
import '../services/api/lesson_hint_api_service.dart';
import '../widgets/learning_path/lesson_hint_dialog.dart';
import '../widgets/learning_path/lesson_translation_check_dialog.dart';
import '../widgets/words/word_detail_dialog.dart';
import 'lesson_assessment_page.dart';

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

  final Map<String, String> _translationCache = {};
  final Set<String> _visibleTranslations = {};
  final Set<String> _translationLoading = {};

  String? _conversationId;
  String? _error;
  int? _dailyLimit;
  int? _dailyRemaining;
  LessonHint? _currentHint;

  bool _loading = true;
  bool _sending = false;
  bool _submitting = false;
  bool _lessonStarted = false;
  bool _hintLoading = false;
  bool _translationCheckShown = false;
  bool _aiTyping = false;
  String? _lastFailedMessage;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? LearningRepository();
    _apiService = ApiService();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startTutor());
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  String _locale() => widget.languageController.locale.languageCode;

  String _text({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? it,
    String? ja,
    String? ko,
    String? zh,
  }) {
    switch (_locale()) {
      case 'fr': return fr ?? en;
      case 'es': return es ?? en;
      case 'de': return de ?? en;
      case 'it': return it ?? en;
      case 'ja': return ja ?? en;
      case 'ko': return ko ?? en;
      case 'zh': return zh ?? en;
      case 'ar':
      default: return ar;
    }
  }

  String _pageTitle() => _text(
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

  String _dailyLimitLabel() => _text(
        ar: 'المحادثات المتبقية اليوم',
        en: 'Conversations remaining today',
        fr: 'Conversations restantes aujourd\'hui',
        es: 'Conversaciones restantes hoy',
        de: 'Verbleibende Gespräche heute',
        it: 'Conversazioni rimanenti oggi',
        ja: '今日の残り会話数',
        ko: '오늘 남은 대화 수',
        zh: '今日剩余对话数',
      );

  String _dailyLimitReachedLabel() => _text(
        ar: 'لقد وصلت إلى الحد الأقصى للمحادثات اليوم',
        en: 'You\'ve reached your conversation limit for today',
        fr: 'Vous avez atteint votre limite de conversations pour aujourd\'hui',
        es: 'Has alcanzado tu límite de conversaciones para hoy',
        de: 'Sie haben Ihr Gesprächslimit für heute erreicht',
        it: 'Hai raggiunto il limite di conversazioni per oggi',
        ja: '今日の会話制限に達しました',
        ko: '오늘 대화 한도에 도달했습니다',
        zh: '您已达到今天的对话限制',
      );

  String _retryLabel() => _text(
        ar: 'إعادة المحاولة',
        en: 'Retry',
        fr: 'Réessayer',
        es: 'Reintentar',
        de: 'Erneut versuchen',
        it: 'Riprova',
        ja: '再試行',
        ko: '다시 시도',
        zh: '重试',
      );

  String _restartLessonLabel() => _text(
        ar: 'إعادة بدء الدرس',
        en: 'Restart Lesson',
        fr: 'Recommencer la leçon',
        es: 'Reiniciar lección',
        de: 'Lektion neu starten',
        it: 'Riavvia lezione',
        ja: 'レッスンを再開',
        ko: '레슨 다시 시작',
        zh: '重新开始课程',
      );

  String _aiTypingLabel() => _text(
        ar: 'المدرّس الذكي يكتب...',
        en: 'AI tutor is typing...',
        fr: 'Le tuteur IA écrit...',
        es: 'El tutor de IA está escribiendo...',
        de: 'KI-Tutor tippt...',
        it: 'Il tutor IA sta scrivendo...',
        ja: 'AIチューターが入力中...',
        ko: 'AI 튜터가 입력 중...',
        zh: 'AI 导师正在输入...',
      );

  String _inputHint() => _text(
        ar: 'اكتب إجابتك...', en: 'Write your answer...',
        fr: 'Écrivez votre réponse...', es: 'Escribe tu respuesta...',
        de: 'Schreibe deine Antwort...', it: 'Scrivi la tua risposta...',
        ja: '答えを入力...', ko: '답변을 입력하세요...', zh: '输入你的回答...',
      );

  String _sendLabel() => _text(
        ar: 'إرسال', en: 'Send', fr: 'Envoyer', es: 'Enviar', de: 'Senden',
        it: 'Invia', ja: '送信', ko: '보내기', zh: '发送',
      );

  String _hintLabel() => _text(
        ar: 'اقتراح إجابة', en: 'Answer hint', fr: 'Indice de réponse',
        es: 'Pista de respuesta', de: 'Antwort-Hinweis', it: 'Suggerimento risposta',
        ja: '回答ヒント', ko: '답변 힌트', zh: '回答提示',
      );

  String _hintSuggestionLabel() => _text(
        ar: 'الكلام المقترح', en: 'Suggested answer', fr: 'Réponse suggérée',
        es: 'Respuesta sugerida', de: 'Vorgeschlagene Antwort', it: 'Risposta suggerita',
        ja: 'おすすめの回答', ko: '추천 답변', zh: '建议回答',
      );

  String _hintTranslationLabel() => _text(
        ar: 'المعنى', en: 'Meaning', fr: 'Signification', es: 'Significado',
        de: 'Bedeutung', it: 'Significato', ja: '意味', ko: '의미', zh: '含义',
      );

  String _hideHintLabel() => _text(
        ar: 'إخفاء الاقتراح', en: 'Hide suggestion', fr: 'Masquer la suggestion',
        es: 'Ocultar sugerencia', de: 'Vorschlag ausblenden', it: 'Nascondi suggerimento',
        ja: '提案を非表示', ko: '추천 숨기기', zh: '隐藏建议',
      );

  String _hintErrorLabel() => _text(
        ar: 'تعذر الحصول على اقتراح. حاول مرة أخرى.',
        en: 'Could not get a hint. Please try again.',
        fr: 'Impossible d’obtenir un indice. Réessayez.',
        es: 'No se pudo obtener una pista. Inténtalo de nuevo.',
        de: 'Hinweis konnte nicht geladen werden. Bitte erneut versuchen.',
        it: 'Impossibile ottenere un suggerimento. Riprova.',
        ja: 'ヒントを取得できませんでした。もう一度お試しください。',
        ko: '힌트를 가져오지 못했습니다. 다시 시도하세요.',
        zh: '无法获取提示，请重试。',
      );

  String _translateLabel() => _text(
        ar: 'ترجمة', en: 'Translate', fr: 'Traduire', es: 'Traducir', de: 'Übersetzen',
        it: 'Traduci', ja: '翻訳', ko: '번역', zh: '翻译',
      );

  String _hideTranslationLabel() => _text(
        ar: 'إخفاء الترجمة', en: 'Hide translation', fr: 'Masquer la traduction',
        es: 'Ocultar traducción', de: 'Übersetzung ausblenden', it: 'Nascondi la traduzione',
        ja: '翻訳を隠す', ko: '번역 숨기기', zh: '隐藏翻译',
      );

  String _translationErrorLabel() => _text(
        ar: 'تعذرت الترجمة. حاول مرة أخرى.', en: 'Translation failed. Please try again.',
        fr: 'La traduction a échoué. Réessayez.', es: 'La traducción falló. Inténtalo de nuevo.',
        de: 'Die Übersetzung ist fehlgeschlagen. Bitte erneut versuchen.',
        it: 'La traduzione non è riuscita. Riprova.', ja: '翻訳に失敗しました。もう一度お試しください。',
        ko: '번역에 실패했습니다. 다시 시도하세요.', zh: '翻译失败，请重试。',
      );

  String _translationKey(_TutorMessage message) => '${_locale()}:${message.role}:${message.text}';

  Future<void> _toggleTranslation(_TutorMessage message) async {
    final key = _translationKey(message);
    if (_translationCache.containsKey(key)) {
      setState(() {
        if (_visibleTranslations.contains(key)) {
          _visibleTranslations.remove(key);
        } else {
          _visibleTranslations.add(key);
        }
      });
      return;
    }
    if (_translationLoading.contains(key)) return;
    setState(() => _translationLoading.add(key));
    try {
      final translation = await _apiService.translateText(text: message.text);
      if (!mounted) return;
      setState(() {
        _translationCache[key] = translation;
        _visibleTranslations.add(key);
        _translationLoading.remove(key);
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _translationLoading.remove(key));
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_translationErrorLabel())));
    }
  }

  Future<void> _showHint() async {
    if (_hintLoading || _sending || _submitting || _messages.isEmpty) return;
    setState(() => _hintLoading = true);
    try {
      final hint = await _apiService.getLessonHint(
        lessonId: widget.lesson.id,
        conversationId: _conversationId,
      );
      if (!mounted) return;
      setState(() => _currentHint = hint);
      await showLessonHintDialog(context, hint: hint, text: _text);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_hintErrorLabel())));
    } finally {
      if (mounted) setState(() => _hintLoading = false);
    }
  }

  Future<void> _startTutor() async {
    if (_lessonStarted || _sending) return;
    setState(() {
      _lessonStarted = true;
      _loading = true;
      _error = null;
    });
    await _sendMessage('START_LESSON', showUserMessage: false);
  }

  Future<void> _sendCurrentMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty || _sending || _submitting) return;
    _messageController.clear();
    setState(() => _currentHint = null);
    await _sendMessage(message, showUserMessage: true);
  }

  Future<void> _sendMessage(String message, {required bool showUserMessage}) async {
    if (_sending || _submitting) return;
    if (showUserMessage) {
      setState(() {
        _messages.add(_TutorMessage(role: 'user', text: message));
        _error = null;
        _lastFailedMessage = null;
      });
      _scrollToBottom();
    }
    setState(() {
      _sending = true;
      _aiTyping = showUserMessage;
      _loading = !showUserMessage;
      _error = null;
      _lastFailedMessage = showUserMessage ? message : _lastFailedMessage;
    });

    var assistantIndex = -1;
    try {
      await for (final chunk in _apiService.lessonAiChat(
        lessonId: widget.lesson.id,
        message: message,
        conversationId: _conversationId,
      )) {
        if (!mounted) break;

        if (chunk.type == 'conversation') {
          final id = chunk.conversationId;
          if (id != null && id.isNotEmpty) _conversationId = id;
        }

        if (chunk.type == 'history' && chunk.history != null) {
          _messages.clear();
          for (final item in chunk.history!) {
            final role = item['role'] == 'user' ? 'user' : 'assistant';
            final text = item['text'] ?? '';
            if (text.isNotEmpty) _messages.add(_TutorMessage(role: role, text: text));
          }
          setState(() {
            _loading = false;
            _aiTyping = false;
            _error = null;
            _lastFailedMessage = null;
          });
          _scrollToBottom();
          continue;
        }

        if (chunk.type == 'chunk') {
          final text = chunk.text ?? '';
          if (text.isNotEmpty) {
            if (assistantIndex == -1) {
              _messages.add(_TutorMessage(role: 'assistant', text: text));
              assistantIndex = _messages.length - 1;
            } else {
              _messages[assistantIndex].text += text;
            }
            setState(() {
              _aiTyping = true;
            });
            _scrollToBottom();
          }
        }

        if (chunk.type == 'done') {
          final id = chunk.conversationId;
          if (id != null && id.isNotEmpty) _conversationId = id;
          _dailyLimit = chunk.dailyLimit;
          _dailyRemaining = chunk.dailyRemaining;
          setState(() {
            _aiTyping = false;
            _lastFailedMessage = null;
          });

          if (chunk.lessonReady == true && !_translationCheckShown) {
            _translationCheckShown = true;
            await _showTranslationCheckAndAssessment();
          }
        }

        if (chunk.type == 'error') {
          throw Exception(chunk.message ?? _errorLabel());
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _aiTyping = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorLabel()),
            action: showUserMessage
                ? SnackBarAction(
                    label: _retryLabel(),
                    onPressed: () => _retryLastMessage(),
                  )
                : null,
          ),
        );
      }
    }

    if (mounted) {
      setState(() {
        _sending = false;
        _loading = false;
        _aiTyping = false;
      });
      _scrollToBottom();
    }
  }

  Future<void> _retryLastMessage() async {
    final message = _lastFailedMessage;
    if (message == null || message.isEmpty) return;

    // Remove the failed user message
    if (_messages.isNotEmpty && _messages.last.isUser) {
      setState(() {
        _messages.removeLast();
      });
    }

    if (message == 'START_LESSON') {
      await _startTutor();
    } else {
      await _sendCurrentMessage();
    }
  }

  Future<void> _restartLesson() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          title: Text(_restartLessonLabel()),
          content: Text(_text(
            ar: 'سيتم حذف المحادثة الحالية والبدء من جديد. هل أنت متأكد؟',
            en: 'The current conversation will be deleted and the lesson will restart. Are you sure?',
            fr: 'La conversation actuelle sera supprimée et la leçon redémarrera. Êtes-vous sûr ?',
            es: 'Se eliminará la conversación actual y la lección se reiniciará. ¿Está seguro?',
            de: 'Der aktuelle Chat wird gelöscht und die Lektion neu gestartet. Sind Sie sicher?',
            it: 'La conversazione attuale verrà eliminata e la lezione verrà riavviata. Sei sicuro?',
            ja: '現在の会話が削除され、レッスンが再開されます。よろしいですか？',
            ko: '현재 대화가 삭제되고 레슨이 다시 시작됩니다. 계속하시겠습니까?',
            zh: '当前对话将被删除，课程将重新开始。您确定吗？',
          )),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(_text(
                ar: 'إلغاء', en: 'Cancel', fr: 'Annuler', es: 'Cancelar',
                de: 'Abbrechen', it: 'Annulla', ja: 'キャンセル',
                ko: '취소', zh: '取消',
              )),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: Text(_restartLessonLabel()),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) return;

    setState(() {
      _messages.clear();
      _error = null;
      _lastFailedMessage = null;
      _aiTyping = false;
      _sending = false;
      _loading = true;
      _lessonStarted = false;
      _translationCheckShown = false;
    });

    // Clear API cache for this lesson
    LessonAiApiService.clearCache(widget.lesson.id);

    await _startTutor();
  }

  Future<void> _showTranslationCheckAndAssessment() async {
    if (!mounted || _conversationId == null || _conversationId!.isEmpty) return;

    setState(() {
      _submitting = true;
      _error = null;
    });

    final passedTranslationCheck = await showLessonTranslationCheckDialog(
      context: context,
      apiService: _apiService,
      lessonId: widget.lesson.id,
      conversationId: _conversationId!,
      text: _text,
    );

    if (!mounted) return;

    if (!passedTranslationCheck) {
      setState(() {
        _submitting = false;
        _translationCheckShown = false;
      });
      return;
    }

    final passedAssessment = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LessonAssessmentPage(
          lesson: widget.lesson,
          languageController: widget.languageController,
          repository: _repository,
          conversationId: _conversationId,
        ),
      ),
    );

    if (!mounted) return;

    setState(() {
      _submitting = false;
      if (passedAssessment != true) _translationCheckShown = false;
    });

    if (passedAssessment == true) Navigator.of(context).pop(true);
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  String _cleanWordToken(String token) => token.replaceAll(
        RegExp(r'^[\.,!?;:()\[\]{}"“”„«»…*_~`、。！？；：（）［］｛｝「」『』【】《》〈〉]+|[\.,!?;:()\[\]{}"“”„«»…*_~`、。！？；：（）［］｛｝「」『』【】《》〈〉]+$'),
        '',
      );

  bool _isWhitespaceRune(int rune) => RegExp(r'\s').hasMatch(String.fromCharCode(rune));

  bool _isCjkPunctuationRune(int rune) => RegExp(r'[\.,!?;:()\[\]{}"“”„«»…*_~`、。！？；：（）［］｛｝「」『』【】《》〈〉]').hasMatch(String.fromCharCode(rune));

  bool _isCjkIdeographRune(int rune) =>
      (rune >= 0x3400 && rune <= 0x4DBF) ||
      (rune >= 0x4E00 && rune <= 0x9FFF) ||
      (rune >= 0xF900 && rune <= 0xFAFF) ||
      (rune >= 0x20000 && rune <= 0x2FA1F);

  bool _isJapaneseKanaRune(int rune) =>
      (rune >= 0x3040 && rune <= 0x309F) ||
      (rune >= 0x30A0 && rune <= 0x30FF) ||
      (rune >= 0x31F0 && rune <= 0x31FF);

  List<String> _messageTokens(String text) {
    final hasCjk = text.runes.any((rune) => _isCjkIdeographRune(rune) || _isJapaneseKanaRune(rune));
    if (!hasCjk) {
      return text.trim().split(RegExp(r'\s+')).where((token) => token.isNotEmpty).toList();
    }

    final result = <String>[];
    var buffer = StringBuffer();

    void flushBuffer() {
      if (buffer.isNotEmpty) {
        result.add(buffer.toString());
        buffer = StringBuffer();
      }
    }

    for (final rune in text.runes) {
      final char = String.fromCharCode(rune);
      if (_isWhitespaceRune(rune)) {
        flushBuffer();
        continue;
      }
      if (_isCjkPunctuationRune(rune)) {
        flushBuffer();
        result.add(char);
        continue;
      }
      if (_isCjkIdeographRune(rune) || _isJapaneseKanaRune(rune)) {
        flushBuffer();
        result.add(char);
        continue;
      }
      buffer.write(char);
    }
    flushBuffer();
    return result;
  }

  Future<void> _openWord(String token) async {
    final word = _cleanWordToken(token).trim();
    if (word.isEmpty) return;
    await showWordDetailDialog(context, word: word, languageCode: _locale());
  }

  TextDirection _textDirection(String text) => RegExp(r'[\u0590-\u08FF]').hasMatch(text) ? TextDirection.rtl : TextDirection.ltr;

  Widget _buildClickableMessage(String text, ThemeData theme) {
    final tokens = _messageTokens(text);
    final hasCjk = text.runes.any((rune) => _isCjkIdeographRune(rune) || _isJapaneseKanaRune(rune));
    final baseStyle = theme.textTheme.bodyLarge?.copyWith(height: 1.45);
    final direction = _textDirection(text);

    return Directionality(
      textDirection: direction,
      child: Wrap(
        textDirection: direction,
        alignment: WrapAlignment.start,
        crossAxisAlignment: WrapCrossAlignment.end,
        spacing: hasCjk ? 0 : 4,
        runSpacing: hasCjk ? 0 : 3,
        children: [
          for (final token in tokens)
            InkWell(
              borderRadius: BorderRadius.circular(5),
              onTap: () => _openWord(token),
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: hasCjk ? 0 : 1, vertical: 1),
                child: Text(token, textDirection: direction, style: baseStyle),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTranslationButton(_TutorMessage message, ThemeData theme) {
    final key = _translationKey(message);
    final cached = _translationCache.containsKey(key);
    final visible = _visibleTranslations.contains(key);
    final loading = _translationLoading.contains(key);

    return Align(
      alignment: message.isUser ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
      child: Padding(
        padding: const EdgeInsetsDirectional.only(top: 2),
        child: TextButton.icon(
          onPressed: loading ? null : () => _toggleTranslation(message),
          icon: loading
              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
              : Icon(cached && visible ? Icons.keyboard_arrow_up_rounded : Icons.translate_rounded, size: 18),
          label: Text(cached && visible ? _hideTranslationLabel() : _translateLabel()),
          style: TextButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            minimumSize: const Size(0, 32),
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
      ),
    );
  }

  Widget _buildMessage(_TutorMessage message, ThemeData theme) {
    final isUser = message.isUser;
    final key = _translationKey(message);
    final translation = _translationCache[key];
    final visible = _visibleTranslations.contains(key);

    return Align(
      alignment: isUser ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 620),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(16, 12, 12, 8),
        decoration: BoxDecoration(
          color: isUser ? theme.colorScheme.primaryContainer : theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            _buildClickableMessage(message.text, theme),
            if (visible && translation != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surface.withValues(alpha: 0.55),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Directionality(
                    textDirection: _textDirection(translation),
                    child: Text(translation, textDirection: _textDirection(translation), style: theme.textTheme.bodyMedium?.copyWith(height: 1.4)),
                  ),
                ),
              ),
            _buildTranslationButton(message, theme),
          ],
        ),
      ),
    );
  }

  Widget _buildHintSuggestion(ThemeData theme) {
    final hint = _currentHint;
    if (hint == null) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
        decoration: BoxDecoration(
          color: theme.colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: theme.colorScheme.outlineVariant),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.lightbulb_rounded, size: 20, color: theme.colorScheme.onSecondaryContainer),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_hintSuggestionLabel(), style: theme.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700, color: theme.colorScheme.onSecondaryContainer)),
                  const SizedBox(height: 4),
                  Text(hint.suggestion, textDirection: _textDirection(hint.suggestion), style: theme.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600, height: 1.35, color: theme.colorScheme.onSecondaryContainer)),
                  const SizedBox(height: 4),
                  Text('${_hintTranslationLabel()}: ${hint.translation}', textDirection: _textDirection(hint.translation), style: theme.textTheme.bodyMedium?.copyWith(height: 1.35, color: theme.colorScheme.onSecondaryContainer)),
                ],
              ),
            ),
            IconButton(
              onPressed: () => setState(() => _currentHint = null),
              tooltip: _hideHintLabel(),
              visualDensity: VisualDensity.compact,
              icon: const Icon(Icons.close_rounded),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildComposer(ThemeData theme) {
    return SafeArea(
      top: false,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHintSuggestion(theme),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                IconButton(
                  onPressed: _hintLoading || _sending || _submitting || _messages.isEmpty ? null : _showHint,
                  tooltip: _hintLabel(),
                  icon: _hintLoading
                      ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.lightbulb_outline_rounded),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: ValueListenableBuilder<TextEditingValue>(
                    valueListenable: _messageController,
                    builder: (context, value, child) {
                      final direction = _textDirection(value.text);
                      return TextField(
                        controller: _messageController,
                        enabled: !_sending && !_submitting,
                        minLines: 1,
                        maxLines: 5,
                        textDirection: direction,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendCurrentMessage(),
                        decoration: InputDecoration(
                          hintText: _inputHint(),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _sending || _submitting ? null : _sendCurrentMessage,
                  tooltip: _sendLabel(),
                  icon: const Icon(Icons.send_rounded),
                ),
              ],
            ),
          ),
        ],
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
            const Icon(Icons.smart_toy_outlined, size: 56),
            const SizedBox(height: 16),
            Text(
              _text(
                ar: 'يبدأ المدرّس الذكي الدرس...',
                en: 'Your AI tutor is starting the lesson...',
                fr: 'Votre tuteur IA démarre la leçon...',
                es: 'Tu tutor de IA está iniciando la lección...',
                de: 'Dein KI-Tutor startet die Lektion...',
                it: 'Il tuo tutor IA sta iniziando la lezione...',
                ja: 'AIチューターがレッスンを開始しています...',
                ko: 'AI 튜터가 레슨을 시작하고 있습니다...',
                zh: 'AI 导师正在开始课程...',
              ),
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

  String _errorLabel() => _text(
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isRtl = _locale() == 'ar';

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Text(_pageTitle(), style: const TextStyle(fontWeight: FontWeight.w700)),
        actions: [
          if (_dailyRemaining != null)
            Padding(
              padding: const EdgeInsetsDirectional.only(end: 4),
              child: Tooltip(
                message: _dailyLimitLabel(),
                child: Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: (_dailyRemaining ?? 0) > 0
                          ? theme.colorScheme.primaryContainer
                          : theme.colorScheme.errorContainer,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.local_fire_department_rounded,
                          size: 14,
                          color: (_dailyRemaining ?? 0) > 0
                              ? theme.colorScheme.onPrimaryContainer
                              : theme.colorScheme.onErrorContainer,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${_dailyRemaining ?? 0}/${_dailyLimit ?? '∞'}',
                          style: theme.textTheme.labelSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: (_dailyRemaining ?? 0) > 0
                                ? theme.colorScheme.onPrimaryContainer
                                : theme.colorScheme.onErrorContainer,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          IconButton(
            tooltip: _restartLessonLabel(),
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _sending || _submitting ? null : _restartLesson,
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: Directionality(
        textDirection: isRtl ? TextDirection.rtl : TextDirection.ltr,
        child: Column(
          children: [
            Expanded(
              child: _messages.isEmpty && _loading
                  ? _buildEmptyState(theme)
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.fromLTRB(16, 20, 16, 12),
                      itemCount: _messages.length + (_sending && !_aiTyping ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (index >= _messages.length) {
                          return _buildLoadingIndicator(theme);
                        }
                        return _buildMessage(_messages[index], theme);
                      },
                    ),
            ),
            if (_aiTyping && _messages.isNotEmpty && !_loading)
              _buildTypingIndicator(theme),
            if (_error != null) _buildErrorBanner(theme),
            if ((_dailyRemaining ?? 1) <= 0 && !_loading)
              _buildDailyLimitBanner(theme),
            _buildComposer(theme),
          ],
        ),
      ),
    );
  }

  Widget _buildTypingIndicator(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _TypingDots(color: theme.colorScheme.primary),
          const SizedBox(width: 10),
          Text(
            _aiTypingLabel(),
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingIndicator(ThemeData theme) {
    return Align(
      alignment: AlignmentDirectional.centerStart,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
            const SizedBox(width: 10),
            Text(_text(
              ar: 'يبدأ المدرّس الذكي الدرس...',
              en: 'Your AI tutor is starting the lesson...',
              fr: 'Votre tuteur IA démarre la leçon...',
              es: 'Tu tutor de IA está iniciando la lección...',
              de: 'Dein KI-Tutor startet die Lektion...',
              it: 'Il tuo tutor IA sta iniziando la lezione...',
              ja: 'AIチューターがレッスンを開始しています...',
              ko: 'AI 튜터가 레슨을 시작하고 있습니다...',
              zh: 'AI 导师正在开始课程...',
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorBanner(ThemeData theme) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.errorContainer.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: theme.colorScheme.error.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.error_outline_rounded,
            size: 20,
            color: theme.colorScheme.onErrorContainer,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _errorLabel(),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onErrorContainer,
              ),
            ),
          ),
          if (_lastFailedMessage != null)
            TextButton(
              onPressed: _sending ? null : _retryLastMessage,
              child: Text(_retryLabel()),
            ),
        ],
      ),
    );
  }

  Widget _buildDailyLimitBanner(ThemeData theme) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.tertiaryContainer.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline_rounded,
            size: 20,
            color: theme.colorScheme.onTertiaryContainer,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _dailyLimitReachedLabel(),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onTertiaryContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Animated typing indicator with three dots.
class _TypingDots extends StatefulWidget {
  final Color color;
  const _TypingDots({required this.color});

  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 36,
      height: 18,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: List.generate(3, (i) {
              final progress = (_controller.value - i * 0.2) % 1.0;
              final scale = (1.0 - (progress - 0.5).abs() * 2).clamp(0.5, 1.0);
              return Transform.scale(
                scale: scale,
                child: Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: widget.color,
                    shape: BoxShape.circle,
                  ),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}
