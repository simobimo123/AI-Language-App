import 'package:flutter/material.dart';

import '../models/lesson_content_model.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';
import '../core/language/language_controller.dart';

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

class _LessonPageState extends State<LessonPage> {
  late final LearningRepository _repository;

  LessonContentModel? _content;
  String? _error;
  bool _loading = true;
  bool _submitting = false;

  int _currentExercise = 0;
  int _correctAnswers = 0;

  String? _selectedAnswer;
  final TextEditingController _answerController = TextEditingController();
  final List<String> _orderedWords = [];

  bool _answerChecked = false;
  bool _lastAnswerCorrect = false;

  @override
  void initState() {
    super.initState();

    _repository = widget.repository ?? LearningRepository();

    _loadContent();
  }

  @override
  void dispose() {
    _answerController.dispose();
    super.dispose();
  }

  Future<void> _loadContent() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final data = await _repository.getLessonContent(
        lessonId: widget.lesson.id,
      );

      if (!mounted) return;

      setState(() {
        _content = LessonContentModel.fromJson(data);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _resetExercise() {
    _selectedAnswer = null;
    _answerController.clear();
    _orderedWords.clear();
    _answerChecked = false;
    _lastAnswerCorrect = false;
  }

  String _normalize(String value) {
    return value.trim().toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
  }

  String _currentUserAnswer(LessonExercise exercise) {
    if (exercise.type == 'multiple_choice') {
      return _selectedAnswer ?? '';
    }

    if (exercise.type == 'word_order') {
      return _orderedWords.join(' ');
    }

    return _answerController.text;
  }

  void _checkAnswer() {
    final content = _content;

    if (content == null ||
        _answerChecked ||
        content.exercises.isEmpty ||
        _currentExercise >= content.exercises.length) {
      return;
    }

    final exercise = content.exercises[_currentExercise];

    final userAnswer = _currentUserAnswer(exercise);

    if (userAnswer.trim().isEmpty) {
      return;
    }

    final isCorrect =
        _normalize(userAnswer) == _normalize(exercise.answer);

    setState(() {
      _answerChecked = true;
      _lastAnswerCorrect = isCorrect;

      if (isCorrect) {
        _correctAnswers++;
      }
    });
  }

  Future<void> _nextExercise() async {
    final content = _content;

    if (content == null || !_answerChecked) {
      return;
    }

    if (_currentExercise < content.exercises.length - 1) {
      setState(() {
        _currentExercise++;
        _resetExercise();
      });

      return;
    }

    await _completeLesson();
  }

  Future<void> _completeLesson() async {
    if (_submitting) return;

    setState(() {
      _submitting = true;
    });

    try {
      final total = _content?.exercises.length ?? 0;

      final score = total == 0
          ? 0
          : ((_correctAnswers / total) * 100).round();

      await _repository.completeLesson(
        lessonId: widget.lesson.id,
        score: score.toDouble(),
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
        SnackBar(
          content: Text(
            'Failed to complete lesson: $e',
          ),
        ),
      );
    }
  }

  String _pageTitle() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Leçon';
      case 'es':
        return 'Lección';
      case 'zh':
        return '课程';
      case 'ja':
        return 'レッスン';
      case 'ko':
        return '레슨';
      case 'en':
        return 'Lesson';
      case 'ar':
      default:
        return 'الدرس';
    }
  }

  String _loadingText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Chargement de la leçon...';
      case 'es':
        return 'Cargando la lección...';
      case 'zh':
        return '正在加载课程...';
      case 'ja':
        return 'レッスンを読み込んでいます...';
      case 'ko':
        return '레슨을 불러오는 중...';
      case 'en':
        return 'Loading lesson...';
      case 'ar':
      default:
        return 'جارٍ تحميل الدرس...';
    }
  }

  String _retryText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Réessayer';
      case 'es':
        return 'Reintentar';
      case 'zh':
        return '重试';
      case 'ja':
        return '再試行';
      case 'ko':
        return '다시 시도';
      case 'en':
        return 'Retry';
      case 'ar':
      default:
        return 'إعادة المحاولة';
    }
  }

  String _startText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Exercices';
      case 'es':
        return 'Ejercicios';
      case 'zh':
        return '练习';
      case 'ja':
        return '練習';
      case 'ko':
        return '연습';
      case 'en':
        return 'Exercises';
      case 'ar':
      default:
        return 'التمارين';
    }
  }

  String _checkText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Vérifier';
      case 'es':
        return 'Comprobar';
      case 'zh':
        return '检查';
      case 'ja':
        return '確認';
      case 'ko':
        return '확인';
      case 'en':
        return 'Check';
      case 'ar':
      default:
        return 'تحقق';
    }
  }

  String _nextText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Suivant';
      case 'es':
        return 'Siguiente';
      case 'zh':
        return '下一题';
      case 'ja':
        return '次へ';
      case 'ko':
        return '다음';
      case 'en':
        return 'Next';
      case 'ar':
      default:
        return 'التالي';
    }
  }

  String _finishText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Terminer';
      case 'es':
        return 'Terminar';
      case 'zh':
        return '完成';
      case 'ja':
        return '完了';
      case 'ko':
        return '완료';
      case 'en':
        return 'Finish';
      case 'ar':
      default:
        return 'إنهاء';
    }
  }

  String _correctText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Correct !';
      case 'es':
        return '¡Correcto!';
      case 'zh':
        return '正确！';
      case 'ja':
        return '正解！';
      case 'ko':
        return '정답입니다!';
      case 'en':
        return 'Correct!';
      case 'ar':
      default:
        return 'إجابة صحيحة!';
    }
  }

  String _incorrectText() {
    final locale = widget.languageController.locale.languageCode;

    switch (locale) {
      case 'fr':
        return 'Incorrect';
      case 'es':
        return 'Incorrecto';
      case 'zh':
        return '不正确';
      case 'ja':
        return '不正解';
      case 'ko':
        return '오답입니다';
      case 'en':
        return 'Incorrect';
      case 'ar':
      default:
        return 'إجابة غير صحيحة';
    }
  }

  Widget _buildVocabulary(
    LessonContentModel content,
    ThemeData theme,
  ) {
    if (content.vocabulary.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Vocabulary',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...content.vocabulary.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        item.word,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        item.translation,
                        textAlign: TextAlign.end,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExamples(
    LessonContentModel content,
    ThemeData theme,
  ) {
    if (content.examples.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Examples',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...content.examples.map(
              (example) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      example.targetText,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      example.translation,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDialogue(
    LessonContentModel content,
    ThemeData theme,
  ) {
    if (content.dialogue.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Dialogue',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...content.dialogue.map(
              (line) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      line.targetText,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(line.translation),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExerciseInput(LessonExercise exercise) {
    if (exercise.type == 'multiple_choice') {
      return RadioGroup<String>(
        groupValue: _selectedAnswer,
        onChanged: (String? value) {
          if (_answerChecked) return;
          setState(() {
            _selectedAnswer = value;
          });
        },
        child: Column(
          children: exercise.options.map((option) {
            return RadioListTile<String>(
              value: option,
              title: Text(option),
              contentPadding: EdgeInsets.zero,
            );
          }).toList(),
        ),
      );
    }

    if (exercise.type == 'word_order') {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_orderedWords.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _orderedWords.join(' '),
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: exercise.options.map((word) {
              final used = _orderedWords.contains(word);

              return OutlinedButton(
                onPressed: _answerChecked || used
                    ? null
                    : () {
                        setState(() {
                          _orderedWords.add(word);
                        });
                      },
                child: Text(word),
              );
            }).toList(),
          ),
          if (_orderedWords.isNotEmpty && !_answerChecked)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: TextButton(
                onPressed: () {
                  setState(() {
                    _orderedWords.clear();
                  });
                },
                child: const Text('Clear'),
              ),
            ),
        ],
      );
    }

    return TextField(
      controller: _answerController,
      enabled: !_answerChecked,
      maxLines: exercise.type == 'translation' ? 3 : 1,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        hintText: 'Type your answer',
      ),
    );
  }

  Widget _buildExercise(
    LessonContentModel content,
    ThemeData theme,
  ) {
    if (content.exercises.isEmpty) {
      return const SizedBox.shrink();
    }

    final exercise = content.exercises[_currentExercise];
    final total = content.exercises.length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _startText(),
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '${_currentExercise + 1} / $total',
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: (_currentExercise + 1).toDouble() / total,
            ),
            const SizedBox(height: 20),
            Text(
              exercise.question,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            _buildExerciseInput(exercise),
            const SizedBox(height: 16),
            if (_answerChecked)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _lastAnswerCorrect
                          ? _correctText()
                          : _incorrectText(),
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                        color: _lastAnswerCorrect
                            ? Colors.green
                            : Colors.red,
                      ),
                    ),
                    if (!_lastAnswerCorrect)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(
                          'Correct answer: ${exercise.answer}',
                        ),
                      ),
                    if (exercise.explanation != null &&
                        exercise.explanation!.trim().isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(
                          exercise.explanation!,
                        ),
                      ),
                  ],
                ),
              ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submitting
                    ? null
                    : _answerChecked
                        ? _nextExercise
                        : _checkAnswer,
                child: Text(
                  _answerChecked
                      ? (_currentExercise == total - 1
                          ? _finishText()
                          : _nextText())
                      : _checkText(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) {
      return Scaffold(
        appBar: AppBar(
          title: Text(_pageTitle()),
        ),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(_loadingText()),
            ],
          ),
        ),
      );
    }

    if (_error != null) {
      return Scaffold(
        appBar: AppBar(
          title: Text(_pageTitle()),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.error_outline,
                  size: 48,
                ),
                const SizedBox(height: 16),
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _loadContent,
                  child: Text(_retryText()),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final content = _content;

    if (content == null) {
      return Scaffold(
        appBar: AppBar(
          title: Text(_pageTitle()),
        ),
        body: Center(
          child: ElevatedButton(
            onPressed: _loadContent,
            child: Text(_retryText()),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          content.title.isNotEmpty ? content.title : _pageTitle(),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadContent,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (content.objective.isNotEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        content.objective,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            if (content.introduction.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    content.introduction,
                    style: theme.textTheme.bodyLarge,
                  ),
                ),
              ),
            ],
            if (content.explanation.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    content.explanation,
                    style: theme.textTheme.bodyLarge,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 12),
            _buildVocabulary(content, theme),
            const SizedBox(height: 12),
            _buildExamples(content, theme),
            const SizedBox(height: 12),
            _buildDialogue(content, theme),
            const SizedBox(height: 12),
            _buildExercise(content, theme),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}


