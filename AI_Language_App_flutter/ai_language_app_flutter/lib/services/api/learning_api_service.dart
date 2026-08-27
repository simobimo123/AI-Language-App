import 'dart:convert';

import '../api/api_client.dart';

class LearningApiService {
  final ApiClient client;

  LearningApiService(this.client);

  Future<List<dynamic>> getLearningProfiles() async {
    final response = await client.get(
      '/learning/profiles',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return List<dynamic>.from(data as List);
    }

    throw client.apiException(
      data,
      'Failed to get learning profiles',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> getCurrentLearningProfile() async {
    final response = await client.get(
      '/learning/current',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to get current learning profile',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> createLearningProfile({
    required String language,
    required String level,
  }) async {
    final response = await client.post(
      '/learning/profiles',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'language': language,
        'level': level,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to create learning profile',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> updateLearningProfile({
    required String language,
    required String level,
    required double progress,
  }) async {
    final response = await client.put(
      '/learning/profiles/$language',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'level': level,
        'progress': progress,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to update learning profile',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> switchLearningLanguage({
    required String language,
  }) async {
    final response = await client.put(
      '/learning/current/$language',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to switch learning language',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> getLearningPath() async {
    final response = await client.get(
      '/learning/path',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to get learning path',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> completeLesson({
    required int lessonId,
    double score = 100,
  }) async {
    final response = await client.post(
      '/learning/lessons/$lessonId/complete',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'score': score,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to complete lesson',
      statusCode: response.statusCode,
    );
  }
}