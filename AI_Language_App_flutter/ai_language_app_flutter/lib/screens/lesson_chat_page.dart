import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../core/language/lesson_chat_ui_text.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';

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
  final List<_Message> _messages = [];
  final Map<int, String> _translations = {};

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

  String _ui(String key) => lessonChatUiText(
        widget.languageController.locale.languageCode,
        key,
      );

  TextDirection get _learningDirection =>
      directionForLanguage(widget.lesson.language);

  String get _stageLabel =>
      widget.isTeaching ? _ui('stageTeaching') : _ui('stagePractice');

  String get _completionLabel =>
      widget.isTeaching ? _ui('continueStage3') : _ui('complete');

  Widget get _completionIcon => Icon(
        widget.isTeaching ? Icons.arrow_forward_rounded : Icons.check_rounded,
      );

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
        stage: widget.stage,
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
            _messages.add(const _Message(role: 'assistant', text: ''));
            assistantIndex = _messages.length - 1;
          }

          final old = _messages[assistantIndex];
          _messages[assistantIndex] =
              _Message(role: old.role, text: old.text + part);

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
          setState(() {
            _error = chunk.message ?? _ui('connectionError');
          });
        }
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _ui('sendError'));
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
          _starting = false;
        });
      }
    }
  }

  Future<void> _translateMessage(int index) async {
    final text = _messages[index].text.trim();
    if (text.isEmpty || _translatingIndex != null || _sending) return;

    setState(() {
      _translatingIndex = index;
      _error = null;
    });

    try {
      final translation = await _api.translateText(text: text);
      if (!mounted) return;
      setState(() => _translations[index] = translation);
      _scrollToEnd();
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _ui('translationError'));
    } finally {
      if (mounted) setState(() => _translatingIndex = null);
    }
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
      if (mounted) setState(() => _suggesting = false);
    }
  }

  InlineSpan _messageSpan(
    String text,
    TextStyle baseStyle,
    Color highlightColor,
  ) {
    final pattern = RegExp(r'\*\*(.+?)\*\*', dotAll: true);
    final matches = pattern.allMatches(text);
    if (matches.isEmpty) {
      return TextSpan(text: text, style: baseStyle);
    }

    final spans = <InlineSpan>[];
    var cursor = 0;
    for (final match in matches) {
      if (match.start > cursor) {
        spans.add(TextSpan(
          text: text.substring(cursor, match.start),
          style: baseStyle,
        ));
      }
      spans.add(TextSpan(
        text: match.group(1),
        style: baseStyle.copyWith(
          color: highlightColor,
          fontWeight: FontWeight.w700,
        ),
      ));
      cursor = match.end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(
        text: text.substring(cursor),
        style: baseStyle,
      ));
    }
    return TextSpan(children: spans);
  }

  Widget _messageActions(BuildContext context, int index) {
    final theme = Theme.of(context);
    final translation = _translations[index];
    final translating = _translatingIndex == index;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 10),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: translating || _sending
                  ? null
                  : () => _translateMessage(index),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    translating
                        ? const SizedBox(
                            width: 15,
                            height: 15,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(
                            Icons.translate_rounded,
                            size: 16,
                            color: theme.colorScheme.primary,
                          ),
                    const SizedBox(width: 6),
                    Text(
                      _ui('translate'),
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: theme.colorScheme.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (translation != null)
          Container(
            margin: const EdgeInsets.only(top: 4),
            padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer.withValues(alpha: .55),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: theme.colorScheme.primary.withValues(alpha: .12),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.translate_rounded,
                  size: 17,
                  color: theme.colorScheme.onPrimaryContainer,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Directionality(
                    textDirection: directionForText(translation),
                    child: Text(
                      translation,
                      textAlign: TextAlign.start,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
                IconButton(
                  tooltip: _ui('hideTranslation'),
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  constraints:
                      const BoxConstraints(minWidth: 30, minHeight: 30),
                  onPressed: () =>
                      setState(() => _translations.remove(index)),
                  icon: const Icon(Icons.keyboard_arrow_up_rounded, size: 21),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _suggestionPanel(BuildContext context) {
    if (_suggestionText == null) return const SizedBox.shrink();
    final theme = Theme.of(context);

    if (_suggestionCollapsed) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
        child: Material(
          color: theme.colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
            child: Row(
              children: [
                Icon(
                  Icons.lightbulb_outline_rounded,
                  size: 19,
                  color: theme.colorScheme.onSecondaryContainer,
                ),
                const SizedBox(width: 8),
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
                  tooltip: _ui('showSuggestion'),
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  onPressed: () =>
                      setState(() => _suggestionCollapsed = false),
                  icon: const Icon(Icons.keyboard_arrow_up_rounded),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 6),
      child: Material(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(15, 12, 9, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: theme.colorScheme.onSecondaryContainer
                          .withValues(alpha: .08),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.lightbulb_rounded,
                      size: 19,
                      color: theme.colorScheme.onSecondaryContainer,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _ui('replySuggestion'),
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: theme.colorScheme.onSecondaryContainer,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: _ui('hideSuggestion'),
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    onPressed: () =>
                        setState(() => _suggestionCollapsed = true),
                    icon: const Icon(Icons.keyboard_arrow_down_rounded),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Directionality(
                textDirection: _learningDirection,
                child: Text(
                  _suggestionText!,
                  textAlign: TextAlign.start,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.onSecondaryContainer,
                    height: 1.45,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (_suggestionTranslation != null &&
                  _suggestionTranslation!.trim().isNotEmpty) ...[
                const SizedBox(height: 7),
                Directionality(
                  textDirection: directionForText(_suggestionTranslation!),
                  child: Text(
                    _suggestionTranslation!,
                    textAlign: TextAlign.start,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSecondaryContainer
                          .withValues(alpha: .78),
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessage(BuildContext context, int index) {
    final theme = Theme.of(context);
    final message = _messages[index];
    final isUser = message.isUser;
    final bubbleColor = isUser
        ? theme.colorScheme.primary
        : theme.colorScheme.surfaceContainerHighest;
    final foregroundColor = isUser
        ? theme.colorScheme.onPrimary
        : theme.colorScheme.onSurface;
    final messageDirection = isUser
        ? directionForText(message.text, fallback: _learningDirection)
        : _learningDirection;
    final baseTextStyle = theme.textTheme.bodyLarge?.copyWith(
          color: foregroundColor,
          height: 1.5,
        ) ??
        TextStyle(color: foregroundColor, height: 1.5);

    return Align(
      alignment: isUser
          ? AlignmentDirectional.centerEnd
          : AlignmentDirectional.centerStart,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Row(
          mainAxisAlignment:
              isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (!isUser) ...[
              Container(
                width: 34,
                height: 34,
                margin: const EdgeInsetsDirectional.only(end: 8),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.auto_awesome_rounded,
                  size: 18,
                  color: theme.colorScheme.onPrimaryContainer,
                ),
              ),
            ],
            Flexible(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: Column(
                  crossAxisAlignment: isUser
                      ? CrossAxisAlignment.end
                      : CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 15,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: bubbleColor,
                        borderRadius: BorderRadius.only(
                          topLeft: const Radius.circular(20),
                          topRight: const Radius.circular(20),
                          bottomLeft: Radius.circular(isUser ? 20 : 6),
                          bottomRight: Radius.circular(isUser ? 6 : 20),
                        ),
                      ),
                      child: Directionality(
                        textDirection: messageDirection,
                        child: RichText(
                          textAlign: TextAlign.start,
                          text: _messageSpan(
                            message.text,
                            baseTextStyle,
                            isUser
                                ? theme.colorScheme.onPrimary
                                : theme.colorScheme.primary,
                          ),
                        ),
                      ),
                    ),
                    if (!isUser) _messageActions(context, index),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
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

  Widget _buildComposer(BuildContext context) {
    final theme = Theme.of(context);

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
        child: Material(
          color: theme.colorScheme.surface,
          elevation: 4,
          borderRadius: BorderRadius.circular(22),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 7, 7, 7),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    enabled: !_sending && !_completed,
                    minLines: 1,
                    maxLines: 5,
                    textDirection: _learningDirection,
                    textInputAction: TextInputAction.newline,
                    decoration: InputDecoration(
                      hintText: _ui('inputHint'),
                      border: InputBorder.none,
                    ),
                    onSubmitted: (_) => _sendCurrent(),
                  ),
                ),
                const SizedBox(width: 5),
                IconButton.filled(
                  onPressed: _sending || _completed ? null : _sendCurrent,
                  icon: _sending
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.arrow_upward_rounded),
                  tooltip: _ui('send'),
                ),
                IconButton(
                  onPressed: _sending || _completed ? null : _suggestReply,
                  icon: _suggesting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.lightbulb_outline_rounded),
                  tooltip: _ui('suggest'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(_stageLabel),
      ),
      body: Column(
        children: [
          Expanded(
            child: _starting && _messages.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(14, 18, 14, 12),
                    itemCount: _messages.length,
                    itemBuilder: _buildMessage,
                  ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 6),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onErrorContainer,
                  ),
                ),
              ),
            ),
          if (_completed)
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 6, 14, 14),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => Navigator.pop(context, true),
                    icon: _completionIcon,
                    label: Text(_completionLabel),
                  ),
                ),
              ),
            )
          else
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _suggestionPanel(context),
                _buildComposer(context),
              ],
            ),
        ],
      ),
    );
  }
}
