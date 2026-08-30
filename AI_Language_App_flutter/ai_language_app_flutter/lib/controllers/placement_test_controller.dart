import 'package:flutter/foundation.dart';

import '../core/errors/error_message.dart';
import '../models/placement_models.dart';
import '../repositories/placement_repository.dart';

class PlacementTestController extends ChangeNotifier {
  final PlacementRepository repository;
  final String language;

  PlacementTestController({
    required this.language,
    PlacementRepository? repository,
  }) : repository = repository ?? PlacementRepository();

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

  Future<void> initialize() => loadWords();

  Future<void> loadWords() async {
    isLoading = true;
    isQuizMode = false;
    errorMessage = null;
    words = const [];
    selectedWordIds.clear();
    notifyListeners();

    try {
      final result = await repository.getPlacementWords(
        language: language,
        level: currentLevel,
      );

      if (result.words.length != 20) {
        throw StateError(
          'The placement test must contain exactly 20 words.',
        );
      }

      words = result.words;
      isLoading = false;
    } catch (error) {
      isLoading = false;
      errorMessage = ErrorMessage.from(error);
    }

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
    if (isEvaluating || words.length != 20) return;

    isEvaluating = true;
    errorMessage = null;
    notifyListeners();

    try {
      final result = await repository.evaluatePlacementWords(
        language: language,
        level: currentLevel,
        presentedWordIds: words.map((word) => word.id).toList(),
        selectedWordIds: selectedWordIds.toList(),
      );

      // If the user knows fewer than 50% of the words at A1,
      // the result is immediately Pre-A1. There is no lower
      // confirmation level to test.
      if (!result.passed && result.preliminaryLevel == 'PRE_A1') {
        await finalizeLevel('PRE_A1');
        return;
      }

      // Vocabulary below 50% means the candidate level is the
      // previous level. Confirm that candidate with the quiz.
      if (!result.passed) {
        await loadQuiz(result.preliminaryLevel);
        return;
      }

      // Vocabulary at or above 50% means the user qualifies for
      // the next level. The quiz confirms that new level before
      // the final placement is saved.
      if (result.nextLevel != null) {
        await loadQuiz(result.nextLevel!);
        return;
      }

      // C2 has no higher level, so confirm C2 itself.
      await loadQuiz(currentLevel);
    } catch (error) {
      isEvaluating = false;
      errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> loadQuiz(String level) async {
    currentLevel = level;
    isLoading = true;
    isEvaluating = false;
    isQuizMode = false;
    quizQuestions = const [];
    quizAnswers.clear();
    errorMessage = null;
    notifyListeners();

    try {
      final result = await repository.getPlacementQuiz(
        language: language,
        level: level,
      );

      if (result.questions.isEmpty) {
        throw StateError('The confirmation quiz is empty.');
      }

      quizQuestions = result.questions;
      isLoading = false;
      isQuizMode = true;
    } catch (error) {
      isLoading = false;
      errorMessage = ErrorMessage.from(error);
    }

    notifyListeners();
  }

  void selectQuizAnswer(int questionId, int answerIndex) {
    if (isEvaluating) return;

    quizAnswers[questionId] = answerIndex;
    notifyListeners();
  }

  Future<void> evaluateQuiz() async {
    if (!canSubmitQuiz) return;

    isEvaluating = true;
    errorMessage = null;
    notifyListeners();

    try {
      final answers = quizAnswers.entries
          .map(
            (entry) => <String, int>{
              'question_id': entry.key,
              'selected_index': entry.value,
            },
          )
          .toList();

      final result = await repository.evaluatePlacementQuiz(
        language: language,
        level: currentLevel,
        answers: answers,
      );

      if (result.finalLevel.isEmpty) {
        throw StateError('The final placement level was not returned.');
      }

      await finalizeLevel(result.finalLevel);
    } catch (error) {
      isEvaluating = false;
      errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> finalizeLevel(String level) async {
    try {
      final result = await repository.finalizePlacement(
        language: language,
        level: level,
      );

      finalLevel = result.level.isEmpty ? level : result.level;
      isEvaluating = false;
      isFinished = true;
      notifyListeners();
    } catch (error) {
      isEvaluating = false;
      errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> retry() async {
    if (isEvaluating) return;
    await loadWords();
  }
}
