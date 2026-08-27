import '../services/api/api_service.dart';

class PlacementRepository {
  final ApiService apiService;

  PlacementRepository({
    ApiService? apiService,
  }) : apiService = apiService ?? ApiService();

  Future<Map<String, dynamic>> getPlacementWords({
    required String language,
    required String level,
  }) {
    return apiService.getPlacementWords(
      language: language,
      level: level,
    );
  }

  Future<Map<String, dynamic>> evaluatePlacementWords({
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

  Future<Map<String, dynamic>> getPlacementQuiz({
    required String language,
    required String level,
  }) {
    return apiService.getPlacementQuiz(
      language: language,
      level: level,
    );
  }

  Future<Map<String, dynamic>> evaluatePlacementQuiz({
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

  Future<Map<String, dynamic>> finalizePlacement({
    required String language,
    required String level,
  }) {
    return apiService.finalizePlacement(
      language: language,
      level: level,
    );
  }
}