import '../models/placement_models.dart';
import '../services/api/api_service.dart';

class PlacementRepository {
  final ApiService apiService;

  PlacementRepository({
    ApiService? apiService,
  }) : apiService = apiService ?? ApiService();

  Future<PlacementWordsResponse> getPlacementWords({
    required String language,
    required String level,
  }) {
    return apiService.getPlacementWords(
      language: language,
      level: level,
    );
  }

  Future<PlacementWordEvaluation> evaluatePlacementWords({
    required String language,
    required String level,
    required List<int> presentedWordIds,
    required List<int> selectedWordIds,
  }) {
    return apiService.evaluatePlacementWords(
      language: language,
      level: level,
      presentedWordIds: presentedWordIds,
      selectedWordIds: selectedWordIds,
    );
  }

  Future<PlacementQuizResponse> getPlacementQuiz({
    required String language,
    required String level,
  }) {
    return apiService.getPlacementQuiz(
      language: language,
      level: level,
    );
  }

  Future<PlacementQuizEvaluation> evaluatePlacementQuiz({
    required String language,
    required String level,
    required List<Map<String, int>> answers,
  }) {
    return apiService.evaluatePlacementQuiz(
      language: language,
      level: level,
      answers: answers,
    );
  }

  Future<PlacementFinalizeResponse> finalizePlacement({
    required String language,
    required String level,
  }) {
    return apiService.finalizePlacement(
      language: language,
      level: level,
    );
  }
}