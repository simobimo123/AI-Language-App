
import 'dart:convert';

import 'package:ai_language_app_flutter/core/errors/api_exception.dart';

import '../../models/placement_models.dart';
import 'api_client.dart';

class PlacementApiService {
  final ApiClient client;

  PlacementApiService(this.client);

  Future<int> startPlacementAttempt({
    required String language,
  }) async {
    final response = await client.post(
      '/placement/attempts',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'language': language,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 || response.statusCode == 201) {
      if (data is! Map || data['attempt_id'] == null) {
        throw const ApiException(
          'Invalid placement attempt response',
        );
      }

      return (data['attempt_id'] as num).toInt();
    }

    throw client.apiException(
      data,
      'Failed to start placement attempt',
      statusCode: response.statusCode,
    );
  }

  Future<PlacementWordsResponse> getPlacementWords({
    required int attemptId,
    required String language,
    required String level,
  }) async {
    final response = await client.get(
      '/placement/words/$language/$level?attempt_id=$attemptId',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 && data is Map) {
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
    required int attemptId,
    required List<int> selectedWordIds,
  }) async {
    final response = await client.post(
      '/placement/attempts/$attemptId/words/evaluate',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'attempt_id': attemptId,
        'selected_word_ids': selectedWordIds,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 && data is Map) {
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
    required int attemptId,
  }) async {
    final response = await client.get(
      '/placement/attempts/$attemptId/quiz',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 && data is Map) {
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
    required int attemptId,
    required String language,
    required String level,
    required Map<int, int> answers,
  }) async {
    final answersList = answers.entries
        .map(
          (entry) => {
            'question_id': entry.key,
            'selected_index': entry.value,
          },
        )
        .toList();

    final response = await client.post(
      '/placement/attempts/$attemptId/quiz/evaluate',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'attempt_id': attemptId,
        'language': language,
        'level': level,
        'answers': answersList,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 && data is Map) {
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
    required int attemptId,
  }) async {
    final response = await client.post(
      '/placement/attempts/$attemptId/finalize',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'attempt_id': attemptId,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 && data is Map) {
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
