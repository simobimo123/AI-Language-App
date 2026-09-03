import 'dart:convert';

import 'api_client.dart';

class TranslationApiService {
  final ApiClient client;

  TranslationApiService(this.client);

  Future<String> translate({required String text}) async {
    final response = await client.post(
      '/ai/translation/',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({'text': text}),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 && data is Map) {
      final translation = data['translation']?.toString().trim();
      if (translation != null && translation.isNotEmpty) {
        return translation;
      }
    }

    throw client.apiException(
      data,
      'Failed to translate text',
      statusCode: response.statusCode,
    );
  }
}
