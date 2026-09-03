import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_client.dart';

class LessonHint {
  final String suggestion;
  final String translation;

  const LessonHint({
    required this.suggestion,
    required this.translation,
  });

  factory LessonHint.fromJson(Map<String, dynamic> json) {
    final suggestion = json['suggestion']?.toString().trim() ?? '';
    final translation = json['translation']?.toString().trim() ?? '';

    if (suggestion.isEmpty || translation.isEmpty) {
      throw const FormatException('Invalid lesson hint response.');
    }

    return LessonHint(
      suggestion: suggestion,
      translation: translation,
    );
  }
}

class LessonHintApiService {
  final ApiClient _client;
  final http.Client _httpClient;

  LessonHintApiService(this._client, {http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  Future<LessonHint> getHint({
    required int lessonId,
    required String? conversationId,
  }) async {
    final token = await _client.getToken();

    final response = await _httpClient.post(
      Uri.parse('${ApiClient.baseUrl}/ai/lesson/hint'),
      headers: {
        ..._client.jsonHeaders,
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'lesson_id': lessonId,
        if (conversationId != null && conversationId.isNotEmpty)
          'conversation_id': conversationId,
      }),
    );

    dynamic data;
    try {
      data = jsonDecode(response.body);
    } catch (_) {
      data = response.body;
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _client.apiException(
        data,
        'Failed to get a lesson hint.',
        statusCode: response.statusCode,
      );
    }

    if (data is! Map) {
      throw const FormatException('Invalid lesson hint response.');
    }

    return LessonHint.fromJson(Map<String, dynamic>.from(data));
  }

  void dispose() {
    _httpClient.close();
  }
}
