import 'dart:convert';

import '../api/api_client.dart';

class WordApiService {
  final ApiClient client;

  WordApiService(this.client);

  Future<Map<String, dynamic>> createWord({
    required String word,
    required String translation,
  }) async {
    final response = await client.post(
      '/words/',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'word': word,
        'translation': translation,
        'learned': false,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to create word',
      statusCode: response.statusCode,
    );
  }

  Future<List<dynamic>> getWords() async {
    final response = await client.get(
      '/words/',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return List<dynamic>.from(data as List);
    }

    throw client.apiException(
      data,
      'Failed to get words',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> updateWordStatus({
    required int wordId,
    required bool learned,
  }) async {
    final response = await client.patch(
      '/words/$wordId',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'learned': learned,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to update word',
      statusCode: response.statusCode,
    );
  }

  Future<void> deleteWord({
    required int wordId,
  }) async {
    final response = await client.delete(
      '/words/$wordId',
      authenticated: true,
    );

    if (response.statusCode == 200 ||
        response.statusCode == 204) {
      return;
    }

    final data = client.decodeResponse(response);

    throw client.apiException(
      data,
      'Failed to delete word',
      statusCode: response.statusCode,
    );
  }
}