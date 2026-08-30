import 'dart:convert';

import '../../models/placement_models.dart';
import 'api_client.dart';

class PlacementApiService {
  final ApiClient client;

  PlacementApiService(this.client);

  Future<PlacementWordsResponse> getPlacementWords({
    required String language,
    required String level,
  }) async {
    final response = await client.get(
      '/placement/words/$language/$level',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      if (data is! Map) {
        throw const ApiException('Invalid placement words response');
      }

      return PlacementWordsResponse.fromJson(
        Map<String, dynamic>.from(data),
      );
    }

    throw client.apiException(
      data,
      'Failed to get placement words',
      statusCode: response.statusCode,
    );
  }

  Future<PlacementWordEvaluation> evaluatePlacementWords({
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
      if (data is! Map) {
        throw const ApiException('Invalid placement word evaluation response');
      }

      return PlacementWordEvaluation.fromJson(
        Map<String, dynamic>.from(data),
      );
    }

    throw client.apiException(
      data,
      'Failed to evaluate placement words',
      statusCode: response.statusCode,
    );
  }

  Future<PlacementQuizResponse> getPlacementQuiz({
    required String language,
    required String level,
  }) async {
    final response = await client.get(
      '/placement/quiz/$language/$level',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      if (data is! Map) {
        throw const ApiException('Invalid placement quiz response');
      }

      return PlacementQuizResponse.fromJson(
        Map<String, dynamic>.from(data),
      );
    }

    throw client.apiException(
      data,
      'Failed to get placement quiz',
      statusCode: response.statusCode,
    );
  }

  Future<PlacementQuizEvaluation> evaluatePlacementQuiz({
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
      if (data is! Map) {
        throw const ApiException('Invalid placement quiz evaluation response');
      }

      return PlacementQuizEvaluation.fromJson(
        Map<String, dynamic>.from(data),
      );
    }

    throw client.apiException(
      data,
      'Failed to evaluate placement quiz',
      statusCode: response.statusCode,
    );
  }

  Future<PlacementFinalizeResponse> finalizePlacement({
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
      if (data is! Map) {
        throw const ApiException('Invalid placement finalize response');
      }

      return PlacementFinalizeResponse.fromJson(
        Map<String, dynamic>.from(data),
      );
    }

    throw client.apiException(
      data,
      'Failed to finalize placement',
      statusCode: response.statusCode,
    );
  }
}