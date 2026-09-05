import 'package:flutter/foundation.dart';

import '../models/learning_lesson_model.dart';
import '../models/learning_path_model.dart';
import '../repositories/learning_repository.dart';
import '../services/learning_language_controller.dart';

class LearningPathController extends ChangeNotifier {
  final LearningRepository repository;

  final LearningLanguageController learningLanguageController;

  LearningPathModel? _learningPath;

  bool _isLoading = false;
  String? _errorMessage;

  String? _loadedLanguage;

  LearningPathController({
    LearningRepository? repository,
    LearningLanguageController? learningLanguageController,
  })  : repository = repository ?? LearningRepository(),
        learningLanguageController =
            learningLanguageController ??
                LearningLanguageController.instance {
    this.learningLanguageController.addListener(
      _onLearningLanguageChanged,
    );
  }

  bool get isLoading => _isLoading;

  String? get errorMessage => _errorMessage;

  LearningPathModel? get learningPath => _learningPath;

  List<LearningLessonModel> get lessons =>
      _learningPath?.lessons ?? const [];

  String get learningLanguage =>
      _learningPath?.language ?? '';

  String get currentLevel =>
      _learningPath?.level ?? '';

  String get nextLevel =>
      _learningPath?.nextLevel ?? '';

  double get progress =>
      _learningPath?.progress ?? 0;

  int get completedLessons =>
      _learningPath?.completedLessons ?? 0;

  int get totalLessons =>
      _learningPath?.totalLessons ?? 0;

  bool get hasLessons => lessons.isNotEmpty;

  Future<void> load() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final data = await repository.getLearningPath();

      final model = LearningPathModel.fromJson(data);

      _learningPath = model;
      _loadedLanguage = model.language;
      _errorMessage = null;
    } catch (error) {
      _errorMessage = _cleanErrorMessage(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final data = await repository.getLearningPath();

      final model = LearningPathModel.fromJson(data);

      _learningPath = model;
      _loadedLanguage = model.language;
      _errorMessage = null;
    } catch (error) {
      _errorMessage = _cleanErrorMessage(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void _onLearningLanguageChanged() {
    final newLanguage =
        learningLanguageController.currentLanguage;

    if (newLanguage == null ||
        newLanguage.isEmpty ||
        newLanguage == _loadedLanguage) {
      return;
    }

    refresh();
  }

  String _cleanErrorMessage(Object error) {
    final message = error.toString();

    if (message.startsWith('Exception: ')) {
      return message.substring('Exception: '.length);
    }

    return message;
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(
      _onLearningLanguageChanged,
    );

    super.dispose();
  }
}