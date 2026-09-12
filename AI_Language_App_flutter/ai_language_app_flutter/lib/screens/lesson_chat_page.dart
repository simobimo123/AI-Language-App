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

  bool _isFocused = false;
  final FocusNode _focusNode = FocusNode();

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

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(() {
      setState(() {
        _isFocused = _focusNode.hasFocus;
      });
    });
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _send('START_STAGE', showUser: false));
  }

  @override
  void dispose() {
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

  InlineSpan _messageSpan(String text, TextStyle baseStyle, Color highlightColor) {
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
      final highlightedText = match.group(1);
      if (highlightedText != null) {
        spans.add(TextSpan(
          text: highlightedText,
          style: baseStyle.copyWith(
            color: highlightColor,
            fontWeight: FontWeight.w800,
          ),
        ));
      }
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

  Widget _buildMessageActions(BuildContext context, int index) {
    final theme = Theme.of(context);
    final translation = _translations[index];
    final translating = _translatingIndex == index;

    return Padding(
      padding: const EdgeInsetsDirectional.only(top: 8, start: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Material(
            color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(12),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: translating || _sending ? null : () => _translateMessage(index),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
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
                        color: theme.colorScheme.primary.withValues(alpha: 0.9),
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
          if (translation != null)
            AnimatedOpacity(
              opacity: 1.0,
              duration: const Duration(milliseconds: 300),
              child: Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer.withValues(alpha: 0.4),
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
                            color: theme.colorScheme.onSurface,
                            height: 1.5,
                          ),
                        ),
                      ),
                    ),
                    InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => setState(() => _translations.remove(index)),
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surface.withValues(alpha: 0.5),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.close_rounded,
                          size: 14,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                ),
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

    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(24),
      topRight: const Radius.circular(24),
      bottomLeft: Radius.circular(isUser ? 24 : 4),
      bottomRight: Radius.circular(isUser ? 4 : 24),
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
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
                boxShadow: [
                  BoxShadow(
                    color: theme.colorScheme.primary.withValues(alpha: 0.2),
                    blurRadius: 8,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Icon(
                Icons.smart_toy_rounded,
                size: 18,
                color: theme.colorScheme.onPrimary,
              ),
            ),
          ],
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.8,
              ),
              child: Column(
                crossAxisAlignment:
                    isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 18,
                      vertical: 14,
                    ),
                    decoration: BoxDecoration(
                      color: bubbleColor,
                      borderRadius: borderRadius,
                      boxShadow: [
                        if (isUser)
                          BoxShadow(
                            color: theme.colorScheme.primary.withValues(alpha: 0.15),
                            blurRadius: 8,
                            offset: const Offset(0, 3),
                          )
                        else
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.02),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                      ],
                    ),
                    child: Directionality(
                      textDirection: messageDirection,
                      child: RichText(
                        textAlign: TextAlign.start,
                        text: _messageSpan(
                          message.text,
                          theme.textTheme.bodyLarge!.copyWith(
                            color: foregroundColor,
                            height: 1.5,
                            letterSpacing: 0.2,
                          ),
                          isUser
                              ? theme.colorScheme.onPrimaryContainer
                              : theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ),
                  if (!isUser) _buildMessageActions(context, index),
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
    final hasSuggestion = _suggestionText != null && _suggestionText!.trim().isNotEmpty;

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
              // زر الإظهار (السهم) يأتي أولاً
              _buildIconButton(
                icon: Icons.keyboard_arrow_up_rounded,
                onPressed: () => setState(() => _suggestionCollapsed = false),
                theme: theme,
              ),
              const SizedBox(width: 4),
              // زر الإزالة (X) أصبح في أقصى اليسار
              _buildIconButton(
                icon: Icons.close_rounded,
                onPressed: _clearSuggestion,
                theme: theme,
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
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: theme.colorScheme.secondary.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.lightbulb_rounded,
                  size: 16,
                  color: theme.colorScheme.secondary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _ui('replySuggestion'),
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.colorScheme.onSecondaryContainer,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.3,
                  ),
                ),
              ),
              // زر الإخفاء (سهم للأسفل) يأتي أولاً
              _buildIconButton(
                icon: Icons.keyboard_arrow_down_rounded,
                onPressed: () => setState(() => _suggestionCollapsed = true),
                theme: theme,
              ),
              const SizedBox(width: 4),
              // زر الإزالة (X) أصبح في أقصى اليسار
              _buildIconButton(
                icon: Icons.close_rounded,
                onPressed: _clearSuggestion,
                theme: theme,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Directionality(
            textDirection: _learningDirection,
            child: Text(
              _suggestionText!,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
                height: 1.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (_suggestionTranslation != null &&
              _suggestionTranslation!.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.only(top: 8),
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(
                    color: theme.colorScheme.secondary.withValues(alpha: 0.1),
                  ),
                ),
              ),
              child: Directionality(
                textDirection: directionForText(_suggestionTranslation!),
                child: Text(
                  _suggestionTranslation!,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSecondaryContainer.withValues(alpha: 0.8),
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildIconButton({
    required IconData icon,
    required VoidCallback onPressed,
    required ThemeData theme,
  }) {
    return Material(
      color: Colors.transparent,
      shape: const CircleBorder(),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Icon(
            icon,
            size: 20,
            color: theme.colorScheme.onSecondaryContainer.withValues(alpha: 0.7),
          ),
        ),
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
                color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
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
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: theme.colorScheme.onSurface,
                      ),
                      decoration: InputDecoration(
                        hintText: (!_isFocused && _input.text.isEmpty) ? "اضغط هنا للكتابة" : null,
                        hintStyle: TextStyle(
                          color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
                        ),
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 14,
                        ),
                      ),
                      onChanged: (text) {
                        setState(() {});
                      },
                      onSubmitted: (_) => _sendCurrent(),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4, right: 4, left: 4),
                    child: IconButton(
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
                      tooltip: _ui('suggest'),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 10),
          Padding(
            padding: const EdgeInsets.only(bottom: 2),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeInOut,
              decoration: BoxDecoration(
                color: _sending || _completed
                    ? theme.colorScheme.surfaceContainerHighest
                    : theme.colorScheme.primary,
                shape: BoxShape.circle,
                boxShadow: _sending || _completed
                    ? []
                    : [
                        BoxShadow(
                          color: theme.colorScheme.primary.withValues(alpha: 0.3),
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
              ),
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
                tooltip: _ui('send'),
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
        shadowColor: Colors.black.withValues(alpha: 0.1),
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
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
                    itemCount: _messages.length,
                    itemBuilder: _buildMessage,
                  ),
          ),
          if (_error != null)
            AnimatedSize(
              duration: const Duration(milliseconds: 300),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline_rounded, color: theme.colorScheme.error, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onErrorContainer,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
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
                      elevation: 2,
                    ),
                    onPressed: () => Navigator.pop(context, true),
                    icon: Icon(
                      widget.isTeaching ? Icons.arrow_forward_rounded : Icons.check_rounded,
                    ),
                    label: Text(
                      _completionLabel,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
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