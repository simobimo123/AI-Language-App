import '../../models/placement_models.dart';
import 'api_client.dart';
import 'auth_api_service.dart';
import 'learning_api_service.dart';
import 'lesson_ai_api_service.dart';
import 'placement_api_service.dart';
import 'stats_api_service.dart';
import 'word_api_service.dart';

class ApiService {
  static const String baseUrl = ApiClient.baseUrl;
  late final ApiClient _client;
  late final AuthApiService _auth;
  late final LearningApiService _learning;
  late final LessonAiApiService _lessonAi;
  late final PlacementApiService _placement;
  late final StatsApiService _stats;
  late final WordApiService _words;

  ApiService() {
    _client = ApiClient();
    _auth = AuthApiService(_client);
    _learning = LearningApiService(_client);
    _lessonAi = LessonAiApiService(_client);
    _placement = PlacementApiService(_client);
    _stats = StatsApiService(_client);
    _words = WordApiService(_client);
  }

  Future<String> testConnection() async {
    final response = await _client.get('/');
    if (response.statusCode == 200) return response.body;
    final data = _client.decodeResponse(response);
    throw _client.apiException(data, 'Failed to connect to backend', statusCode: response.statusCode);
  }

  Future<Map<String, dynamic>> register({required String name, required String email, required String password}) => _auth.register(name: name, email: email, password: password);
  Future<Map<String, dynamic>> login({required String email, required String password}) => _auth.login(email: email, password: password);
  Future<Map<String, dynamic>> loginWithGoogle({required String idToken}) => _auth.loginWithGoogle(idToken: idToken);
  Future<Map<String, dynamic>> getCurrentUser() => _auth.getCurrentUser();
  Future<Map<String, dynamic>> updateCurrentUser({required String name, required String email, required String nativeLanguage, required String learningLanguage}) => _auth.updateCurrentUser(name: name, email: email, nativeLanguage: nativeLanguage, learningLanguage: learningLanguage);

  Future<List<dynamic>> getLearningProfiles() => _learning.getLearningProfiles();
  Future<Map<String, dynamic>> getCurrentLearningProfile() => _learning.getCurrentLearningProfile();
  Future<Map<String, dynamic>> createLearningProfile({required String language, required String level}) => _learning.createLearningProfile(language: language, level: level);
  Future<Map<String, dynamic>> updateLearningProfile({required String language, required String level, required double progress}) => _learning.updateLearningProfile(language: language, level: level, progress: progress);
  Future<Map<String, dynamic>> switchLearningLanguage({required String language}) => _learning.switchLearningLanguage(language: language);
  Future<Map<String, dynamic>> getLearningPath() => _learning.getLearningPath();
  Future<Map<String, dynamic>> getLessonContent({required int lessonId}) => _learning.getLessonContent(lessonId: lessonId);
  Future<Map<String, dynamic>> getLessonAssessment({required int lessonId, String? conversationId}) => _learning.getLessonAssessment(lessonId: lessonId, conversationId: conversationId);
  Future<Map<String, dynamic>> submitLessonAssessment({required int lessonId, String? conversationId, required List<Map<String, String>> answers}) => _learning.submitLessonAssessment(lessonId: lessonId, conversationId: conversationId, answers: answers);
  Future<Map<String, dynamic>> completeLesson({required int lessonId, double score = 100}) => _learning.completeLesson(lessonId: lessonId, score: score);

  Stream<LessonAiChunk> lessonAiChat({required int lessonId, required String message, String? conversationId}) => _lessonAi.chat(lessonId: lessonId, message: message, conversationId: conversationId);

  Future<int> startPlacementAttempt({required String language}) => _placement.startPlacementAttempt(language: language);
  Future<PlacementWordsResponse> getPlacementWords({required int attemptId, required String language, required String level}) => _placement.getPlacementWords(attemptId: attemptId, language: language, level: level);
  Future<PlacementWordEvaluation> evaluatePlacementWords({required int attemptId, required List<int> selectedWordIds}) => _placement.evaluatePlacementWords(attemptId: attemptId, selectedWordIds: selectedWordIds);
  Future<PlacementFinalizeResponse> finalizePlacement({required int attemptId}) => _placement.finalizePlacement(attemptId: attemptId);

  Future<Map<String, dynamic>> createWord({required String word, required String translation}) => _words.createWord(word: word, translation: translation);
  Future<List<dynamic>> getWords() => _words.getWords();
  Future<Map<String, dynamic>> updateWordStatus({required int wordId, required bool learned}) => _words.updateWordStatus(wordId: wordId, learned: learned);
  Future<void> deleteWord({required int wordId}) => _words.deleteWord(wordId: wordId);
  Future<Map<String, dynamic>> getHomeStats() => _stats.getHomeStats();
}
