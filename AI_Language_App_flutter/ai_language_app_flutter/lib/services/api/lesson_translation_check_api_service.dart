import 'dart:convert';

import 'api_client.dart';

class LessonTranslationQuestion {
  final String id;
  final String sentence;

  const LessonTranslationQuestion({
    required this.id,
    required this.sentence,
  });

  factory LessonTranslationQuestion.fromJson(Map<String, dynamic> json) {
    return LessonTranslationQuestion(
      id: json['id']?.toString() ?? '',
      sentence: json['sentence']?.toString() ?? '',
    );
  }
}

class LessonTranslationCheckResult {
  final int lessonId;
  final String conversationId;
  final double score;
  final bool passed;
  final int correctCount;
  final int totalQuestions;
  final List<Map<String, dynamic>> results;

  const LessonTranslationCheckResult({
    required this.lessonId,
    required this.conversationId,
    required this.score,
    required this.passed,
    required this.correctCount,
    required this.totalQuestions,
    required this.results,
  });

  factory LessonTranslationCheckResult.fromJson(Map<String, dynamic> json) {
    final rawResults = json['results'];
    final parsedResults = rawResults is List
        ? rawResults.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList()
        : <Map<String, dynamic>>[];

    return LessonTranslationCheckResult(
      lessonId: int.tryParse(json['lesson_id']?.toString() ?? '') ?? 0,
      conversationId: json['conversation_id']?.toString() ?? '',
      score: double.tryParse(json['score']?.toString() ?? '') ?? 0,
      passed: json['passed'] == true,
      correctCount: int.tryParse(json['correct_count']?.toString() ?? '') ?? 0,
      totalQuestions: int.tryParse(json['total_questions']?.toString() ?? '') ?? 0,
      results: parsedResults,
    );
  }
}

class LessonTranslationCheckApiService {
  final ApiClient _client;

  LessonTranslationCheckApiService(this._client);

  Future<Map<String, dynamic>> getQuestions({
    required int lessonId,
    required String conversationId,
  }) async {
    final response = await _client.get(
      '/learning/lessons/$lessonId/translation-check',
      authenticated: true,
      headers: {
        'conversation_id': conversationId,
      },
    );

    final data = _client.decodeResponse(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _client.apiException(
        data,
        'Failed to load the translation check.',
        statusCode: response.statusCode,
      );
    }
    return Map<String, dynamic>.from(data as Map);
  }

  Future<LessonTranslationCheckResult> submit({
    required int lessonId,
    required String conversationId,
    required List<Map<String, String>> answers,
  }) async {
    final response = await _client.post(
      '/learning/lessons/$lessonId/translation-check',
      authenticated: true,
      headers: _client.jsonHeaders,
      body: jsonEncode({
        'conversation_id': conversationId,
        'answers': answers,
      }),
    );

    final data = _client.decodeResponse(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _client.apiException(
        data,
        'Failed to evaluate the translation check.',
        statusCode: response.statusCode,
      );
    }

    return LessonTranslationCheckResult.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }
}
