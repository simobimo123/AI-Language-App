import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/errors/api_exception.dart';
import 'api_client.dart';

class LessonAiChunk {
  final String type;
  final String? text;
  final String? conversationId;
  final int? dailyLimit;
  final int? dailyUsed;
  final int? dailyRemaining;
  final String? message;

  const LessonAiChunk({
    required this.type,
    this.text,
    this.conversationId,
    this.dailyLimit,
    this.dailyUsed,
    this.dailyRemaining,
    this.message,
  });

  factory LessonAiChunk.fromJson(Map<String, dynamic> json) {
    return LessonAiChunk(
      type: json['type']?.toString() ?? 'unknown',
      text: json['text']?.toString(),
      conversationId: json['conversation_id']?.toString(),
      dailyLimit: _toInt(json['daily_limit']),
      dailyUsed: _toInt(json['daily_used']),
      dailyRemaining: _toInt(json['daily_remaining']),
      message: json['message']?.toString(),
    );
  }

  static int? _toInt(dynamic value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '');
  }
}

class LessonAiApiService {
  final ApiClient _client;
  final http.Client _httpClient;

  LessonAiApiService(this._client, {http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  Stream<LessonAiChunk> chat({
    required int lessonId,
    required String message,
    String? conversationId,
  }) async* {
    final token = await _client.getToken();

    final request = http.Request(
      'POST',
      Uri.parse('${ApiClient.baseUrl}/ai/lesson/chat'),
    );

    request.headers.addAll({
      ..._client.jsonHeaders,
      'Authorization': 'Bearer $token',
      'Accept': 'text/event-stream',
    });

    request.body = jsonEncode({
      'lesson_id': lessonId,
      'message': message,
      if (conversationId != null && conversationId.isNotEmpty)
        'conversation_id': conversationId,
    });

    late final http.StreamedResponse response;
    try {
      response = await _httpClient.send(request);
    } on http.ClientException catch (e) {
      throw NetworkException(
        'Unable to connect to the server. Please check your internet connection.',
        cause: e,
      );
    } catch (e) {
      throw NetworkException(
        'A network error occurred. Please try again.',
        cause: e,
      );
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final body = await response.stream.bytesToString();
      dynamic data;
      try {
        data = jsonDecode(body);
      } catch (_) {
        data = body;
      }
      throw _client.apiException(
        data,
        'Failed to contact the AI tutor.',
        statusCode: response.statusCode,
      );
    }

    String? pendingEvent;
    final dataLines = <String>[];

    await for (final line in response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())) {
      if (line.startsWith('event:')) {
        pendingEvent = line.substring(6).trim();
        continue;
      }

      if (line.startsWith('data:')) {
        dataLines.add(line.substring(5).trimLeft());
        continue;
      }

      if (line.isEmpty && dataLines.isNotEmpty) {
        final chunk = _parseEvent(
          dataLines.join('\n'),
          fallbackType: pendingEvent,
        );
        dataLines.clear();
        pendingEvent = null;
        if (chunk != null) yield chunk;
      }
    }

    if (dataLines.isNotEmpty) {
      final chunk = _parseEvent(
        dataLines.join('\n'),
        fallbackType: pendingEvent,
      );
      if (chunk != null) yield chunk;
    }
  }

  LessonAiChunk? _parseEvent(String payload, {String? fallbackType}) {
    if (payload.isEmpty || payload == '[DONE]') return null;

    try {
      final decoded = jsonDecode(payload);
      if (decoded is Map) {
        return LessonAiChunk.fromJson(Map<String, dynamic>.from(decoded));
      }
    } catch (_) {
      if (fallbackType != null && fallbackType.isNotEmpty) {
        return LessonAiChunk(type: fallbackType, text: payload);
      }
    }
    return null;
  }

  void dispose() => _httpClient.close();
}
