import '../services/api/api_service.dart';

class LearningRepository {
  final ApiService apiService;

  LearningRepository({
    ApiService? apiService,
  }) : apiService = apiService ?? ApiService();

  Future<List<dynamic>> getLearningProfiles() {
    return apiService.getLearningProfiles();
  }

  Future<Map<String, dynamic>> getCurrentLearningProfile() {
    return apiService.getCurrentLearningProfile();
  }

  Future<Map<String, dynamic>> createLearningProfile({
    required String language,
    required String level,
  }) {
    return apiService.createLearningProfile(
      language: language,
      level: level,
    );
  }

  Future<Map<String, dynamic>> updateLearningProfile({
    required String language,
    required String level,
    required double progress,
  }) {
    return apiService.updateLearningProfile(
      language: language,
      level: level,
      progress: progress,
    );
  }

  Future<Map<String, dynamic>> switchLearningLanguage({
    required String language,
  }) {
    return apiService.switchLearningLanguage(
      language: language,
    );
  }

  Future<Map<String, dynamic>> getLearningPath() {
    return apiService.getLearningPath();
  }

  Future<Map<String, dynamic>> getLessonContent({required int lessonId}) {
    return apiService.getLessonContent(lessonId: lessonId);
  }

  Future<Map<String, dynamic>> completeLesson({
    required int lessonId,
    double score = 100,
  }) {
    return apiService.completeLesson(
      lessonId: lessonId,
      score: score,
    );
  }
}
