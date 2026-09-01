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

  int? attemptId;
  String currentLevel = 'A1';
  List<PlacementWord> words = const [];
  final Set<int> selectedWordIds = {};

  bool isLoading = true;
  bool isEvaluating = false;
  bool isFinished = false;
  String? errorMessage;
  String? finalLevel;

  Future<void> initialize() => startAttempt();

  Future<void> startAttempt() async {
    isLoading = true;
    isFinished = false;
    isEvaluating = false;
    errorMessage = null;
    finalLevel = null;
    attemptId = null;
    currentLevel = 'A1';
    words = const [];
    selectedWordIds.clear();
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

    if (currentLevel == 'PRE_A1') {
      await _finalize(id);
      return;
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

      // Vocabulary-only placement:
      // - 50% or more: move up one CEFR level.
      // - Less than 50%: move down one CEFR level.
      // - A1 failure: PRE_A1 and finish immediately.
      // - C2 success: finish at C2.
      if (!result.passed) {
        currentLevel = result.preliminaryLevel;
        await _finalize(id);
        return;
      }

      final nextLevel = result.nextLevel;
      if (nextLevel != null && nextLevel.isNotEmpty) {
        currentLevel = nextLevel;
        await _loadWordsForAttempt();
        return;
      }

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
    errorMessage = null;
    notifyListeners();
  }

  Future<void> retry() async {
    if (isEvaluating) return;
    await startAttempt();
  }
}
