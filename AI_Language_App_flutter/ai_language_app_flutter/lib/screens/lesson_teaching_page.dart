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
        stage: 'teaching',
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
            _error = chunk.message ??
                _t('تعذر الاتصال بالمدرّس الذكي.',
                    'Could not reach the AI tutor.');
          });
        }
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = _t(
          'تعذر إرسال الرسالة. حاول مرة أخرى.',
          'Could not send the message. Please try again.',
        );
      });
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
      setState(() {
        _error = _t('تعذر ترجمة الرسالة.', 'Could not translate the message.');
      });
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
      setState(() {
        _error = _t(
          'تعذر إنشاء اقتراح للرد.',
          'Could not generate a reply suggestion.',
        );
      });
    } finally {
      if (mounted) setState(() => _suggesting = false);
    }
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
                        : Icon(Icons.translate_rounded,
                            size: 16, color: theme.colorScheme.primary),
                    const SizedBox(width: 6),
                    Text(
                      _t('ترجمة', 'Translate'),
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
                Icon(Icons.translate_rounded,
                    size: 17, color: theme.colorScheme.onPrimaryContainer),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    translation,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onPrimaryContainer,
                      height: 1.4,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: _t('إخفاء الترجمة', 'Hide translation'),
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                  onPressed: () => setState(() => _translations.remove(index)),
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
                Icon(Icons.lightbulb_outline_rounded,
                    size: 19, color: theme.colorScheme.onSecondaryContainer),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _t('اقتراح رد', 'Reply suggestion'),
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: theme.colorScheme.onSecondaryContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: _t('إظهار الاقتراح', 'Show suggestion'),
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  onPressed: () => setState(() => _suggestionCollapsed = false),
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
                      color: theme.colorScheme.onSecondaryContainer.withValues(alpha: .08),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.lightbulb_rounded,
                        size: 19, color: theme.colorScheme.onSecondaryContainer),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _t('اقتراح للرد', 'Suggested reply'),
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: theme.colorScheme.onSecondaryContainer,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: _t('إخفاء الاقتراح', 'Hide suggestion'),
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    onPressed: () => setState(() => _suggestionCollapsed = true),
                    icon: const Icon(Icons.keyboard_arrow_down_rounded),
                  ),
                  IconButton(
                    tooltip: _t('إزالة الاقتراح', 'Remove suggestion'),
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    onPressed: _clearSuggestion,
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                _suggestionText!,
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSecondaryContainer,
                  height: 1.45,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (_suggestionTranslation != null &&
                  _suggestionTranslation!.trim().isNotEmpty) ...[
                const SizedBox(height: 7),
                Text(
                  _suggestionTranslation!,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSecondaryContainer.withValues(alpha: .78),
                    height: 1.35,
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
                child: Icon(Icons.auto_awesome_rounded,
                    size: 18, color: theme.colorScheme.onPrimaryContainer),
              ),
            ],
            Flexible(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 650),
                child: Container(
                  padding: const EdgeInsets.fromLTRB(15, 12, 15, 11),
                  decoration: BoxDecoration(
                    color: bubbleColor,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(20),
                      topRight: const Radius.circular(20),
                      bottomLeft: Radius.circular(isUser ? 20 : 5),
                      bottomRight: Radius.circular(isUser ? 5 : 20),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: .04),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        message.text,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          color: foregroundColor,
                          height: 1.5,
                        ),
                      ),
                      if (!isUser && message.text.trim().isNotEmpty)
                        _messageActions(context, index),
                    ],
                  ),
                ),
              ),
            ),
            if (isUser)
              Container(
                width: 34,
                height: 34,
                margin: const EdgeInsetsDirectional.only(start: 8),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.person_rounded,
                    size: 18, color: theme.colorScheme.onPrimaryContainer),
              ),
          ],
        ),
      ),
    );
  }

  Widget _typingIndicator(BuildContext context) {
    final theme = Theme.of(context);
    return Align(
      alignment: AlignmentDirectional.centerStart,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Container(
              width: 34,
              height: 34,
              margin: const EdgeInsetsDirectional.only(end: 8),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.auto_awesome_rounded,
                  size: 18, color: theme.colorScheme.onPrimaryContainer),
            ),
            _AnimatedTypingBubble(
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
              dotColor: theme.colorScheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildComposer(BuildContext context) {
    final theme = Theme.of(context);
    final canSuggest = _conversationId != null &&
        !_suggesting && !_sending && !_completed;

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 5, 12, 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Tooltip(
              message: _t('اقتراح رد مناسب', 'Suggest a suitable reply'),
              child: Material(
                color: theme.colorScheme.secondaryContainer,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16)),
                child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: canSuggest ? _suggestReply : null,
                  child: SizedBox(
                    width: 50,
                    height: 50,
                    child: Center(
                      child: _suggesting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Icon(Icons.lightbulb_outline_rounded,
                              color: canSuggest
                                  ? theme.colorScheme.onSecondaryContainer
                                  : theme.colorScheme.onSurfaceVariant),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: _input,
                enabled: !_sending && !_completed,
                minLines: 1,
                maxLines: 5,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _sendCurrent(),
                decoration: InputDecoration(
                  hintText: _t('اكتب إجابتك...', 'Write your answer...'),
                  filled: true,
                  fillColor: theme.colorScheme.surfaceContainerHighest,
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 17, vertical: 14),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(18),
                    borderSide: BorderSide.none,
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(18),
                    borderSide: BorderSide(
                        color: theme.colorScheme.outline.withValues(alpha: .08)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(18),
                    borderSide: BorderSide(
                        color: theme.colorScheme.primary, width: 1.4),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              tooltip: _t('إرسال', 'Send'),
              onPressed: _sending || _completed ? null : _sendCurrent,
              style: IconButton.styleFrom(
                minimumSize: const Size(50, 50),
                maximumSize: const Size(50, 50),
              ),
              icon: const Icon(Icons.arrow_upward_rounded),
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final showTyping = _sending &&
        !_starting &&
        !_completed &&
        (_messages.isEmpty || _messages.last.isUser);

    return Scaffold(
      appBar: AppBar(
        elevation: 0,
        titleSpacing: 0,
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
        title: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.auto_awesome_rounded,
                  size: 20, color: theme.colorScheme.onPrimaryContainer),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_t('المدرّس الذكي', 'AI Tutor'),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text(
                    _t('المرحلة 2 · التعليم', 'Stage 2 · Teaching'),
                    style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          if (_completed)
            Padding(
              padding: const EdgeInsetsDirectional.only(end: 10),
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.check_circle_rounded,
                          size: 16, color: theme.colorScheme.onPrimaryContainer),
                      const SizedBox(width: 5),
                      Text(_t('مكتملة', 'Complete'),
                          style: theme.textTheme.labelMedium?.copyWith(
                              color: theme.colorScheme.onPrimaryContainer,
                              fontWeight: FontWeight.w700)),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _starting && _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 58,
                          height: 58,
                          decoration: BoxDecoration(
                            color: theme.colorScheme.primaryContainer,
                            shape: BoxShape.circle,
                          ),
                          child: const Padding(
                            padding: EdgeInsets.all(18),
                            child: CircularProgressIndicator(strokeWidth: 2.4),
                          ),
                        ),
                        const SizedBox(height: 14),
                        Text(
                          _t('جاري بدء المحادثة...', 'Starting the conversation...'),
                          style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(14, 18, 14, 10),
                    itemCount: _messages.length + (showTyping ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (showTyping && index == _messages.length) {
                        return _typingIndicator(context);
                      }
                      return _buildMessage(context, index);
                    },
                  ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 6),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onErrorContainer),
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
                    icon: const Icon(Icons.arrow_forward_rounded),
                    label: Text(_t('فتح المرحلة 3', 'Continue to stage 3')),
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

class _AnimatedTypingBubble extends StatefulWidget {
  final Color backgroundColor;
  final Color dotColor;

  const _AnimatedTypingBubble({
    required this.backgroundColor,
    required this.dotColor,
  });

  @override
  State<_AnimatedTypingBubble> createState() => _AnimatedTypingBubbleState();
}

class _AnimatedTypingBubbleState extends State<_AnimatedTypingBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  double _valueForDot(int index) {
    final phase = (_controller.value - index * 0.18) % 1.0;
    return phase < 0.5 ? phase * 2 : (1.0 - phase) * 2;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 17, vertical: 13),
      decoration: BoxDecoration(
        color: widget.backgroundColor,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomRight: Radius.circular(20),
          bottomLeft: Radius.circular(5),
        ),
      ),
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return SizedBox(
            width: 34,
            height: 12,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: List.generate(3, (index) {
                final value = _valueForDot(index);
                return Transform.translate(
                  offset: Offset(0, -3 * value),
                  child: Opacity(
                    opacity: 0.35 + 0.65 * value,
                    child: Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: widget.dotColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              }),
            ),
          );
        },
      ),
    );
  }
}
