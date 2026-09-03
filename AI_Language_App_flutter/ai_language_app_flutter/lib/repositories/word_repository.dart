import '../services/api/api_service.dart';
import '../services/api/api_client.dart';
import '../services/api/word_api_service.dart';

class WordRepository {
  final ApiService apiService;
  final WordApiService wordApiService;

  WordRepository({ApiService? apiService, WordApiService? wordApiService})
      : apiService = apiService ?? ApiService(),
        wordApiService = wordApiService ?? WordApiService(ApiClient());

  Future<List<dynamic>> getWords() => apiService.getWords();

  Future<Map<String, dynamic>> updateWordStatus({
    required int wordId,
    required bool learned,
  }) => apiService.updateWordStatus(wordId: wordId, learned: learned);

  Future<void> deleteWord({required int wordId}) => apiService.deleteWord(wordId: wordId);

  Future<Map<String, dynamic>> createWord({
    required String word,
    required String translation,
  }) => apiService.createWord(word: word, translation: translation);

  Future<Map<String, dynamic>> createSentence({
    required String sentence,
    required String translation,
  }) => wordApiService.createSentence(sentence: sentence, translation: translation);

  Future<List<dynamic>> getSentences() => wordApiService.getSentences();

  Future<Map<String, dynamic>> updateSentenceStatus({
    required int sentenceId,
    required bool learned,
  }) => wordApiService.updateSentenceStatus(sentenceId: sentenceId, learned: learned);

  Future<void> deleteSentence({required int sentenceId}) => wordApiService.deleteSentence(sentenceId: sentenceId);
}
