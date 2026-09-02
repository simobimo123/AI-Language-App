import 'package:flutter/material.dart';

import '../models/lesson_content_model.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';

class LessonPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LearningRepository? repository;

  const LessonPage({
    super.key,
    required this.lesson,
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
      final data = await _repository.getLessonContent(lessonId: widget.lesson.id);
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

  String _tr({required String ar, required String en, String? fr, String? es}) {
    // The lesson content itself is already generated in the user's instruction language.
    // These labels remain local so the lesson UI works without another API/AI call.
    return ar;
  }

  void _resetExercise() {
    _selectedAnswer = null;
    _answerController.clear();
    _orderedWords.clear();
    _answerChecked = false;
    _lastAnswerCorrect = false;
  }

  void _checkAnswer() {
    final content = _content;
    if (content == null || _answerChecked) return;
    final exercise = content.exercises[_currentExercise];
    String answer;

    if (exercise.type == 'multiple_choice') {
      answer = _selectedAnswer ?? '';
    } else if (exercise.type == 'word_order') {
      answer = _orderedWords.join(' ').trim();
    } else {
      answer = _answerController.text.trim();
    }

    if (answer.isEmpty) return;

    final correct = _normalize(answer) == _normalize(exercise.answer);
    setState(() {
      _answerChecked = true;
      _lastAnswerCorrect = correct;
      if (correct) _correctAnswers++;
    });
  }

  String _normalize(String value) {
    return value.trim().toLowerCase().replaceAll(RegExp(r'\\s+'), ' ');
  }

  void _nextExercise() {
    final content = _content;
    if (content == null) return;

    if (_currentExercise < content.exercises.length - 1) {
      setState(() {
        _currentExercise++;
        _resetExercise();
      });
      return;
    }

    _completeLesson();
  }

  Future<void> _completeLesson() async {
    final content = _content;
    if (content == null || _submitting) return;

    final total = content.exercises.length;
    final score = total == 0 ? 100.0 : (_correctAnswers / total) * 100.0;

    setState(() => _submitting = true);

    try {
      await _repository.completeLesson(
        lessonId: widget.lesson.id,
        score: score,
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Lesson completed'),
          content: Text(
            'Your score: ${score.round()}%\\n\\nYou can continue to the next lesson.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Continue'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: theme.scaffoldBackgroundColor,
        title: Text(
          widget.lesson.title,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : _content == null
                  ? const Center(child: Text('Lesson content is unavailable.'))
                  : _buildLesson(_content!),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 48),
            const SizedBox(height: 16),
            const Text(
              'Unable to load this lesson.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _loadContent,
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLesson(LessonContentModel content) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        _sectionCard(
          icon: Icons.flag_outlined,
          title: content.title,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(content.objective, style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 16),
              Text(content.introduction),
            ],
          ),
        ),
        if (content.explanation.isNotEmpty)
          _sectionCard(
            icon: Icons.menu_book_outlined,
            title: 'Explanation',
            child: Text(
              content.explanation,
              style: const TextStyle(fontSize: 16, height: 1.5),
            ),
          ),
        if (content.vocabulary.isNotEmpty) _buildVocabulary(content.vocabulary),
        if (content.examples.isNotEmpty) _buildExamples(content.examples),
        if (content.dialogue.isNotEmpty) _buildDialogue(content.dialogue),
        if (content.exercises.isNotEmpty) _buildExercises(content.exercises),
      ],
    );
  }

  Widget _sectionCard({
    required IconData icon,
    required String title,
    required Widget child,
  }) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }

  Widget _buildVocabulary(List<LessonVocabularyItem> items) {
    return _sectionCard(
      icon: Icons.translate,
      title: 'Vocabulary',
      child: Column(
        children: items.map((item) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    item.word,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    item.translation,
                    textAlign: TextAlign.end,
                    style: TextStyle(
                      fontSize: 16,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildExamples(List<LessonExample> items) {
    return _sectionCard(
      icon: Icons.lightbulb_outline,
      title: 'Examples',
      child: Column(
        children: items.asMap().entries.map((entry) {
          final item = entry.value;
          return Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.targetText, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                Text(item.translation),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildDialogue(List<LessonExample> items) {
    return _sectionCard(
      icon: Icons.forum_outlined,
      title: 'Dialogue',
      child: Column(
        children: items.map((item) {
          return ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(item.targetText),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(item.translation),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildExercises(List<LessonExercise> exercises) {
    final exercise = exercises[_currentExercise];
    final progress = (_currentExercise + 1) / exercises.length;

    return _sectionCard(
      icon: Icons.quiz_outlined,
      title: 'Practice',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LinearProgressIndicator(value: progress),
          const SizedBox(height: 10),
          Text(
            'Exercise ${_currentExercise + 1} of ${exercises.length}',
            style: TextStyle(color: Theme.of(context).colorScheme.primary),
          ),
          const SizedBox(height: 16),
          Text(
            exercise.question,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 16),
          _buildExerciseInput(exercise),
          if (_answerChecked) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                color: _lastAnswerCorrect
                    ? Colors.green.withValues(alpha: 0.12)
                    : Colors.red.withValues(alpha: 0.12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _lastAnswerCorrect ? 'Correct!' : 'Not quite',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: _lastAnswerCorrect ? Colors.green : Colors.red,
                    ),
                  ),
                  if (!_lastAnswerCorrect) ...[
                    const SizedBox(height: 6),
                    Text('Correct answer: ${exercise.answer}'),
                  ],
                  if (exercise.explanation?.isNotEmpty == true) ...[
                    const SizedBox(height: 6),
                    Text(exercise.explanation!),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _submitting
                  ? null
                  : _answerChecked
                      ? _nextExercise
                      : _checkAnswer,
              child: Text(
                _answerChecked
                    ? (_currentExercise == exercises.length - 1
                        ? 'Finish lesson'
                        : 'Next')
                    : 'Check answer',
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExerciseInput(LessonExercise exercise) {
    if (exercise.type == 'multiple_choice') {
      return Column(
        children: exercise.options.map((option) {
          return RadioListTile<String>(
            value: option,
            groupValue: _selectedAnswer,
            onChanged: _answerChecked ? null : (value) => setState(() => _selectedAnswer = value),
            title: Text(option),
            contentPadding: EdgeInsets.zero,
          );
        }).toList(),
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
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
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
                    : () => setState(() => _orderedWords.add(word)),
                child: Text(word),
              );
            }).toList(),
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
}
