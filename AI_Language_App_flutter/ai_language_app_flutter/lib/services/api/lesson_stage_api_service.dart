import 'package:http/http.dart' as http;

import 'api_client.dart';

class LessonStageApiService {
  final ApiClient _client;

  LessonStageApiService(this._client);

  Future<Map<String, dynamic>> getStages({required int lessonId}) async {
    final response = await _client.get('/lessons/$lessonId/stages');
    final data = _client.decodeResponse(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _client.apiException(
        data,
        'Failed to load lesson stages.',
        statusCode: response.statusCode,
      );
    }
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> completeStage({
    required int lessonId,
    required String stage,
    String? conversationId,
  }) async {
    final token = await _client.getToken();
    final response = await _client.post(
      '/lessons/$lessonId/stages/complete',
      headers: {
        ..._client.jsonHeaders,
        if (token != null && token.isNotEmpty)
          'Authorization': 'Bearer $token',
      },
      body: {
        'stage': stage,
        if (conversationId != null && conversationId.isNotEmpty)
          'conversation_id': conversationId,
      },
    );
    final data = _client.decodeResponse(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _client.apiException(
        data,
        'Failed to save lesson stage.',
        statusCode: response.statusCode,
      );
    }
    return Map<String, dynamic>.from(data as Map);
  }
}
