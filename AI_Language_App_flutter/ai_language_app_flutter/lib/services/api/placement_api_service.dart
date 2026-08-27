import 'dart:convert';

import '../api/api_client.dart';

class PlacementApiService {
  final ApiClient client;

  PlacementApiService(this.client);

  Future<Map<String, dynamic>> getPlacementWords({
    required String language,
    required String level,
  }) async {
    final response = await client.get(
      '/placement/words/$language/$level',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to get placement words',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> evaluatePlacementWords({
    required String language,
    required String level,
    required List<int> presentedWordIds,
    required List<int> selectedWordIds,
  }) async {
    final response = await client.post(
      '/placement/words/evaluate',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'language': language,
        'level': level,
        'presented_word_ids': presentedWordIds,
        'selected_word_ids': selectedWordIds,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to evaluate placement words',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> getPlacementQuiz({
    required String language,
    required String level,
  }) async {
    final response = await client.get(
      '/placement/quiz/$language/$level',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to get placement quiz',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> evaluatePlacementQuiz({
    required String language,
    required String level,
    required List<Map<String, int>> answers,
  }) async {
    final response = await client.post(
      '/placement/quiz/evaluate',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'language': language,
        'level': level,
        'answers': answers,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to evaluate placement quiz',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> finalizePlacement({
    required String language,
    required String level,
  }) async {
    final response = await client.post(
      '/placement/finalize',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'language': language,
        'level': level,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to finalize placement',
      statusCode: response.statusCode,
    );
  }
}