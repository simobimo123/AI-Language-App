import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../core/language/lesson_chat_ui_text.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';
import '../services/lesson_chat_session_store.dart';
import '../services/tts_player_service.dart';
import '../widgets/words/word_detail_dialog.dart';

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

  const _Message({
    required this.role,
    required this.text,
  });

  bool get isUser => role == 'user';
}

class _LessonChatPageState extends State<LessonChatPage> {
  final ApiService _api = ApiService();
  final TtsPlayerService _ttsPlayer = TtsPlayerService();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final _focusNode = FocusNode();

  final List<_Message> _messages = [];
  final Map<int, String> _translations = {};
  final Set<int> _hiddenTranslationIndexes = <int>{};

  late final LessonChatStoredSession _session;

  String? _conversationId;
  String? _error;

  bool _starting = true;
  bool _sending = false;
  bool _completed = false;

  int? _translatingIndex;
  int? _speakingIndex;

  bool _suggesting = false;
  String? _suggestionText;
  String? _suggestionTranslation;
  bool _suggestionCollapsed = false;

  bool _isFocused = false;

  String _ui(String key) {
    return lessonChatUiText(
      widget.languageController.locale.languageCode,
      key,
    );
  }

  TextDirection get _learningDirection {
    return directionForLanguage(widget.lesson.language);
  }

  String get _stageLabel {
    return widget.isTeaching
        ? _ui('stageTeaching')
        : _ui('stagePractice');
  }

  String get _completionLabel {
    return widget.isTeaching
        ? _ui('continueStage3')
        : _ui('complete');
  }

  bool get _hasLearnerMessage {
    return _messages.any((message) => message.isUser);
  }

  String _cleanWordToken(String token) {
    return token.replaceAll(
      RegExp(
        r'^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$',
        unicode: true,
      ),
      '',
    );
  }

  Future<void> _showWordDetails(String word) async {
    final cleanWord = _cleanWordToken(word).trim();

    if (cleanWord.isEmpty || cleanWord.length > 80) {
      return;
    }

    final languageCode = widget.languageController.locale.languageCode
        .toLowerCase()
        .split('-')
        .first;

    await showWordDetailDialog(
      context,
      word: cleanWord,
      languageCode: languageCode,
    );
  }

  TextSpan _buildClickableWordSpan(
    String token,
    TextStyle style,
  ) {
    final word = _cleanWordToken(token);
    final isWord = word.isNotEmpty && word.length <= 80;

    if (!isWord) {
      return TextSpan(
        text: token,
        style: style,
      );
    }

    return TextSpan(
      text: token,
      style: style,
      recognizer: TapGestureRecognizer()
        ..onTap = () {
          _showWordDetails(word);
        },
    );
  }

  TextSpan _buildNormalTextSpan({
    required String text,
    required TextStyle style,
  }) {
    final spans = <InlineSpan>[];

    final matches = RegExp(r'(\s+)').allMatches(text);

    int lastEnd = 0;

    for (final match in matches) {
      if (match.start > lastEnd) {
        final wordToken = text.substring(
          lastEnd,
          match.start,
        );

        spans.add(
          _buildClickableWordSpan(
            wordToken,
            style,
          ),
        );
      }

      spans.add(
        TextSpan(
          text: text.substring(
            match.start,
            match.end,
          ),
          style: style,
        ),
      );

      lastEnd = match.end;
    }

    if (lastEnd < text.length) {
      spans.add(
        _buildClickableWordSpan(
          text.substring(lastEnd),
          style,
        ),
      );
    }

    return TextSpan(
      children: spans,
      style: style,
    );
  }

  TextSpan _buildColoredTextSpan({
    required String text,
    required TextStyle style,
  }) {
    final spans = <InlineSpan>[];

    final matches = RegExp(r'(\s+)').allMatches(text);

    int lastEnd = 0;

    for (final match in matches) {
      if (match.start > lastEnd) {
        final wordToken = text.substring(
          lastEnd,
          match.start,
        );

        spans.add(
          _buildClickableWordSpan(
            wordToken,
            style,
          ),
        );
      }

      spans.add(
        TextSpan(
          text: text.substring(
            match.start,
            match.end,
          ),
          style: style,
        ),
      );

      lastEnd = match.end;
    }

    if (lastEnd < text.length) {
      spans.add(
        _buildClickableWordSpan(
          text.substring(lastEnd),
          style,
        ),
      );
    }

    return TextSpan(
      children: spans,
      style: style,
    );
  }

  TextSpan _buildFormattedMessageSpan({
    required String text,
    required TextStyle style,
  }) {
    final spans = <InlineSpan>[];

    int index = 0;

    while (index < text.length) {
      final current = text[index];

      if (current == '*' &&
          index + 1 < text.length &&
          text[index + 1] == '*') {
        final closingIndex = text.indexOf(
          '**',
          index + 2,
        );

        if (closingIndex != -1) {
          final content = text.substring(
            index + 2,
            closingIndex,
          );

          if (content.isNotEmpty) {
            spans.add(
              _buildNormalTextSpan(
                text: content,
                style: style,
              ),
            );
          }

          index = closingIndex + 2;
          continue;
        }
      }

      if (current == '"') {
        final closingIndex = text.indexOf(
          '"',
          index + 1,
        );

        if (closingIndex != -1) {
          final content = text.substring(
            index + 1,
            closingIndex,
          );

          if (content.isNotEmpty) {
            spans.add(
              _buildColoredTextSpan(
                text: content,
                style: style.copyWith(
                  color: Colors.red,
                ),
              ),
            );
          }

          index = closingIndex + 1;
          continue;
        }
      }

      if (current == '*' &&
          (index == 0 || text[index - 1] != '*')) {
        final closingIndex = text.indexOf(
          '*',
          index + 1,
        );

        if (closingIndex != -1 &&
            closingIndex > index + 1 &&
            (closingIndex + 1 >= text.length ||
                text[closingIndex + 1] != '*')) {
          final content = text.substring(
            index + 1,
            closingIndex,
          );

          if (content.isNotEmpty) {
            spans.add(
              _buildColoredTextSpan(
                text: content,
                style: style.copyWith(
                  color: Colors.green,
                ),
              ),
            );
          }

          index = closingIndex + 1;
          continue;
        }
      }

      int nextMarker = text.length;

      final doubleQuoteIndex = text.indexOf(
        '"',
        index,
      );

      final boldIndex = text.indexOf(
        '**',
        index,
      );

      final singleStarIndex = _findSingleStarMarker(
        text,
        index,
      );

      if (doubleQuoteIndex != -1 &&
          doubleQuoteIndex < nextMarker) {
        nextMarker = doubleQuoteIndex;
      }

      if (boldIndex != -1 &&
          boldIndex < nextMarker) {
        nextMarker = boldIndex;
      }

      if (singleStarIndex != -1 &&
          singleStarIndex < nextMarker) {
        nextMarker = singleStarIndex;
      }

      if (nextMarker == index) {
        spans.add(
          TextSpan(
            text: current,
            style: style,
          ),
        );

        index++;
        continue;
      }

      final normalText = text.substring(
        index,
        nextMarker,
      );

      if (normalText.isNotEmpty) {
        spans.add(
          _buildNormalTextSpan(
            text: normalText,
            style: style,
          ),
        );
      }

      index = nextMarker;
    }

    return TextSpan(
      children: spans,
      style: style,
    );
  }

  int _findSingleStarMarker(
    String text,
    int start,
  ) {
    for (int i = start; i < text.length; i++) {
      if (text[i] != '*') {
        continue;
      }

      final isDoubleStarBefore =
          i + 1 < text.length && text[i + 1] == '*';

      final isDoubleStarAfter =
          i > 0 && text[i - 1] == '*';

      if (!isDoubleStarBefore && !isDoubleStarAfter) {
        return i;
      }
    }

    return -1;
  }

  Widget _buildClickableMessageText(
    BuildContext context, {
    required String text,
    required TextStyle style,
    required TextDirection direction,
    required bool isUser,
    required int messageIndex,
  }) {
    if (text.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    final TextSpan messageSpan;

    if (isUser) {
      messageSpan = TextSpan(
        text: text.replaceAll('**', ''),
        style: style,
      );
    } else {
      messageSpan = _buildFormattedMessageSpan(
        text: text,
        style: style,
      );
    }

    return SelectableText.rich(
      messageSpan,
      textDirection: direction,
      style: style,
      enableInteractiveSelection: true,
      showCursor: false,
      cursorWidth: 0,
      selectionColor: Theme.of(context)
          .colorScheme
          .primary
          .withValues(alpha: 0.22),
      selectionControls: materialTextSelectionControls,
      textAlign: TextAlign.start,
    );
  }

  @override
  void initState() {
    super.initState();

    _restoreSession();

    _focusNode.addListener(() {
      if (!mounted) {
        return;
      }

      setState(() {
        _isFocused = _focusNode.hasFocus;
      });
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }

      if (_messages.isEmpty) {
        _send(
          'START_STAGE',
          showUser: false,
        );
      } else {
        setState(() {
          _starting = false;
        });

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
          (message) => _Message(
            role: message.role,
            text: message.text,
          ),
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
          (message) => LessonChatStoredMessage(
            role: message.role,
            text: message.text,
          ),
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
    _ttsPlayer.dispose();
    _input.dispose();
    _scroll.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _speakMessage(int index) async {
    if (index < 0 || index >= _messages.length) {
      return;
    }

    final text = _messages[index].text.trim();
    if (text.isEmpty) {
      return;
    }

    if (_speakingIndex == index) {
      await _ttsPlayer.stop();
      if (mounted) {
        setState(() {
          _speakingIndex = null;
        });
      }
      return;
    }

    if (_speakingIndex != null) {
      await _ttsPlayer.stop();
    }

    setState(() {
      _speakingIndex = index;
      _error = null;
    });

    try {
      final audio = await _api.synthesizeSpeech(
        text: text,
      );

      if (!mounted) {
        return;
      }

      await _ttsPlayer.play(audio);
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = 'TTS: $error';
      });
    } finally {
      if (mounted && _speakingIndex == index) {
        setState(() {
          _speakingIndex = null;
        });
      }
    }
  }

  Future<void> _sendCurrent() async {
    final text = _input.text.trim();

    if (text.isEmpty || _sending || _completed) {
      return;
    }

    _input.clear();
    _clearSuggestion();

    await _send(
      text,
      showUser: true,
    );
  }

  void _clearSuggestion() {
    if (_suggestionText == null &&
        _suggestionTranslation == null) {
      return;
    }

    setState(() {
      _suggestionText = null;
      _suggestionTranslation = null;
      _suggestionCollapsed = false;
    });
  }

  Future<void> _send(
    String text, {
    required bool showUser,
  }) async {
    if (_sending) {
      return;
    }

    if (showUser) {
      setState(() {
        _messages.add(
          _Message(
            role: 'user',
            text: text,
          ),
        );

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
        if (!mounted) {
          return;
        }

        if (chunk.conversationId != null &&
            chunk.conversationId!.isNotEmpty) {
          _conversationId = chunk.conversationId;
          _saveSession();
        }

        if (chunk.type == 'token' || chunk.type == 'chunk') {
          final part = chunk.text ?? '';

          if (part.isEmpty) {
            continue;
          }

          if (assistantIndex == -1) {
            _messages.add(
              const _Message(
                role: 'assistant',
                text: '',
              ),
            );

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
          if (widget.isTeaching) {
            setState(() {
              _completed = true;
            });

            _saveSession();
          }
        }

        if (chunk.type == 'error') {
          setState(() {
            _error = chunk.message ?? _ui('connectionError');
          });

          _saveSession();
        }
      }
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = _ui('sendError');
      });

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

  Future<void> _finishPractice() async {
    if (widget.isTeaching ||
        !_hasLearnerMessage ||
        _conversationId == null ||
        _sending ||
        _completed) {
      return;
    }

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

      if (!mounted) {
        return;
      }

      setState(() {
        _sending = false;
        _completed = true;
      });

      _saveSession();
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _sending = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _translateMessage(int index) async {
    final cachedTranslation = _translations[index];

    if (cachedTranslation != null &&
        cachedTranslation.trim().isNotEmpty) {
      setState(() {
        _hiddenTranslationIndexes.remove(index);
        _error = null;
      });

      _saveSession();
      _scrollToEnd();

      return;
    }

    final text = _messages[index].text.trim();

    if (text.isEmpty ||
        _translatingIndex != null ||
        _sending) {
      return;
    }

    setState(() {
      _translatingIndex = index;
      _error = null;
    });

    try {
      final translation = await _api.translateText(
        text: text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _translations[index] = translation;
        _hiddenTranslationIndexes.remove(index);
      });

      _saveSession();
      _scrollToEnd();
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = _ui('translationError');
      });
    } finally {
      if (mounted) {
        setState(() {
          _translatingIndex = null;
        });
      }
    }
  }

  void _deleteTranslation(int index) {
    if (!_translations.containsKey(index)) {
      return;
    }

    setState(() {
      _hiddenTranslationIndexes.add(index);
    });

    _saveSession();
  }

  Future<void> _suggestReply() async {
    if (_conversationId == null ||
        _suggesting ||
        _sending ||
        _completed) {
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

      if (!mounted) {
        return;
      }

      setState(() {
        _suggestionText = hint.suggestion;
        _suggestionTranslation = hint.translation;
        _suggestionCollapsed = false;
      });

      _scrollToEnd();
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = _ui('suggestionError');
      });
    } finally {
      if (mounted) {
        setState(() {
          _suggesting = false;
        });
      }
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) {
        return;
      }

      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
      );
    });
  }

  Widget _buildMessageActions(
    BuildContext context,
    int index,
  ) {
    final theme = Theme.of(context);
    final translation = _translations[index];

    final hasTranslation =
        translation != null &&
        translation.trim().isNotEmpty;

    final translationHidden =
        _hiddenTranslationIndexes.contains(index);

    final translating = _translatingIndex == index;
    final speaking = _speakingIndex == index;

    return Padding(
      padding: const EdgeInsetsDirectional.only(
        top: 8,
        start: 8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Material(
                color: theme
                    .colorScheme
                    .surfaceContainerHighest
                    .withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(12),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: _sending
                      ? null
                      : () => _speakMessage(index),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    child: speaking
                        ? SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: theme.colorScheme.primary,
                            ),
                          )
                        : Icon(
                            Icons.volume_up_rounded,
                            size: 16,
                            color: theme.colorScheme.primary
                                .withValues(alpha: 0.9),
                          ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (!hasTranslation || translationHidden)
                Material(
                  color: theme
                      .colorScheme
                      .surfaceContainerHighest
                      .withValues(alpha: 0.4),
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
                              color: theme.colorScheme.primary
                                  .withValues(alpha: 0.9),
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
            ],
          ),
          if (hasTranslation && !translationHidden)
            Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer
                    .withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: theme.colorScheme.primary
                      .withValues(alpha: 0.1),
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
                      textDirection:
                          directionForText(translation),
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
                    onPressed: () =>
                        _deleteTranslation(index),
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

  Widget _buildMessage(
    BuildContext context,
    int index,
  ) {
    final theme = Theme.of(context);
    final message = _messages[index];

    final isUser = message.isUser;

    final bubbleColor = isUser
        ? theme.colorScheme.primary
        : theme.colorScheme.surfaceContainerHighest
            .withValues(alpha: 0.5);

    final foregroundColor = isUser
        ? theme.colorScheme.onPrimary
        : theme.colorScheme.onSurface;

    final messageDirection = isUser
        ? directionForText(
            message.text,
            fallback: _learningDirection,
          )
        : _learningDirection;

    final textStyle = theme.textTheme.bodyLarge!.copyWith(
      color: foregroundColor,
      height: 1.5,
      letterSpacing: 0.2,
    );

    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(24),
      topRight: const Radius.circular(24),
      bottomLeft: Radius.circular(
        isUser ? 24 : 4,
      ),
      bottomRight: Radius.circular(
        isUser ? 4 : 24,
      ),
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
              margin: const EdgeInsetsDirectional.only(
                end: 10,
              ),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    theme.colorScheme.primary,
                    theme.colorScheme.primary
                        .withValues(alpha: 0.7),
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
                maxWidth:
                    MediaQuery.of(context).size.width * 0.8,
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
                  if (!isUser)
                    _buildMessageActions(
                      context,
                      index,
                    ),
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
        _suggestionText != null &&
        _suggestionText!.trim().isNotEmpty;

    return AnimatedSize(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
      child: hasSuggestion
          ? Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 8,
              ),
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

  Widget _buildCollapsedSuggestion(
    ThemeData theme,
  ) {
    return Material(
      key: const ValueKey('collapsed'),
      color: theme.colorScheme.secondaryContainer
          .withValues(alpha: 0.5),
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          setState(() {
            _suggestionCollapsed = false;
          });
        },
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 12,
          ),
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
                onPressed: () {
                  setState(() {
                    _suggestionCollapsed = false;
                  });
                },
                icon: const Icon(
                  Icons.keyboard_arrow_up_rounded,
                ),
                iconSize: 20,
              ),
              IconButton(
                onPressed: _clearSuggestion,
                icon: const Icon(
                  Icons.close_rounded,
                ),
                iconSize: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildExpandedSuggestion(
    ThemeData theme,
  ) {
    return Container(
      key: const ValueKey('expanded'),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer
            .withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: theme.colorScheme.secondary
              .withValues(alpha: 0.15),
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
                onPressed: () {
                  setState(() {
                    _suggestionCollapsed = true;
                  });
                },
                icon: const Icon(
                  Icons.keyboard_arrow_down_rounded,
                ),
                iconSize: 20,
              ),
              IconButton(
                onPressed: _clearSuggestion,
                icon: const Icon(
                  Icons.close_rounded,
                ),
                iconSize: 20,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Directionality(
            textDirection: _learningDirection,
            child: Text(
              _suggestionText!,
              style: theme.textTheme.bodyLarge?.copyWith(
                height: 1.5,
              ),
            ),
          ),
          if (_suggestionTranslation != null &&
              _suggestionTranslation!.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Directionality(
              textDirection:
                  directionForText(_suggestionTranslation!),
              child: Text(
                _suggestionTranslation!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  height: 1.4,
                ),
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
                color: theme.colorScheme.surfaceContainerHighest
                    .withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(28),
                border: Border.all(
                  color: theme.colorScheme.outline
                      .withValues(alpha: 0.1),
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
                      textInputAction:
                          TextInputAction.newline,
                      style: theme.textTheme.bodyLarge,
                      decoration: InputDecoration(
                        hintText:
                            (!_isFocused &&
                                    _input.text.isEmpty)
                                ? 'اضغط هنا للكتابة'
                                : null,
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding:
                            const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 14,
                        ),
                      ),
                      onChanged: (_) {
                        setState(() {});
                      },
                      onSubmitted: (_) {
                        _sendCurrent();
                      },
                    ),
                  ),
                  IconButton(
                    onPressed:
                        _sending || _completed
                            ? null
                            : _suggestReply,
                    icon: _suggesting
                        ? SizedBox(
                            width: 20,
                            height: 20,
                            child:
                                CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color:
                                  theme.colorScheme.primary,
                            ),
                          )
                        : Icon(
                            Icons.lightbulb_outline_rounded,
                            color:
                                theme.colorScheme.primary,
                          ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 10),
          CircleAvatar(
            radius: 25,
            backgroundColor:
                _sending || _completed
                    ? theme.colorScheme
                        .surfaceContainerHighest
                    : theme.colorScheme.primary,
            child: IconButton(
              onPressed:
                  _sending || _completed
                      ? null
                      : _sendCurrent,
              icon: _sending
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color:
                            theme.colorScheme.onSurfaceVariant,
                      ),
                    )
                  : Icon(
                      Icons.send_rounded,
                      color:
                          theme.colorScheme.onPrimary,
                      size: 20,
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context) {
    if (_error == null) {
      return const SizedBox.shrink();
    }

    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 8,
      ),
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
          Expanded(
            child: Text(_error!),
          ),
        ],
      ),
    );
  }

  Widget _buildCompletedButton(BuildContext context) {
    if (!_completed) {
      return const SizedBox.shrink();
    }

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(
                vertical: 16,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
              ),
            ),
            onPressed: () {
              Navigator.pop(context, true);
            },
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
    );
  }

  Widget _buildPracticeFinishButton(BuildContext context) {
    if (widget.isTeaching || !_hasLearnerMessage) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        16,
        4,
        16,
        4,
      ),
      child: SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed:
              _sending || _conversationId == null
                  ? null
                  : _finishPractice,
          icon: const Icon(
            Icons.check_circle_outline_rounded,
          ),
          label: Text(_ui('complete')),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final showLoading =
        _starting && _messages.isEmpty;

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
        backgroundColor:
            theme.colorScheme.surface.withValues(
          alpha: 0.9,
        ),
        surfaceTintColor: Colors.transparent,
      ),
      body: Column(
        children: [
          Expanded(
            child: showLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment:
                          MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(
                          color:
                              theme.colorScheme.primary,
                          strokeWidth: 3,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'جاري بدء المحادثة...',
                          style: theme.textTheme.bodyMedium
                              ?.copyWith(
                            color: theme.colorScheme
                                .onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding:
                        const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 24,
                    ),
                    itemCount: _messages.length,
                    itemBuilder: _buildMessage,
                  ),
          ),
          _buildError(context),
          if (_completed)
            _buildCompletedButton(context)
          else
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildPracticeFinishButton(context),
                _buildSuggestionPanel(context),
                _buildComposer(context),
              ],
            ),
        ],
      ),
    );
  }
}
