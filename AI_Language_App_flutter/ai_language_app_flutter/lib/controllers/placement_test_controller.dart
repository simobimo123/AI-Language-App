import 'package:flutter/foundation.dart';

import '../core/errors/error_message.dart';
import '../models/placement_models.dart';
import '../repositories/placement_repository.dart';

class PlacementTestController extends ChangeNotifier {
  final PlacementRepository repository;
  final String language;

  PlacementTestController({required this.language, PlacementRepository? repository})
      : repository = repository ?? PlacementRepository();

  int? attemptId;
  String currentLevel = 'A1';
  List<PlacementWord> words = const [];
  final Set<int> selectedWordIds = {};
  List<PlacementQuizQuestion> quizQuestions = const [];
  final Map<int, int> quizAnswers = {};

  bool isLoading = true;
  bool isEvaluating = false;
  bool isQuizMode = false;
  bool isFinished = false;
  String? errorMessage;
  String? finalLevel;

  int get quizAnsweredCount => quizAnswers.length;

  bool get canSubmitQuiz =>
      quizQuestions.isNotEmpty &&
      quizAnswers.length == quizQuestions.length &&
      !isEvaluating;

  Future<void> initialize() => startAttempt();

  Future<void> startAttempt() async {
    isLoading = true;
    isQuizMode = false;
    isFinished = false;
    isEvaluating = false;
    errorMessage = null;
    finalLevel = null;
    attemptId = null;
    currentLevel = 'A1';
    words = const [];
    selectedWordIds.clear();
    quizQuestions = const [];
    quizAnswers.clear();
    notifyListeners();

    try {
      final id = await repository.startPlacementAttempt(language: language);
      attemptId = id;
      await _loadWordsForAttempt();
    } catch (error) {
      isLoading = false;
      errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> _loadWordsForAttempt() async {
    final id = attemptId;
    if (id == null) {
      throw StateError('Placement attempt was not created.');
    }

    final result = await repository.getPlacementWords(
      attemptId: id,
      language: language,
      level: currentLevel,
    );

    if (result.words.length != 20) {
      throw StateError('The placement test must contain exactly 20 words.');
    }

    words = result.words;
    selectedWordIds.clear();
    isLoading = false;
    isQuizMode = false;
    isEvaluating = false;
    errorMessage = null;
    notifyListeners();
  }

  void toggleWord(int wordId) {
    if (isEvaluating || isLoading) return;

    if (selectedWordIds.contains(wordId)) {
      selectedWordIds.remove(wordId);
    } else {
      selectedWordIds.add(wordId);
    }

    notifyListeners();
  }

  Future<void> evaluateWords() async {
    final id = attemptId;
    if (isEvaluating || id == null || words.length != 20) return;

    isEvaluating = true;
    errorMessage = null;
    notifyListeners();

    try {
      final result = await repository.evaluatePlacementWords(
        attemptId: id,
        selectedWordIds: selectedWordIds.toList(),
      );

      // The server reports the level represented by the words that
      // were just tested. A failed level is therefore confirmed at
      // THAT SAME LEVEL; we must not silently move down before the quiz.
      if (!result.passed) {
        currentLevel = result.preliminaryLevel;
        await _loadQuiz(id);
        return;
      }

      // Passed this level. Continue progressively to the next level.
      final nextLevel = result.nextLevel;

      if (nextLevel != null && nextLevel.isNotEmpty) {
        currentLevel = nextLevel;
        await _loadWordsForAttempt();
        return;
      }

      // C2 is the highest level. If the user passed it, placement is
      // complete without a confirmation quiz.
      await _finalize(id);
    } catch (error) {
      isEvaluating = false;
      errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> _loadQuiz(int id) async {
    isLoading = true;
    isQuizMode = false;
    quizQuestions = const [];
    quizAnswers.clear();
    errorMessage = null;
    notifyListeners();

    final result = await repository.getPlacementQuiz(attemptId: id);

    if (result.questions.length != 10) {
      throw StateError('The confirmation quiz must contain exactly 10 questions.');
    }

    quizQuestions = result.questions;
    isLoading = false;
    isEvaluating = false;
    isQuizMode = true;
    notifyListeners();
  }

  void selectQuizAnswer(int questionId, int answerIndex) {
    if (isEvaluating) return;
    quizAnswers[questionId] = answerIndex;
    notifyListeners();
  }

  Future<void> evaluateQuiz() async {
    final id = attemptId;
    if (!canSubmitQuiz || id == null) return;

    isEvaluating = true;
    errorMessage = null;
    notifyListeners();

    try {
      final result = await repository.evaluatePlacementQuiz(
        attemptId: id,
        answers: Map<int, int>.from(quizAnswers),
      );

      currentLevel = result.finalLevel;
      await _finalize(id);
    } catch (error) {
      isEvaluating = false;
      errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> _finalize(int id) async {
    final result = await repository.finalizePlacement(attemptId: id);
    finalLevel = result.level;
    currentLevel = result.level;
    isEvaluating = false;
    isLoading = false;
    isFinished = true;
    isQuizMode = false;
    errorMessage = null;
    notifyListeners();
  }

  Future<void> retry() async {
    if (isEvaluating) return;
    await startAttempt();
  }
}
