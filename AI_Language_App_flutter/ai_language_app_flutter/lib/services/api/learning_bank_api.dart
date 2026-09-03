import 'word_api_service.dart';
import 'api_client.dart';
import 'api_service.dart';

extension LearningBankApi on ApiService {
  Future<Map<String, dynamic>> saveSentence({
    required String sentence,
    required String translation,
  }) {
    return WordApiService(ApiClient()).createSentence(
      sentence: sentence,
      translation: translation,
    );
  }

  Future<List<dynamic>> getSavedSentences() {
    return WordApiService(ApiClient()).getSentences();
  }
}
