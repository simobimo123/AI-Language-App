import 'dart:convert';
import 'dart:typed_data';

import 'api_client.dart';

class TtsApiService {
  final ApiClient _client;

  TtsApiService(this._client);

  Future<Uint8List> synthesize({
    required String text,
    String? learningLanguage,
    String? nativeLanguage,
    String? gender,
  }) async {
    final payload = <String, dynamic>{
      'text': text,
      if (learningLanguage != null && learningLanguage.isNotEmpty)
        'learning_language': learningLanguage,
      if (nativeLanguage != null && nativeLanguage.isNotEmpty)
        'native_language': nativeLanguage,
      if (gender != null) 'gender': gender,
    };

    final response = await _client.post(
      '/ai/tts/',
      authenticated: true,
      headers: _client.jsonHeaders,
      body: jsonEncode(payload),
    );

    if (response.statusCode != 200) {
      final data = _client.decodeResponse(response);
      throw _client.apiException(
        data,
        'Unable to generate speech.',
        statusCode: response.statusCode,
      );
    }

    if (response.bodyBytes.isEmpty) {
      throw _client.apiException(
        null,
        'The TTS server returned empty audio.',
        statusCode: response.statusCode,
      );
    }

    return response.bodyBytes;
  }
}
