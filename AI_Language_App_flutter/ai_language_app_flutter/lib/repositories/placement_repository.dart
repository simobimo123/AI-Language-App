import '../models/placement_models.dart';
import '../services/api/api_service.dart';

class PlacementRepository {
  final ApiService apiService;

  PlacementRepository({ApiService? apiService}) : apiService = apiService ?? ApiService();

  Future<int> startPlacementAttempt({required String language}) =>
      apiService.startPlacementAttempt(language: language);

  Future<PlacementWordsResponse> getPlacementWords({
    required int attemptId,
    required String language,
    required String level,
  }) =>
      apiService.getPlacementWords(
        attemptId: attemptId,
        language: language,
        level: level,
      );

  Future<PlacementWordEvaluation> evaluatePlacementWords({
    required int attemptId,
    required List<int> selectedWordIds,
  }) =>
      apiService.evaluatePlacementWords(
        attemptId: attemptId,
        selectedWordIds: selectedWordIds,
      );

  Future<PlacementQuizResponse> getPlacementQuiz({required int attemptId}) =>
      apiService.getPlacementQuiz(attemptId: attemptId);

  Future<PlacementQuizEvaluation> evaluatePlacementQuiz({
    required int attemptId,
    required String language,
    required String level,
    required Map<int, int> answers,
  }) =>
      apiService.evaluatePlacementQuiz(
        attemptId: attemptId,
        language: language,
        level: level,
        answers: answers,
      );

  Future<PlacementFinalizeResponse> finalizePlacement({required int attemptId}) =>
      apiService.finalizePlacement(attemptId: attemptId);
}