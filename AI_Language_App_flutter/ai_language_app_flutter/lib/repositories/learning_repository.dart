import '../services/api/api_service.dart';

class LearningRepository {
  final ApiService apiService;

  LearningRepository({ApiService? apiService}) : apiService = apiService ?? ApiService();

  Future<List<dynamic>> getLearningProfiles() => apiService.getLearningProfiles();
  Future<Map<String, dynamic>> getCurrentLearningProfile() => apiService.getCurrentLearningProfile();

  Future<Map<String, dynamic>> createLearningProfile({required String language, required String level}) =>
      apiService.createLearningProfile(language: language, level: level);

  Future<Map<String, dynamic>> updateLearningProfile({required String language, required String level, required double progress}) =>
      apiService.updateLearningProfile(language: language, level: level, progress: progress);

  Future<Map<String, dynamic>> switchLearningLanguage({required String language}) =>
      apiService.switchLearningLanguage(language: language);

  Future<Map<String, dynamic>> getLearningPath() => apiService.getLearningPath();
  Future<Map<String, dynamic>> getLessonContent({required int lessonId}) => apiService.getLessonContent(lessonId: lessonId);

  Future<Map<String, dynamic>> getLessonAssessment({required int lessonId, required String conversationId}) =>
      apiService.getLessonAssessment(lessonId: lessonId, conversationId: conversationId);

  Future<Map<String, dynamic>> submitLessonAssessment({
    required int lessonId,
    required String conversationId,
    required List<Map<String, String>> answers,
  }) => apiService.submitLessonAssessment(
        lessonId: lessonId,
        conversationId: conversationId,
        answers: answers,
      );

  Future<Map<String, dynamic>> completeLesson({required int lessonId, double score = 100}) =>
      apiService.completeLesson(lessonId: lessonId, score: score);
}
