import 'package:flutter/material.dart';

import '../controllers/learning_path_controller.dart';
import '../core/language/language_controller.dart';
import '../core/theme/theme_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/learning_language_controller.dart';
import '../widgets/learning_path/learning_path_view.dart';

class LearningPathPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const LearningPathPage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<LearningPathPage> createState() => _LearningPathPageState();
}

class _LearningPathPageState extends State<LearningPathPage> {
  late final LearningPathController _controller;

  @override
  void initState() {
    super.initState();

    _controller = LearningPathController(
      learningLanguageController: LearningLanguageController.instance,
    );
    _controller.addListener(_onChanged);
    widget.languageController.addListener(_onChanged);
    _controller.load();
  }

  @override
  void dispose() {
    _controller.removeListener(_onChanged);
    widget.languageController.removeListener(_onChanged);
    _controller.dispose();
    super.dispose();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  void _openLesson(LearningLessonModel lesson) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '${lesson.title} • ${_controller.currentLevel.isNotEmpty ? _levelName(_controller.currentLevel) : ''}',
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  String _levelName(String level) =>
      level.toUpperCase() == 'PRE_A1' ? 'Pre-A1' : level;

  String _title() {
    switch (widget.languageController.locale.languageCode) {
      case 'fr': return 'Parcours d’apprentissage';
      case 'es': return 'Ruta de aprendizaje';
      case 'zh': return '学习路径';
      case 'ja': return '学習パス';
      case 'ko': return '학습 경로';
      case 'en': return 'Learning Path';
      case 'ar':
      default: return 'مسار التعلّم';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: theme.scaffoldBackgroundColor,
        elevation: 0,
        title: Text(
          _title(),
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),
      body: LearningPathView(
        controller: _controller,
        languageController: widget.languageController,
        onRetry: _controller.refresh,
        onLessonTap: _openLesson,
      ),
    );
  }
}
