import '../services/api/api_service.dart';

class WordRepository {
  final ApiService apiService;

  WordRepository({ApiService? apiService})
      : apiService = apiService ?? ApiService();

  Future<List<dynamic>> getWords() {
    return apiService.getWords();
  }

  Future<Map<String, dynamic>> updateWordStatus({
    required int wordId,
    required bool learned,
  }) {
    return apiService.updateWordStatus(
      wordId: wordId,
      learned: learned,
    );
  }

  Future<void> deleteWord({required int wordId}) {
    return apiService.deleteWord(wordId: wordId);
  }

  Future<Map<String, dynamic>> createWord({
    required String word,
    required String translation,
  }) {
    return apiService.createWord(
      word: word,
      translation: translation,
    );
  }
}
