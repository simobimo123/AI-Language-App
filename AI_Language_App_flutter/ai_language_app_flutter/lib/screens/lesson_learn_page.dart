import 'dart:math';

import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';

class LessonLearnPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;

  const LessonLearnPage({
    super.key,
    required this.lesson,
    required this.languageController,
  });

  @override
  State<LessonLearnPage> createState() => _LessonLearnPageState();
}

class _LessonLearnPageState extends State<LessonLearnPage> {
  final ApiService _api = ApiService();
  final TextEditingController _input = TextEditingController();
  final Random _random = Random();

  List<Map<String, dynamic>> _sections = [];
  List<Map<String, dynamic>> _questions = [];
  List<String> _displayOptions = [];
  bool _loading = true;
  String? _error;
  int _index = 0;
  int? _selected;
  bool _answered = false;
  bool _correct = false;

  String _t(String ar, String en) =>
      widget.languageController.locale.languageCode == 'ar' ? ar : en;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final response = await _api.getLessonContent(lessonId: widget.lesson.id);
      final content = response['content'] is Map
          ? Map<String, dynamic>.from(response['content'])
          : <String, dynamic>{};
      final sections = content['sections'] is List
          ? (content['sections'] as List)
              .whereType<Map>()
              .map((e) => Map<String, dynamic>.from(e))
              .toList()
          : <Map<String, dynamic>>[];
      final questions = content['exercises'] is List
          ? (content['exercises'] as List)
              .whereType<Map>()
              .map((e) => Map<String, dynamic>.from(e))
              .toList()
          : <Map<String, dynamic>>[];

      if (!mounted) return;

      setState(() {
        _sections = sections;
        _questions = questions;
        _loading = false;
        _prepareOptions();
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = _t(
          'تعذر تحميل محتوى الدرس.',
          'Could not load the lesson content.',
        );
      });
    }
  }

  Map<String, dynamic>? get _section =>
      _index < _sections.length ? _sections[_index] : null;

  Map<String, dynamic>? get _question =>
      _index < _questions.length ? _questions[_index] : null;

  int get _total =>
      _questions.isNotEmpty ? _questions.length : _sections.length;

  String _answerFor(Map<String, dynamic> question) {
    return (question['correct_answer'] ?? question['answer'] ?? '')
        .toString();
  }

  bool _isShortAnswer() {
    final type = (_question?['type'] ?? '').toString();
    final options = _question?['options'];
    return type == 'short_answer' || options is! List || options.isEmpty;
  }

  void _prepareOptions() {
    if (_question == null) {
      _displayOptions = [];
      return;
    }

    final raw = _question!['options'];
    if (raw is! List) {
      _displayOptions = [];
      return;
    }

    _displayOptions = raw.map((value) => value.toString()).toList();
    _displayOptions.shuffle(_random);
  }

  void _choose(int i) {
    if (_answered || _question == null) return;

    final answer = _answerFor(_question!);
    setState(() {
      _selected = i;
      _answered = true;
      _correct = i < _displayOptions.length && _displayOptions[i] == answer;
    });
  }

  void _submitText() {
    if (_answered || _question == null) return;

    final expected = _answerFor(_question!).trim().toLowerCase();
    final value = _input.text.trim().toLowerCase();
    final accepted = (_question!['accepted_answers'] is List) &&
        (_question!['accepted_answers'] as List).any(
          (x) => x.toString().trim().toLowerCase() == value,
        );

    setState(() {
      _answered = true;
      _correct = value.isNotEmpty && (value == expected || accepted);
    });
  }

  void _next() {
    if (!_answered) return;

    if (_index + 1 >= _total) {
      Navigator.pop(context, true);
      return;
    }

    setState(() {
      _index++;
      _selected = null;
      _answered = false;
      _correct = false;
      _input.clear();
      _prepareOptions();
    });
  }

  void _finishButtonPressed() {
    if (_answered) {
      _next();
      return;
    }

    if (_index + 1 >= _total &&
        _isShortAnswer() &&
        _input.text.trim().isNotEmpty) {
      _submitText();
    }
  }

  bool get _finishButtonEnabled =>
      _answered ||
      (_index + 1 >= _total &&
          _isShortAnswer() &&
          _input.text.trim().isNotEmpty);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final progress = _total == 0
        ? 0.0
        : ((_index + 1) / _total).clamp(0.0, 1.0);

    final sectionHasTeaching =
        (_section?['target_text'] ?? '').toString().trim().isNotEmpty ||
            (_section?['translation'] ?? '').toString().trim().isNotEmpty ||
            (_section?['explanation'] ?? '').toString().trim().isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: Text(_t('المرحلة 1 · التعلّم', 'Stage 1 · Learning')),
        actions: [
          Padding(
            padding: const EdgeInsetsDirectional.only(end: 18),
            child: Center(
              child: Text(
                _total == 0 ? '' : '${_index + 1}/$_total',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorState(message: _error!, onRetry: _load, text: _t)
              : _total == 0
                  ? _EmptyState(
                      onBack: () => Navigator.pop(context),
                      text: _t,
                    )
                  : SafeArea(
                      child: Column(
                        children: [
                          Padding(
                            padding:
                                const EdgeInsets.fromLTRB(20, 4, 20, 12),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(99),
                              child: LinearProgressIndicator(
                                value: progress,
                                minHeight: 7,
                              ),
                            ),
                          ),
                          Expanded(
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                              child: Column(
                                children: [
                                  if (sectionHasTeaching)
                                    _TeachingCard(
                                      section: _section,
                                      theme: theme,
                                      languageController:
                                          widget.languageController,
                                    ),
                                  if (sectionHasTeaching)
                                    const SizedBox(height: 16),
                                  _QuestionCard(
                                    question: _question,
                                    options: _displayOptions,
                                    answered: _answered,
                                    selected: _selected,
                                    correct: _correct,
                                    input: _input,
                                    onChoose: _choose,
                                    onSubmitText: _submitText,
                                    onTextChanged: () => setState(() {}),
                                    languageController:
                                        widget.languageController,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(20, 8, 20, 18),
                            child: SizedBox(
                              width: double.infinity,
                              child: FilledButton(
                                onPressed: _finishButtonEnabled
                                    ? _finishButtonPressed
                                    : null,
                                style: FilledButton.styleFrom(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 16),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(17),
                                  ),
                                ),
                                child: Text(
                                  _index + 1 >= _total
                                      ? _t('إنهاء المرحلة', 'Finish stage')
                                      : _t('متابعة', 'Continue'),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
    );
  }
}

class _TeachingCard extends StatelessWidget {
  final Map<String, dynamic>? section;
  final ThemeData theme;
  final LanguageController languageController;

  const _TeachingCard({
    required this.section,
    required this.theme,
    required this.languageController,
  });

  String _t(String ar, String en) =>
      languageController.locale.languageCode == 'ar' ? ar : en;

  @override
  Widget build(BuildContext context) {
    final target = (section?['target_text'] ?? '').toString();
    final translation = (section?['translation'] ?? '').toString();
    final explanation = (section?['explanation'] ?? '').toString();
    final examples = section?['examples'];

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primary,
            theme.colorScheme.primary.withOpacity(.76),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withOpacity(.18),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(.15),
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(Icons.lightbulb_rounded,
                    color: Colors.white),
              ),
              const SizedBox(width: 12),
              Text(
                _t('تعلّم', 'Learn'),
                style: const TextStyle(
                  color: Colors.white70,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (target.isNotEmpty)
            Text(
              target,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.w900,
                height: 1.2,
              ),
            ),
          if (translation.isNotEmpty) ...[
            const SizedBox(height: 10),
            Center(
              child: Text(
                translation,
                style: const TextStyle(color: Colors.white70, fontSize: 16),
              ),
            ),
          ],
          if (explanation.isNotEmpty) ...[
            const SizedBox(height: 18),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(.10),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                explanation,
                style: const TextStyle(color: Colors.white, height: 1.45),
              ),
            ),
          ],
          if (examples is List && examples.isNotEmpty) ...[
            const SizedBox(height: 14),
            for (final e in examples.take(2))
              if (e is Map)
                Padding(
                  padding: const EdgeInsets.only(top: 5),
                  child: Text(
                    '${e['target_text'] ?? ''}  —  ${e['translation'] ?? ''}',
                    style:
                        const TextStyle(color: Colors.white70, height: 1.35),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}

class _QuestionCard extends StatelessWidget {
  final Map<String, dynamic>? question;
  final List<String> options;
  final bool answered;
  final int? selected;
  final bool correct;
  final TextEditingController input;
  final ValueChanged<int> onChoose;
  final VoidCallback onSubmitText;
  final VoidCallback onTextChanged;
  final LanguageController languageController;

  const _QuestionCard({
    required this.question,
    required this.options,
    required this.answered,
    required this.selected,
    required this.correct,
    required this.input,
    required this.onChoose,
    required this.onSubmitText,
    required this.onTextChanged,
    required this.languageController,
  });

  String _t(String ar, String en) =>
      languageController.locale.languageCode == 'ar' ? ar : en;

  String _answerFor(Map<String, dynamic> value) =>
      (value['correct_answer'] ?? value['answer'] ?? '').toString();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final title = (question?['question'] ?? '').toString();
    final type = (question?['type'] ?? 'multiple_choice').toString();
    final answer = question == null ? '' : _answerFor(question!);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _t('جرّب الآن', 'Try it now'),
            style: TextStyle(
              color: theme.colorScheme.primary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w900,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 16),
          if (type == 'short_answer' || options.isEmpty)
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: input,
                    enabled: !answered,
                    onChanged: (_) => onTextChanged(),
                    onSubmitted: (_) => onSubmitText(),
                    decoration: InputDecoration(
                      hintText: _t('اكتب بالألمانية...', 'Write in German...'),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton.filled(
                  onPressed: answered ? null : onSubmitText,
                  icon: const Icon(Icons.check_rounded),
                ),
              ],
            )
          else
            ...List.generate(options.length, (i) {
              final isSelected = selected == i;
              final isCorrect = options[i] == answer;
              final good = answered && isCorrect;
              final bad = answered && isSelected && !isCorrect;
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InkWell(
                  onTap: answered ? null : () => onChoose(i),
                  borderRadius: BorderRadius.circular(16),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    padding: const EdgeInsets.all(15),
                    decoration: BoxDecoration(
                      color: good
                          ? Colors.green.withOpacity(.10)
                          : bad
                              ? Colors.red.withOpacity(.08)
                              : isSelected
                                  ? theme.colorScheme.primary.withOpacity(.10)
                                  : theme.colorScheme.surfaceContainerHighest
                                      .withOpacity(.55),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: good
                            ? Colors.green
                            : bad
                                ? Colors.red
                                : isSelected
                                    ? theme.colorScheme.primary
                                    : theme.colorScheme.outlineVariant,
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            options[i],
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ),
                        if (good)
                          const Icon(Icons.check_circle_rounded,
                              color: Colors.green)
                        else if (bad)
                          const Icon(Icons.cancel_rounded, color: Colors.red),
                      ],
                    ),
                  ),
                ),
              );
            }),
          if (answered) ...[
            const SizedBox(height: 4),
            Text(
              correct
                  ? _t('ممتاز! الإجابة صحيحة.', 'Great! That is correct.')
                  : _t(
                      'لا بأس. راجع الجملة ثم تابع.',
                      'No problem. Review the sentence and continue.',
                    ),
              style: TextStyle(
                color: correct ? Colors.green : theme.colorScheme.error,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  final String Function(String ar, String en) text;

  const _ErrorState({
    required this.message,
    required this.onRetry,
    required this.text,
  });

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_rounded, size: 52),
              const SizedBox(height: 14),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 18),
              FilledButton(
                onPressed: onRetry,
                child: Text(text('إعادة المحاولة', 'Retry')),
              ),
            ],
          ),
        ),
      );
}

class _EmptyState extends StatelessWidget {
  final VoidCallback onBack;
  final String Function(String ar, String en) text;

  const _EmptyState({required this.onBack, required this.text});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.menu_book_rounded, size: 52),
              const SizedBox(height: 14),
              Text(
                text(
                  'محتوى الدرس غير متاح بعد.',
                  'Lesson content is not available yet.',
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 18),
              FilledButton(
                onPressed: onBack,
                child: Text(text('رجوع', 'Back')),
              ),
            ],
          ),
        ),
      );
}
