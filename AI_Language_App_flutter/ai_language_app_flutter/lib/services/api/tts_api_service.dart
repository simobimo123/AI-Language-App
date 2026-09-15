import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';

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

    debugPrint(
      '[TTS][API] Requesting speech for ${text.length} characters.',
    );

    final response = await _client.post(
      '/ai/tts/',
      authenticated: true,
      headers: _client.jsonHeaders,
      body: jsonEncode(payload),
    );

    final contentType = response.headers['content-type'] ?? '';
    debugPrint(
      '[TTS][API] status=${response.statusCode}, '
      'content-type=$contentType, bytes=${response.bodyBytes.length}.',
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

    if (response.bodyBytes.length < 12 ||
        String.fromCharCodes(response.bodyBytes.sublist(0, 4)) != 'RIFF' ||
        String.fromCharCodes(response.bodyBytes.sublist(8, 12)) != 'WAVE') {
      throw StateError(
        'The TTS server returned invalid WAV audio.',
      );
    }

    return response.bodyBytes;
  }
}
