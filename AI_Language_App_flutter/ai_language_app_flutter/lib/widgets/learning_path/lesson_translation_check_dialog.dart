import 'package:flutter/material.dart';

import '../../services/api/api_service.dart';
import 'lesson_review_dialog.dart';

Future<bool> showLessonTranslationCheckDialog({
  required BuildContext context,
  required ApiService apiService,
  required int lessonId,
  required String conversationId,
  required String Function({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? it,
    String? ja,
    String? ko,
    String? zh,
  }) text,
}) async {
  final wantsReview = await showLessonReviewChoice(
    context: context,
    text: text,
  );

  if (wantsReview) {
    await showLessonQuickReview(
      context: context,
      apiService: apiService,
      lessonId: lessonId,
      conversationId: conversationId,
      text: text,
    );
  }

  if (!context.mounted) return false;

  return await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (_) => _LessonTranslationCheckDialog(
          apiService: apiService,
          lessonId: lessonId,
          conversationId: conversationId,
          text: text,
        ),
      ) ??
      false;
}

class _LessonTranslationCheckDialog extends StatefulWidget {
  final ApiService apiService;
  final int lessonId;
  final String conversationId;
  final String Function({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? it,
    String? ja,
    String? ko,
    String? zh,
  }) text;

  const _LessonTranslationCheckDialog({
    required this.apiService,
    required this.lessonId,
    required this.conversationId,
    required this.text,
  });

  @override
  State<_LessonTranslationCheckDialog> createState() =>
      _LessonTranslationCheckDialogState();
}

class _LessonTranslationCheckDialogState
    extends State<_LessonTranslationCheckDialog> {
  final TextEditingController _controller = TextEditingController();
  List<Map<String, dynamic>> _questions = [];
  int _index = 0;
  bool _loading = true;
  bool _submitting = false;
  String? _error;
  final Map<String, String> _answers = {};

  String _label(String ar, String en) => widget.text(ar: ar, en: en);

  @override
  void initState() {
    super.initState();
    _loadQuestions();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _loadQuestions() async {
    try {
      final data = await widget.apiService.getLessonTranslationCheck(
        lessonId: widget.lessonId,
        conversationId: widget.conversationId,
      );
      final raw = data['questions'];
      final questions = raw is List
          ? raw.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).where((item) => item['sentence']?.toString().trim().isNotEmpty == true).toList()
          : <Map<String, dynamic>>[];

      if (questions.isEmpty) {
        throw Exception('No translation questions available.');
      }

      if (!mounted) return;
      setState(() {
        _questions = questions;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = _label(
          'تعذر تحميل تمرين الترجمة. حاول مرة أخرى.',
          'Could not load the translation check. Please try again.',
        );
      });
    }
  }

  void _next() {
    final answer = _controller.text.trim();
    if (answer.isEmpty || _submitting || _questions.isEmpty) return;

    final id = _questions[_index]['id'].toString();
    _answers[id] = answer;

    if (_index < _questions.length - 1) {
      setState(() {
        _index++;
        _controller.text = _answers[_questions[_index]['id'].toString()] ?? '';
        _error = null;
      });
      return;
    }

    _submit();
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final result = await widget.apiService.submitLessonTranslationCheck(
        lessonId: widget.lessonId,
        conversationId: widget.conversationId,
        answers: _questions
            .map(
              (question) => {
                'question_id': question['id'].toString(),
                'answer': _answers[question['id'].toString()] ?? '',
              },
            )
            .toList(),
      );

      if (!mounted) return;

      if (result.passed) {
        Navigator.of(context).pop(true);
        return;
      }

      setState(() {
        _submitting = false;
        _error = _label(
          'لم تصل بعد إلى النتيجة المطلوبة. راجع الجمل التي تعلمتها ثم حاول مرة أخرى.',
          'You have not reached the required score yet. Review the learned sentences and try again.',
        );
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = _label(
          'تعذر تقييم إجاباتك. حاول مرة أخرى.',
          'Your answers could not be evaluated. Please try again.',
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: Text(
        _label('التحقق من التعلم', 'Learning check'),
      ),
      content: SizedBox(
        width: 560,
        child: _loading
            ? const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            : _error != null && _questions.isEmpty
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Text(_error!, textAlign: TextAlign.center),
                  )
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        _label(
                          'ترجم الجملة إلى لغتك الأم:',
                          'Translate the sentence into your native language:',
                        ),
                        style: theme.textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 14),
                      Text(
                        _questions[_index]['sentence'].toString(),
                        textAlign: TextAlign.center,
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 18),
                      TextField(
                        controller: _controller,
                        autofocus: true,
                        minLines: 2,
                        maxLines: 4,
                        textDirection: TextDirection.rtl,
                        enabled: !_submitting,
                        decoration: InputDecoration(
                          hintText: _label(
                            'اكتب الترجمة هنا...',
                            'Write your translation here...',
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                        onSubmitted: (_) => _next(),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        '${_index + 1} / ${_questions.length}',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.labelMedium,
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: TextStyle(color: theme.colorScheme.error),
                        ),
                      ],
                    ],
                  ),
      ),
      actions: [
        if (!_loading && _questions.isNotEmpty && _index > 0)
          TextButton(
            onPressed: _submitting
                ? null
                : () {
                    final id = _questions[_index]['id'].toString();
                    _answers[id] = _controller.text.trim();
                    setState(() {
                      _index--;
                      _controller.text =
                          _answers[_questions[_index]['id'].toString()] ?? '';
                      _error = null;
                    });
                  },
            child: Text(_label('السابق', 'Back')),
          ),
        if (!_loading && _questions.isNotEmpty)
          FilledButton(
            onPressed: _submitting ? null : _next,
            child: _submitting
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(
                    _index == _questions.length - 1
                        ? _label('تقييم الإجابات', 'Check answers')
                        : _label('التالي', 'Next'),
                  ),
          ),
      ],
    );
  }
}
