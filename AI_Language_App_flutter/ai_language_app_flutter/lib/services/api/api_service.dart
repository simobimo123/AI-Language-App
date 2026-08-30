import '../../core/errors/api_exception.dart';
import '../../models/placement_models.dart';
import 'api_client.dart';
import 'auth_api_service.dart';
import 'learning_api_service.dart';
import 'placement_api_service.dart';
import 'word_api_service.dart';

class ApiService {
  static const String baseUrl = ApiClient.baseUrl;

  late final ApiClient _client;
  late final AuthApiService _auth;
  late final LearningApiService _learning;
  late final PlacementApiService _placement;
  late final WordApiService _words;

  ApiService() {
    _client = ApiClient();
    _auth = AuthApiService(_client);
    _learning = LearningApiService(_client);
    _placement = PlacementApiService(_client);
    _words = WordApiService(_client);
  }

  Future<String> testConnection() async {
    final response = await _client.get('/');

    if (response.statusCode == 200) {
      return response.body;
    }

    final data = _client.decodeResponse(response);

    throw _client.apiException(
      data,
      'Failed to connect to backend',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
  }) {
    return _auth.register(
      name: name,
      email: email,
      password: password,
    );
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) {
    return _auth.login(
      email: email,
      password: password,
    );
  }

  Future<Map<String, dynamic>> loginWithGoogle({
    required String idToken,
  }) {
    return _auth.loginWithGoogle(
      idToken: idToken,
    );
  }

  Future<Map<String, dynamic>> getCurrentUser() {
    return _auth.getCurrentUser();
  }

  Future<Map<String, dynamic>> updateCurrentUser({
    required String name,
    required String email,
    required String nativeLanguage,
    required String learningLanguage,
  }) {
    return _auth.updateCurrentUser(
      name: name,
      email: email,
      nativeLanguage: nativeLanguage,
      learningLanguage: learningLanguage,
    );
  }

  Future<List<dynamic>> getLearningProfiles() {
    return _learning.getLearningProfiles();
  }

  Future<Map<String, dynamic>> getCurrentLearningProfile() {
    return _learning.getCurrentLearningProfile();
  }

  Future<Map<String, dynamic>> createLearningProfile({
    required String language,
    required String level,
  }) {
    return _learning.createLearningProfile(
      language: language,
      level: level,
    );
  }

  Future<Map<String, dynamic>> updateLearningProfile({
    required String language,
    required String level,
    required double progress,
  }) {
    return _learning.updateLearningProfile(
      language: language,
      level: level,
      progress: progress,
    );
  }

  Future<Map<String, dynamic>> switchLearningLanguage({
    required String language,
  }) {
    return _learning.switchLearningLanguage(
      language: language,
    );
  }

  Future<Map<String, dynamic>> getLearningPath() {
    return _learning.getLearningPath();
  }

  Future<Map<String, dynamic>> completeLesson({
    required int lessonId,
    double score = 100,
  }) {
    return _learning.completeLesson(
      lessonId: lessonId,
      score: score,
    );
  }

  Future<PlacementWordsResponse> getPlacementWords({
    required String language,
    required String level,
  }) {
    return _placement.getPlacementWords(
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
    return _placement.evaluatePlacementWords(
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
    return _placement.getPlacementQuiz(
      language: language,
      level: level,
    );
  }

  Future<PlacementQuizEvaluation> evaluatePlacementQuiz({
    required String language,
    required String level,
    required List<Map<String, int>> answers,
  }) {
    return _placement.evaluatePlacementQuiz(
      language: language,
      level: level,
      answers: answers,
    );
  }

  Future<PlacementFinalizeResponse> finalizePlacement({
    required String language,
    required String level,
  }) {
    return _placement.finalizePlacement(
      language: language,
      level: level,
    );
  }

  Future<Map<String, dynamic>> createWord({
    required String word,
    required String translation,
  }) {
    return _words.createWord(
      word: word,
      translation: translation,
    );
  }

  Future<List<dynamic>> getWords() {
    return _words.getWords();
  }

  Future<Map<String, dynamic>> updateWordStatus({
    required int wordId,
    required bool learned,
  }) {
    return _words.updateWordStatus(
      wordId: wordId,
      learned: learned,
    );
  }

  Future<void> deleteWord({
    required int wordId,
  }) {
    return _words.deleteWord(
      wordId: wordId,
    );
  }

  Future<Map<String, dynamic>> getHomeStats() async {
    final response = await _client.get(
      '/stats',
      authenticated: true,
    );

    final data = _client.decodeResponse(response);

    if (response.statusCode == 200) {
      if (data is Map<String, dynamic>) {
        return data;
      }

      if (data is Map) {
        return Map<String, dynamic>.from(data);
      }

      throw const ApiException(
        'Invalid response format from home stats endpoint',
      );
    }

    throw _client.apiException(
      data,
      'Failed to get home statistics',
      statusCode: response.statusCode,
    );
  }
}