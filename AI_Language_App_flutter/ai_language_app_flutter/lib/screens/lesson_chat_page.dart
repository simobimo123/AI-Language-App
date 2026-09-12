import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../core/language/lesson_chat_ui_text.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';
import '../services/lesson_chat_session_store.dart';

class LessonChatPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;
  final String stage;

  const LessonChatPage({
    super.key,
    required this.lesson,
    required this.languageController,
    required this.stage,
  }) : assert(stage == 'teaching' || stage == 'practice');

  bool get isTeaching => stage == 'teaching';

  @override
  State<LessonChatPage> createState() => _LessonChatPageState();
}

class _Message {
  final String role;
  final String text;

  const _Message({required this.role, required this.text});

  bool get isUser => role == 'user';
}

class _LessonChatPageState extends State<LessonChatPage> {
  final ApiService _api = ApiService();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final _focusNode = FocusNode();
  final List<_Message> _messages = [];
  final Map<int, String> _translations = {};
  final Map<String, Map<String, dynamic>> _wordDetails = {};

  /// Message indexes whose cached translation is currently hidden.
  ///
  /// IMPORTANT:
  /// This is only UI state. The actual translation remains in
  /// [_translations] and therefore remains available in the temporary
  /// session cache.
  final Set<int> _hiddenTranslationIndexes = <int>{};

  late final LessonChatStoredSession _session;

  String? _conversationId;
  String? _error;
  bool _starting = true;
  bool _sending = false;
  bool _completed = false;
  int? _translatingIndex;
  bool _suggesting = false;
  String? _suggestionText;
  String? _suggestionTranslation;
  bool _suggestionCollapsed = false;
  bool _isFocused = false;
  String? _selectedWordKey;
  String? _loadingWordKey;
  int? _wordCardMessageIndex;
  OverlayEntry? _wordActionOverlay;

  String _ui(String key) =>
      lessonChatUiText(widget.languageController.locale.languageCode, key);

  TextDirection get _learningDirection =>
      directionForLanguage(widget.lesson.language);

  String get _stageLabel =>
      widget.isTeaching ? _ui('stageTeaching') : _ui('stagePractice');

  String get _completionLabel =>
      widget.isTeaching ? _ui('continueStage3') : _ui('complete');

  String _wordUi(String key) {
    final language = widget.languageController.locale.languageCode
        .toLowerCase()
        .split('-')
        .first;

    const labels = <String, Map<String, String>>{
      'ar': {
        'explain': 'شرح',
        'partOfSpeech': 'نوع الكلمة',
        'pronunciation': 'النطق',
        'example': 'مثال',
        'exampleTranslation': 'ترجمة المثال',
        'loading': 'جاري إنشاء البطاقة...',
        'lookupError': 'تعذر شرح هذه الكلمة.',
      },
      'en': {
        'explain': 'Explain',
        'partOfSpeech': 'Part of speech',
        'pronunciation': 'Pronunciation',
        'example': 'Example',
        'exampleTranslation': 'Example translation',
        'loading': 'Creating the word card...',
        'lookupError': 'Could not explain this word.',
      },
      'fr': {
        'explain': 'Expliquer',
        'partOfSpeech': 'Nature du mot',
        'pronunciation': 'Prononciation',
        'example': 'Exemple',
        'exampleTranslation': "Traduction de l’exemple",
        'loading': 'Création de la fiche...',
        'lookupError': 'Impossible d’expliquer ce mot.',
      },
      'de': {
        'explain': 'Erklären',
        'partOfSpeech': 'Wortart',
        'pronunciation': 'Aussprache',
        'example': 'Beispiel',
        'exampleTranslation': 'Beispielübersetzung',
        'loading': 'Wortkarte wird erstellt...',
        'lookupError': 'Dieses Wort konnte nicht erklärt werden.',
      },
      'es': {
        'explain': 'Explicar',
        'partOfSpeech': 'Tipo de palabra',
        'pronunciation': 'Pronunciación',
        'example': 'Ejemplo',
        'exampleTranslation': 'Traducción del ejemplo',
        'loading': 'Creando la ficha...',
        'lookupError': 'No se pudo explicar esta palabra.',
      },
      'it': {
        'explain': 'Spiega',
        'partOfSpeech': 'Parte del discorso',
        'pronunciation': 'Pronuncia',
        'example': 'Esempio',
        'exampleTranslation': "Traduzione dell’esempio",
        'loading': 'Creazione della scheda...',
        'lookupError': 'Impossibile spiegare questo parola.',
      },
      'pt': {
        'explain': 'Explicar',
        'partOfSpeech': 'Classe gramatical',
        'pronunciation': 'Pronúncia',
        'example': 'Exemplo',
        'exampleTranslation': 'Tradução do exemplo',
        'loading': 'Criando o cartão...',
        'lookupError': 'Não foi possível explicar esta palavra.',
      },
      'tr': {
        'explain': 'Açıkla',
        'partOfSpeech': 'Sözcük türü',
        'pronunciation': 'Telaffuz',
        'example': 'Örnek',
        'exampleTranslation': 'Örnek çevirisi',
        'loading': 'Kelime kartı oluşturuluyor...',
        'lookupError': 'Bu kelime açıklanamadı.',
      },
      'nl': {
        'explain': 'Uitleg',
        'partOfSpeech': 'Woordsoort',
        'pronunciation': 'Uitspraak',
        'example': 'Voorbeeld',
        'exampleTranslation': 'Vertaling van voorbeeld',
        'loading': 'Woordkaart wordt gemaakt...',
        'lookupError': 'Dit woord kon niet worden uitgelegd.',
      },
      'pl': {
        'explain': 'Wyjaśnij',
        'partOfSpeech': 'Część mowy',
        'pronunciation': 'Wymowa',
        'example': 'Przykład',
        'exampleTranslation': 'Tłumaczenie przykładu',
        'loading': 'Tworzenie karty słowa...',
        'lookupError': 'Nie można wyjaśnić tego słowa.',
      },
      'ru': {
        'explain': 'Объяснить',
        'partOfSpeech': 'Часть речи',
        'pronunciation': 'Произношение',
        'example': 'Пример',
        'exampleTranslation': 'Перевод примера',
        'loading': 'Создание карточки...',
        'lookupError': 'Не удалось объяснить это слово.',
      },
      'uk': {
        'explain': 'Пояснити',
        'partOfSpeech': 'Частина мови',
        'pronunciation': 'Вимова',
        'example': 'Приклад',
        'exampleTranslation': 'Переклад прикладу',
        'loading': 'Створення картки слова...',
        'lookupError': 'Не вдалося пояснити це слово.',
      },
      'id': {
        'explain': 'Jelaskan',
        'partOfSpeech': 'Kelas kata',
        'pronunciation': 'Pengucapan',
        'example': 'Contoh',
        'exampleTranslation': 'Terjemahan contoh',
        'loading': 'Membuat kartu kata...',
        'lookupError': 'Kata ini tidak dapat dijelaskan.',
      },
      'ja': {
        'explain': '説明',
        'partOfSpeech': '品詞',
        'pronunciation': '発音',
        'example': '例文',
        'exampleTranslation': '例文の翻訳',
        'loading': '単語カードを作成中...',
        'lookupError': 'この単語を説明できませんでした。',
      },
      'ko': {
        'explain': '설명',
        'partOfSpeech': '품사',
        'pronunciation': '발음',
        'example': '예문',
        'exampleTranslation': '예문 번역',
        'loading': '단어 카드를 만드는 중...',
        'lookupError': '이 단어를 설명할 수 없습니다.',
      },
      'zh': {
        'explain': '解释',
        'partOfSpeech': '词性',
        'pronunciation': '发音',
        'example': '例句',
        'exampleTranslation': '例句翻译',
        'loading': '正在创建单词卡...',
        'lookupError': '无法解释这个词。',
      },
      'th': {
        'explain': 'อธิบาย',
        'partOfSpeech': 'ชนิดของคำ',
        'pronunciation': 'การออกเสียง',
        'example': 'ตัวอย่าง',
        'exampleTranslation': 'คำแปลตัวอย่าง',
        'loading': 'กำลังสร้างการ์ดคำศัพท์...',
        'lookupError': 'ไม่สามารถอธิบายคำนี้ได้',
      },
      'vi': {
        'explain': 'Giải thích',
        'partOfSpeech': 'Từ loại',
        'pronunciation': 'Phát âm',
        'example': 'Ví dụ',
        'exampleTranslation': 'Dịch ví dụ',
        'loading': 'Đang tạo thẻ từ...',
        'lookupError': 'Không thể giải thích từ này.',
      },
    };

    return labels[language]?[key] ?? labels['en']![key]!;
  }

  String _normalizeWord(String word) => word.trim().toLowerCase();

  @override
  void initState() {
    super.initState();

    _restoreSession();

    _focusNode.addListener(() {
      if (!mounted) return;
      setState(() => _isFocused = _focusNode.hasFocus);
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      if (_messages.isEmpty) {
        _send('START_STAGE', showUser: false);
      } else {
        setState(() => _starting = false);
        _scrollToEnd();
      }
    });
  }

  void _restoreSession() {
    _session = lessonChatSessionStore.getOrCreate(
      lessonId: widget.lesson.id,
      stage: widget.stage,
    );

    _conversationId = _session.conversationId;

    _messages
      ..clear()
      ..addAll(
        _session.messages.map(
          (message) => _Message(role: message.role, text: message.text),
        ),
      );

    _translations
      ..clear()
      ..addAll(_session.translations);

    _hiddenTranslationIndexes.clear();

    _completed = _session.completed;
    _starting = _messages.isEmpty;
  }

  void _saveSession() {
    _session.conversationId = _conversationId;

    _session.messages
      ..clear()
      ..addAll(
        _messages.map(
          (message) =>
              LessonChatStoredMessage(role: message.role, text: message.text),
        ),
      );

    _session.translations
      ..clear()
      ..addAll(_translations);

    _session.completed = _completed;

    lessonChatSessionStore.save(_session);
  }

  @override
  void dispose() {
    _removeWordActionOverlay();
    _input.dispose();
    _scroll.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _sendCurrent() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending || _completed) return;

    _input.clear();
    _clearSuggestion();

    await _send(text, showUser: true);
  }

  void _clearSuggestion() {
    if (_suggestionText == null && _suggestionTranslation == null) return;

    setState(() {
      _suggestionText = null;
      _suggestionTranslation = null;
      _suggestionCollapsed = false;
    });
  }

  Future<void> _send(String text, {required bool showUser}) async {
    if (_sending) return;

    if (showUser) {
      setState(() {
        _messages.add(_Message(role: 'user', text: text));
        _error = null;
      });

      _saveSession();
      _scrollToEnd();
    }

    setState(() {
      _sending = true;
      _starting = !showUser;
      _error = null;
    });

    _saveSession();

    var assistantIndex = -1;

    try {
      await for (final chunk in _api.lessonStageAiChat(
        lessonId: widget.lesson.id,
        stage: widget.stage,
        message: text,
        conversationId: _conversationId,
      )) {
        if (!mounted) return;

        if (chunk.conversationId != null && chunk.conversationId!.isNotEmpty) {
          _conversationId = chunk.conversationId;
          _saveSession();
        }

        if (chunk.type == 'token' || chunk.type == 'chunk') {
          final part = chunk.text ?? '';
          if (part.isEmpty) continue;

          if (assistantIndex == -1) {
            _messages.add(const _Message(role: 'assistant', text: ''));

            assistantIndex = _messages.length - 1;
          }

          final old = _messages[assistantIndex];

          _messages[assistantIndex] = _Message(
            role: old.role,
            text: old.text + part,
          );

          _saveSession();

          setState(() {
            _starting = false;
            _error = null;
          });

          _scrollToEnd();
        }

        if (chunk.type == 'done' && chunk.axisCompleted) {
          setState(() => _completed = true);
          _saveSession();
        }

        if (chunk.type == 'error') {
          setState(() {
            _error = chunk.message ?? _ui('connectionError');
          });

          _saveSession();
        }
      }
    } catch (_) {
      if (!mounted) return;

      setState(() => _error = _ui('sendError'));
      _saveSession();
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
          _starting = false;
        });

        _saveSession();
      }
    }
  }

  Future<void> _translateMessage(int index) async {
    final cachedTranslation = _translations[index];

    // The translation is already in the temporary cache.
    // Re-opening it must NEVER call the API or AI.
    if (cachedTranslation != null && cachedTranslation.trim().isNotEmpty) {
      setState(() {
        _hiddenTranslationIndexes.remove(index);
        _error = null;
      });

      _saveSession();
      _scrollToEnd();
      return;
    }

    final text = _messages[index].text.trim();

    if (text.isEmpty || _translatingIndex != null || _sending) return;

    setState(() {
      _translatingIndex = index;
      _error = null;
    });

    try {
      final translation = await _api.translateText(text: text);

      if (!mounted) return;

      setState(() {
        _translations[index] = translation;
        _hiddenTranslationIndexes.remove(index);
      });

      _saveSession();
      _scrollToEnd();
    } catch (_) {
      if (!mounted) return;

      setState(() => _error = _ui('translationError'));
    } finally {
      if (mounted) {
        setState(() => _translatingIndex = null);
      }
    }
  }

  void _deleteTranslation(int index) {
    if (!_translations.containsKey(index)) return;

    setState(() {
      // Deliberately DO NOT remove the translation from [_translations].
      // The translation stays in RAM cache and can be restored instantly.
      _hiddenTranslationIndexes.add(index);
    });

    _saveSession();
  }

  Future<void> _suggestReply() async {
    if (_conversationId == null || _suggesting || _sending || _completed) {
      return;
    }

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

      setState(() {
        _suggestionText = hint.suggestion;
        _suggestionTranslation = hint.translation;
        _suggestionCollapsed = false;
      });

      _scrollToEnd();
    } catch (_) {
      if (!mounted) return;

      setState(() => _error = _ui('suggestionError'));
    } finally {
      if (mounted) {
        setState(() => _suggesting = false);
      }
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;

      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
      );
    });
  }

  void _removeWordActionOverlay() {
    _wordActionOverlay?.remove();
    _wordActionOverlay = null;
  }

  void _showWordAction({
    required String word,
    required Offset globalPosition,
    required int messageIndex,
  }) {
    _removeWordActionOverlay();

    final key = _normalizeWord(word);
    if (key.isEmpty) return;

    setState(() {
      _selectedWordKey = key;
      _wordCardMessageIndex = messageIndex;
    });

    final overlay = Overlay.of(context);
    final size = MediaQuery.of(context).size;

    const popupWidth = 112.0;
    const popupHeight = 46.0;

    final left = (globalPosition.dx - popupWidth / 2).clamp(
      12.0,
      size.width - popupWidth - 12.0,
    );

    final top = (globalPosition.dy - popupHeight - 10).clamp(
      MediaQuery.of(context).padding.top + 8,
      size.height - popupHeight - 12,
    );

    _wordActionOverlay = OverlayEntry(
      builder: (context) => Positioned(
        left: left,
        top: top,
        width: popupWidth,
        height: popupHeight,
        child: Material(
          color: Colors.transparent,
          child: Center(
            child: Material(
              color: Theme.of(context).colorScheme.inverseSurface,
              borderRadius: BorderRadius.circular(14),
              elevation: 8,
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () {
                  _removeWordActionOverlay();
                  _lookupWord(word, messageIndex);
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 11,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.menu_book_rounded,
                        size: 17,
                        color: Theme.of(context).colorScheme.onInverseSurface,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _wordUi('explain'),
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onInverseSurface,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    overlay.insert(_wordActionOverlay!);
  }

  Future<void> _lookupWord(String word, int messageIndex) async {
    final cleanWord = word.trim();
    final key = _normalizeWord(cleanWord);

    if (key.isEmpty) return;

    setState(() {
      _selectedWordKey = key;
      _wordCardMessageIndex = messageIndex;
      _error = null;
    });

    final cached = _wordDetails[key];

    if (cached != null) {
      _scrollToEnd();
      return;
    }

    setState(() => _loadingWordKey = key);

    try {
      final result = await _api.lookupWord(word: cleanWord);

      if (!mounted) return;

      setState(() {
        _wordDetails[key] = result;
        _selectedWordKey = key;
        _wordCardMessageIndex = messageIndex;
      });

      _scrollToEnd();
    } catch (_) {
      if (!mounted) return;

      setState(() => _error = _wordUi('lookupError'));
    } finally {
      if (mounted) {
        setState(() => _loadingWordKey = null);
      }
    }
  }

  String _plainMessageText(String text) => text.replaceAll('**', '');

  String? _wordAtOffset({
    required String text,
    required TextStyle style,
    required TextDirection direction,
    required double maxWidth,
    required Offset localPosition,
  }) {
    final displayText = _plainMessageText(text);

    if (displayText.trim().isEmpty) return null;

    final painter = TextPainter(
      text: TextSpan(text: displayText, style: style),
      textDirection: direction,
      textAlign: TextAlign.start,
      maxLines: null,
    )..layout(maxWidth: maxWidth);

    final position = painter.getPositionForOffset(localPosition);
    final offset = position.offset.clamp(0, displayText.length);

    var start = offset;

    while (start > 0 && !RegExp(r'\s').hasMatch(displayText[start - 1])) {
      start--;
    }

    var end = offset;

    while (end < displayText.length &&
        !RegExp(r'\s').hasMatch(displayText[end])) {
      end++;
    }

    if (start >= end) return null;

    final raw = displayText.substring(start, end);

    final word = raw.replaceAll(
      RegExp(r'^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$', unicode: true),
      '',
    );

    if (word.isEmpty || word.length > 80) return null;

    return word;
  }

  Widget _buildClickableMessageText(
    BuildContext context, {
    required String text,
    required TextStyle style,
    required TextDirection direction,
    required bool isUser,
    required int messageIndex,
  }) {
    final displayText = _plainMessageText(text);
    final maxWidth = MediaQuery.of(context).size.width * 0.8 - 36;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapUp: isUser
          ? null
          : (details) {
              final word = _wordAtOffset(
                text: text,
                style: style,
                direction: direction,
                maxWidth: maxWidth,
                localPosition: details.localPosition,
              );

              if (word == null) return;

              _showWordAction(
                word: word,
                globalPosition: (context.findRenderObject() as RenderBox)
                    .localToGlobal(details.localPosition),
                messageIndex: messageIndex,
              );
            },
      child: Text(displayText, textDirection: direction, style: style),
    );
  }

  Widget _buildWordCard(BuildContext context, int messageIndex) {
    final theme = Theme.of(context);
    final key = _selectedWordKey;

    if (key == null || _wordCardMessageIndex != messageIndex) {
      return const SizedBox.shrink();
    }

    final data = _wordDetails[key];
    final loading = _loadingWordKey == key;

    if (data == null && !loading) {
      return const SizedBox.shrink();
    }

    String value(String field) => (data?[field] ?? '').toString().trim();

    final word = value('word').isNotEmpty ? value('word') : key;
    final translation = value('translation');
    final partOfSpeech = value('part_of_speech');
    final pronunciation = value('pronunciation');
    final example = value('example_sentence');
    final exampleTranslation = value('example_translation');

    return AnimatedSize(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOutCubic,
      child: Container(
        margin: const EdgeInsets.only(top: 10),
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: theme.colorScheme.primaryContainer.withValues(alpha: 0.45),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: theme.colorScheme.primary.withValues(alpha: 0.16),
          ),
        ),
        child: loading
            ? Row(
                children: [
                  SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.3,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _wordUi('loading'),
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: theme.colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Directionality(
                          textDirection: _learningDirection,
                          child: Text(
                            word,
                            style: theme.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w900,
                              color: theme.colorScheme.onPrimaryContainer,
                            ),
                          ),
                        ),
                      ),
                      InkWell(
                        borderRadius: BorderRadius.circular(20),
                        onTap: () => setState(() {
                          _selectedWordKey = null;
                          _wordCardMessageIndex = null;
                        }),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
                          child: Icon(
                            Icons.close_rounded,
                            size: 19,
                            color: theme.colorScheme.onPrimaryContainer
                                .withValues(alpha: 0.65),
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (translation.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _wordInfoRow(
                      context,
                      icon: Icons.translate_rounded,
                      value: translation,
                      strong: true,
                      direction: directionForText(translation),
                    ),
                  ],
                  if (partOfSpeech.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _wordInfoRow(
                      context,
                      icon: Icons.category_outlined,
                      label: _wordUi('partOfSpeech'),
                      value: partOfSpeech,
                      direction: directionForText(
                        partOfSpeech,
                        fallback: _learningDirection,
                      ),
                    ),
                  ],
                  if (pronunciation.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _wordInfoRow(
                      context,
                      icon: Icons.record_voice_over_outlined,
                      label: _wordUi('pronunciation'),
                      value: pronunciation,
                      direction: TextDirection.ltr,
                    ),
                  ],
                  if (example.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _wordSection(
                      context,
                      label: _wordUi('example'),
                      value: example,
                      direction: _learningDirection,
                    ),
                  ],
                  if (exampleTranslation.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _wordSection(
                      context,
                      label: _wordUi('exampleTranslation'),
                      value: exampleTranslation,
                      direction: directionForText(exampleTranslation),
                    ),
                  ],
                ],
              ),
      ),
    );
  }

  Widget _wordInfoRow(
    BuildContext context, {
    required IconData icon,
    required String value,
    required TextDirection direction,
    String? label,
    bool strong = false,
  }) {
    final theme = Theme.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 17, color: theme.colorScheme.primary),
        const SizedBox(width: 8),
        if (label != null) ...[
          Text(
            '$label: ',
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w800,
              color: theme.colorScheme.onPrimaryContainer.withValues(
                alpha: 0.7,
              ),
            ),
          ),
        ],
        Expanded(
          child: Directionality(
            textDirection: direction,
            child: Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: strong ? FontWeight.w800 : FontWeight.w600,
                color: theme.colorScheme.onPrimaryContainer,
                height: 1.4,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _wordSection(
    BuildContext context, {
    required String label,
    required String value,
    required TextDirection direction,
  }) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.labelMedium?.copyWith(
              fontWeight: FontWeight.w800,
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 5),
          Directionality(
            textDirection: direction,
            child: Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageActions(BuildContext context, int index) {
    final theme = Theme.of(context);
    final translation = _translations[index];
    final hasTranslation =
        translation != null && translation.trim().isNotEmpty;
    final translationHidden = _hiddenTranslationIndexes.contains(index);
    final translating = _translatingIndex == index;

    return Padding(
      padding: const EdgeInsetsDirectional.only(top: 8, start: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!hasTranslation || translationHidden)
            Material(
              color: theme.colorScheme.surfaceContainerHighest.withValues(
                alpha: 0.4,
              ),
              borderRadius: BorderRadius.circular(12),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: translating || _sending
                    ? null
                    : () => _translateMessage(index),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (translating)
                        SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: theme.colorScheme.primary,
                          ),
                        )
                      else
                        Icon(
                          Icons.translate_rounded,
                          size: 14,
                          color: theme.colorScheme.primary.withValues(
                            alpha: 0.9,
                          ),
                        ),
                      const SizedBox(width: 6),
                      Text(
                        _ui('translate'),
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          if (hasTranslation && !translationHidden)
            Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer.withValues(
                  alpha: 0.4,
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: theme.colorScheme.primary.withValues(alpha: 0.1),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.g_translate_rounded,
                    size: 16,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Directionality(
                      textDirection: directionForText(translation),
                      child: Text(
                        translation,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          height: 1.5,
                        ),
                      ),
                    ),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(
                      minWidth: 28,
                      minHeight: 28,
                    ),
                    tooltip: 'Delete',
                    onPressed: () => _deleteTranslation(index),
                    icon: const Icon(
                      Icons.delete_outline_rounded,
                      size: 18,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildMessage(BuildContext context, int index) {
    final theme = Theme.of(context);
    final message = _messages[index];
    final isUser = message.isUser;

    final bubbleColor = isUser
        ? theme.colorScheme.primary
        : theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5);

    final foregroundColor = isUser
        ? theme.colorScheme.onPrimary
        : theme.colorScheme.onSurface;

    final messageDirection = isUser
        ? directionForText(message.text, fallback: _learningDirection)
        : _learningDirection;

    final textStyle = theme.textTheme.bodyLarge!.copyWith(
      color: foregroundColor,
      height: 1.5,
      letterSpacing: 0.2,
    );

    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(24),
      topRight: const Radius.circular(24),
      bottomLeft: Radius.circular(isUser ? 24 : 4),
      bottomRight: Radius.circular(isUser ? 4 : 24),
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        mainAxisAlignment: isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser)
            Container(
              width: 34,
              height: 34,
              margin: const EdgeInsetsDirectional.only(end: 10),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    theme.colorScheme.primary,
                    theme.colorScheme.primary.withValues(alpha: 0.7),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.smart_toy_rounded,
                size: 18,
                color: theme.colorScheme.onPrimary,
              ),
            ),
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.8,
              ),
              child: Column(
                crossAxisAlignment: isUser
                    ? CrossAxisAlignment.end
                    : CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 18,
                      vertical: 14,
                    ),
                    decoration: BoxDecoration(
                      color: bubbleColor,
                      borderRadius: borderRadius,
                    ),
                    child: Directionality(
                      textDirection: messageDirection,
                      child: _buildClickableMessageText(
                        context,
                        text: message.text,
                        style: textStyle,
                        direction: messageDirection,
                        isUser: isUser,
                        messageIndex: index,
                      ),
                    ),
                  ),
                  if (!isUser) ...[
                    _buildMessageActions(context, index),
                    _buildWordCard(context, index),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSuggestionPanel(BuildContext context) {
    final theme = Theme.of(context);
    final hasSuggestion =
        _suggestionText != null && _suggestionText!.trim().isNotEmpty;

    return AnimatedSize(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
      child: hasSuggestion
          ? Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 250),
                child: _suggestionCollapsed
                    ? _buildCollapsedSuggestion(theme)
                    : _buildExpandedSuggestion(theme),
              ),
            )
          : const SizedBox.shrink(),
    );
  }

  Widget _buildCollapsedSuggestion(ThemeData theme) {
    return Material(
      key: const ValueKey('collapsed'),
      color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.5),
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => setState(() => _suggestionCollapsed = false),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: [
              Icon(
                Icons.lightbulb_rounded,
                size: 20,
                color: theme.colorScheme.secondary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _ui('replySuggestion'),
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.onSecondaryContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              IconButton(
                onPressed: () => setState(() => _suggestionCollapsed = false),
                icon: const Icon(Icons.keyboard_arrow_up_rounded),
                iconSize: 20,
              ),
              IconButton(
                onPressed: _clearSuggestion,
                icon: const Icon(Icons.close_rounded),
                iconSize: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildExpandedSuggestion(ThemeData theme) {
    return Container(
      key: const ValueKey('expanded'),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: theme.colorScheme.secondary.withValues(alpha: 0.15),
        ),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.lightbulb_rounded,
                size: 20,
                color: theme.colorScheme.secondary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _ui('replySuggestion'),
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              IconButton(
                onPressed: () => setState(() => _suggestionCollapsed = true),
                icon: const Icon(Icons.keyboard_arrow_down_rounded),
                iconSize: 20,
              ),
              IconButton(
                onPressed: _clearSuggestion,
                icon: const Icon(Icons.close_rounded),
                iconSize: 20,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Directionality(
            textDirection: _learningDirection,
            child: Text(
              _suggestionText!,
              style: theme.textTheme.bodyLarge?.copyWith(height: 1.5),
            ),
          ),
          if (_suggestionTranslation != null &&
              _suggestionTranslation!.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Directionality(
              textDirection: directionForText(_suggestionTranslation!),
              child: Text(
                _suggestionTranslation!,
                style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildComposer(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 12,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest.withValues(
                  alpha: 0.4,
                ),
                borderRadius: BorderRadius.circular(28),
                border: Border.all(
                  color: theme.colorScheme.outline.withValues(alpha: 0.1),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      focusNode: _focusNode,
                      enabled: !_sending && !_completed,
                      minLines: 1,
                      maxLines: 5,
                      textDirection: _learningDirection,
                      textInputAction: TextInputAction.newline,
                      style: theme.textTheme.bodyLarge,
                      decoration: InputDecoration(
                        hintText: (!_isFocused && _input.text.isEmpty)
                            ? 'اضغط هنا للكتابة'
                            : null,
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 14,
                        ),
                      ),
                      onChanged: (_) => setState(() {}),
                      onSubmitted: (_) => _sendCurrent(),
                    ),
                  ),
                  IconButton(
                    onPressed: _sending || _completed ? null : _suggestReply,
                    icon: _suggesting
                        ? SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: theme.colorScheme.primary,
                            ),
                          )
                        : Icon(
                            Icons.lightbulb_outline_rounded,
                            color: theme.colorScheme.primary,
                          ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 10),
          CircleAvatar(
            radius: 25,
            backgroundColor: _sending || _completed
                ? theme.colorScheme.surfaceContainerHighest
                : theme.colorScheme.primary,
            child: IconButton(
              onPressed: _sending || _completed ? null : _sendCurrent,
              icon: _sending
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    )
                  : Icon(
                      Icons.send_rounded,
                      color: theme.colorScheme.onPrimary,
                      size: 20,
                    ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.colorScheme.surface,
      appBar: AppBar(
        title: Text(
          _stageLabel,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 18,
            letterSpacing: 0.5,
          ),
        ),
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 4,
        backgroundColor: theme.colorScheme.surface.withValues(alpha: 0.9),
        surfaceTintColor: Colors.transparent,
      ),
      body: Column(
        children: [
          Expanded(
            child: _starting && _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(
                          color: theme.colorScheme.primary,
                          strokeWidth: 3,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'جاري بدء المحادثة...',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 24,
                    ),
                    itemCount: _messages.length,
                    itemBuilder: _buildMessage,
                  ),
          ),
          if (_error != null)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.error_outline_rounded,
                    color: theme.colorScheme.error,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_error!)),
                ],
              ),
            ),
          if (_completed)
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    onPressed: () => Navigator.pop(context, true),
                    icon: Icon(
                      widget.isTeaching
                          ? Icons.arrow_forward_rounded
                          : Icons.check_rounded,
                    ),
                    label: Text(
                      _completionLabel,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ),
            )
          else
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildSuggestionPanel(context),
                _buildComposer(context),
              ],
            ),
        ],
      ),
    );
  }
}
