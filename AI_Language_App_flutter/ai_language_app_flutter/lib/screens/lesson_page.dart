import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';
import '../services/api/api_service.dart';
import '../widgets/learning_path/lesson_hint_dialog.dart';
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

  bool _loading = true;
  bool _sending = false;
  bool _submitting = false;
  bool _lessonStarted = false;
  bool _hintLoading = false;

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

  String _inputHint() => _text(
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

  String _sendLabel() => _text(
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

  String _hintLabel() => _text(
        ar: 'اقتراح إجابة',
        en: 'Answer hint',
        fr: 'Indice de réponse',
        es: 'Pista de respuesta',
        de: 'Antwort-Hinweis',
        it: 'Suggerimento risposta',
        ja: '回答ヒント',
        ko: '답변 힌트',
        zh: '回答提示',
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
        ar: 'ترجمة',
        en: 'Translate',
        fr: 'Traduire',
        es: 'Traducir',
        de: 'Übersetzen',
        it: 'Traduci',
        ja: '翻訳',
        ko: '번역',
        zh: '翻译',
      );

  String _hideTranslationLabel() => _text(
        ar: 'إخفاء الترجمة',
        en: 'Hide translation',
        fr: 'Masquer la traduction',
        es: 'Ocultar traducción',
        de: 'Übersetzung ausblenden',
        it: 'Nascondi traduzione',
        ja: '翻訳を隠す',
        ko: '번역 숨기기',
        zh: '隐藏翻译',
      );

  String _translationErrorLabel() => _text(
        ar: 'تعذرت الترجمة. حاول مرة أخرى.',
        en: 'Translation failed. Please try again.',
        fr: 'La traduction a échoué. Réessayez.',
        es: 'La traducción falló. Inténtalo de nuevo.',
        de: 'Die Übersetzung ist fehlgeschlagen. Bitte erneut versuchen.',
        it: 'La traduzione non è riuscita. Riprova.',
        ja: '翻訳に失敗しました。もう一度お試してください。',
        ko: '번역에 실패했습니다. 다시 시도하세요.',
        zh: '翻译失败，请重试。',
      );

  String _finishLabel() => _text(
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

  String _finishQuestion() => _text(
        ar: 'هل أنهيت التعلم؟ سيبدأ اختبار الدرس بعد ذلك، ولن يُسجّل الدرس كمكتمل إلا بعد النجاح.',
        en: 'Ready to finish learning? The lesson assessment will start next, and the lesson is completed only after you pass it.',
        fr: 'Prêt à terminer ? L’évaluation commencera ensuite et la leçon ne sera validée qu’après réussite.',
        es: '¿Listo para terminar? Después comenzará la evaluación y la lección se completará al aprobarla.',
        de: 'Möchtest du die Lektion beenden? Danach startet der Test und die Lektion wird erst nach Bestehen abgeschlossen.',
        it: 'Vuoi terminare? Dopo inizierà la verifica e la lezione sarà completata solo dopo il superamento.',
        ja: '学習を終了しますか？次にテストが始まり、合格するとレッスンが完了します。',
        ko: '학습을 끝낼까요? 다음에 평가가 시작되며 통과해야 레슨이 완료됩니다.',
        zh: '要结束学习吗？接下来会开始测试，只有通过后课程才会完成。',
      );

  String _cancelLabel() => _text(
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

  String _confirmLabel() => _text(
        ar: 'بدء الاختبار',
        en: 'Start assessment',
        fr: 'Commencer l’évaluation',
        es: 'Iniciar evaluación',
        de: 'Test starten',
        it: 'Inizia verifica',
        ja: 'テスト開始',
        ko: '평가 시작',
        zh: '开始测试',
      );

  String _startingLabel() => _text(
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

  String _translationKey(_TutorMessage message) =>
      '${_locale()}:${message.role}:${message.text}';

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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_translationErrorLabel())),
      );
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

      await showLessonHintDialog(
        context,
        hint: hint,
        text: _text,
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_hintErrorLabel())),
      );
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
    await _sendMessage(message, showUserMessage: true);
  }

  Future<void> _sendMessage(
    String message, {
    required bool showUserMessage,
  }) async {
    if (_sending || _submitting) return;

    if (showUserMessage) {
      setState(() {
        _messages.add(_TutorMessage(role: 'user', text: message));
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
            if (text.isNotEmpty) {
              _messages.add(_TutorMessage(role: role, text: text));
            }
          }
          setState(() {
            _loading = false;
            _error = null;
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
            setState(() {});
            _scrollToBottom();
          }
        }

        if (chunk.type == 'done') {
          final id = chunk.conversationId;
          if (id != null && id.isNotEmpty) _conversationId = id;
          _dailyLimit = chunk.dailyLimit;
          _dailyRemaining = chunk.dailyRemaining;
        }

        if (chunk.type == 'error') {
          throw Exception(chunk.message ?? _errorLabel());
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString());
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_errorLabel())),
        );
      }
    }

    if (mounted) {
      setState(() {
        _sending = false;
        _loading = false;
      });
      _scrollToBottom();
    }
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

  String _cleanWordToken(String token) {
    return token.replaceAll(
      RegExp(
        r'^[\.,!?;:()\[\]{}"“”„«»…*_~`、。！？；：（）［］｛｝「」『』【】《》〈〉]+|[\.,!?;:()\[\]{}"“”„«»…*_~`、。！？；：（）［］｛｝「」『』【】《》〈〉]+$',
      ),
      '',
    );
  }

  bool _isWhitespaceRune(int rune) =>
      RegExp(r'\s').hasMatch(String.fromCharCode(rune));

  bool _isCjkPunctuationRune(int rune) =>
      RegExp(r'[\.,!?;:()\[\]{}"“”„«»…*_~`、。！？；：（）［］｛｝「」『』【】《》〈〉]').hasMatch(
        String.fromCharCode(rune),
      );

  bool _isCjkIdeographRune(int rune) {
    return (rune >= 0x3400 && rune <= 0x4DBF) ||
        (rune >= 0x4E00 && rune <= 0x9FFF) ||
        (rune >= 0xF900 && rune <= 0xFAFF) ||
        (rune >= 0x20000 && rune <= 0x2FA1F);
  }

  bool _isJapaneseKanaRune(int rune) {
    return (rune >= 0x3040 && rune <= 0x309F) ||
        (rune >= 0x30A0 && rune <= 0x30FF) ||
        (rune >= 0x31F0 && rune <= 0x31FF);
  }

  List<String> _messageTokens(String text) {
    final locale = _locale();
    if (locale != 'ja' && locale != 'zh') {
      return text.split(RegExp(r'(\s+)'));
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
        result.add(char);
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

    await showWordDetailDialog(
      context,
      word: word,
      languageCode: _locale(),
    );
  }

  Widget _buildClickableMessage(String text, ThemeData theme) {
    final tokens = _messageTokens(text);
    final baseStyle = theme.textTheme.bodyLarge?.copyWith(height: 1.45);

    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.end,
      children: [
        for (final token in tokens)
          if (token.trim().isEmpty)
            Text(token, style: baseStyle)
          else
            InkWell(
              borderRadius: BorderRadius.circular(5),
              onTap: () => _openWord(token),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 1, vertical: 1),
                child: Text(
                  token,
                  textDirection: _textDirection(token),
                  style: baseStyle,
                ),
              ),
            ),
      ],
    );
  }

  Widget _buildTranslationButton(_TutorMessage message, ThemeData theme) {
    final key = _translationKey(message);
    final cached = _translationCache.containsKey(key);
    final visible = _visibleTranslations.contains(key);
    final loading = _translationLoading.contains(key);

    return Align(
      alignment: message.isUser
          ? AlignmentDirectional.centerEnd
          : AlignmentDirectional.centerStart,
      child: Padding(
        padding: const EdgeInsetsDirectional.only(top: 2),
        child: TextButton.icon(
          onPressed: loading ? null : () => _toggleTranslation(message),
          icon: loading
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Icon(
                  cached && visible
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.translate_rounded,
                  size: 18,
                ),
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
      alignment: isUser
          ? AlignmentDirectional.centerEnd
          : AlignmentDirectional.centerStart,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 620),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(16, 12, 12, 8),
        decoration: BoxDecoration(
          color: isUser
              ? theme.colorScheme.primaryContainer
              : theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: isUser
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
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
                  child: Text(
                    translation,
                    textDirection: _textDirection(translation),
                    style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
                  ),
                ),
              ),
            _buildTranslationButton(message, theme),
          ],
        ),
      ),
    );
  }

  TextDirection _textDirection(String text) {
    return RegExp(r'[\u0600-\u06FF]').hasMatch(text)
        ? TextDirection.rtl
        : TextDirection.ltr;
  }

  Widget _buildComposer(ThemeData theme) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            IconButton(
              onPressed: _hintLoading || _sending || _submitting || _messages.isEmpty
                  ? null
                  : _showHint,
              tooltip: _hintLabel(),
              icon: _hintLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.lightbulb_outline_rounded),
            ),
            const SizedBox(width: 4),
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
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
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

  Future<void> _finishLesson() async {
    if (_submitting || _sending) return;

    final shouldStart = await showDialog<bool>(
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

    if (shouldStart != true || !mounted) return;

    setState(() {
      _submitting = true;
      _error = null;
    });

    final passed = await Navigator.of(context).push<bool>(
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

    setState(() => _submitting = false);

    if (passed == true) {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isRtl = _locale() == 'ar';

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Text(
          _pageTitle(),
          style: const TextStyle(fontWeight: FontWeight.w700),
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
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  ),
                                  const SizedBox(width: 10),
                                  Text(_startingLabel()),
                                ],
                              ),
                            ),
                          );
                        }

                        return _buildMessage(_messages[index], theme);
                      },
                    ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text(
                  _errorLabel(),
                  textAlign: TextAlign.center,
                  style: TextStyle(color: theme.colorScheme.error),
                ),
              ),
            _buildComposer(theme),
          ],
        ),
      ),
    );
  }
}
