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
  final bool? lessonReady;
  final String? message;
  final List<Map<String, String>>? history;

  const LessonAiChunk({
    required this.type,
    this.text,
    this.conversationId,
    this.dailyLimit,
    this.dailyUsed,
    this.dailyRemaining,
    this.lessonReady,
    this.message,
    this.history,
  });

  factory LessonAiChunk.fromJson(Map<String, dynamic> json) {
    List<Map<String, String>>? parsedHistory;
    final rawHistory = json['history'];

    if (rawHistory is List) {
      parsedHistory = rawHistory
          .whereType<Map>()
          .map(
            (item) => {
              'role': item['role']?.toString() ?? 'assistant',
              'text': item['text']?.toString() ?? '',
            },
          )
          .where((item) => item['text']!.isNotEmpty)
          .toList();
    }

    return LessonAiChunk(
      type: json['type']?.toString() ?? 'unknown',
      text: json['text']?.toString(),
      conversationId: json['conversation_id']?.toString(),
      dailyLimit: _toInt(json['daily_limit']),
      dailyUsed: _toInt(json['daily_used']),
      dailyRemaining: _toInt(json['daily_remaining']),
      lessonReady: json['lesson_ready'] == true,
      message: json['message']?.toString(),
      history: parsedHistory,
    );
  }

  static int? _toInt(dynamic value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '');
  }
}

class _CachedLessonConversation {
  String? conversationId;
  final List<Map<String, String>> messages;

  _CachedLessonConversation({
    List<Map<String, String>>? messages,
  }) : messages = messages ?? [];
}

class LessonAiApiService {
  final ApiClient _client;
  final http.Client _httpClient;

  static final Map<int, _CachedLessonConversation> _sessionCache = {};

  LessonAiApiService(this._client, {http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  Stream<LessonAiChunk> chat({
    required int lessonId,
    required String message,
    required String? conversationId,
  }) async* {
    final cached = _sessionCache[lessonId];

    if (message == 'START_LESSON' &&
        cached != null &&
        cached.messages.isNotEmpty) {
      yield LessonAiChunk(
        type: 'conversation',
        conversationId: cached.conversationId,
      );

      yield LessonAiChunk(
        type: 'history',
        conversationId: cached.conversationId,
        history: List<Map<String, String>>.from(cached.messages),
      );

      return;
    }

    final token = await _client.getToken();

    final effectiveConversationId =
        conversationId ?? cached?.conversationId;

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
      if (effectiveConversationId != null &&
          effectiveConversationId.isNotEmpty)
        'conversation_id': effectiveConversationId,
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
    String? streamedConversationId = effectiveConversationId;
    final streamedAssistantText = StringBuffer();

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

        if (chunk != null) {
          if (chunk.conversationId != null &&
              chunk.conversationId!.isNotEmpty) {
            streamedConversationId = chunk.conversationId;
          }

          if (chunk.type == 'chunk' && chunk.text != null) {
            streamedAssistantText.write(chunk.text);
          }

          if (chunk.type == 'done') {
            _storeCompletedTurn(
              lessonId: lessonId,
              conversationId: streamedConversationId,
              userMessage: message,
              assistantMessage: streamedAssistantText.toString(),
            );
          }

          yield chunk;
        }
      }
    }

    if (dataLines.isNotEmpty) {
      final chunk = _parseEvent(
        dataLines.join('\n'),
        fallbackType: pendingEvent,
      );

      if (chunk != null) {
        if (chunk.conversationId != null &&
            chunk.conversationId!.isNotEmpty) {
          streamedConversationId = chunk.conversationId;
        }

        if (chunk.type == 'chunk' && chunk.text != null) {
          streamedAssistantText.write(chunk.text);
        }

        if (chunk.type == 'done') {
          _storeCompletedTurn(
            lessonId: lessonId,
            conversationId: streamedConversationId,
            userMessage: message,
            assistantMessage: streamedAssistantText.toString(),
          );
        }

        yield chunk;
      }
    }
  }

  void _storeCompletedTurn({
    required int lessonId,
    required String? conversationId,
    required String userMessage,
    required String assistantMessage,
  }) {
    if (assistantMessage.trim().isEmpty) return;

    final cached = _sessionCache.putIfAbsent(
      lessonId,
      () => _CachedLessonConversation(),
    );

    if (conversationId != null && conversationId.isNotEmpty) {
      cached.conversationId = conversationId;
    }

    if (userMessage != 'START_LESSON') {
      cached.messages.add({
        'role': 'user',
        'text': userMessage,
      });
    }

    cached.messages.add({
      'role': 'assistant',
      'text': assistantMessage,
    });
  }

  LessonAiChunk? _parseEvent(
    String payload, {
    String? fallbackType,
  }) {
    if (payload.isEmpty || payload == '[DONE]') return null;

    try {
      final decoded = jsonDecode(payload);

      if (decoded is Map) {
        return LessonAiChunk.fromJson(
          Map<String, dynamic>.from(decoded),
        );
      }
    } catch (_) {
      if (fallbackType != null && fallbackType.isNotEmpty) {
        return LessonAiChunk(
          type: fallbackType,
          text: payload,
        );
      }
    }

    return null;
  }

  void dispose() {
    _httpClient.close();
  }
}
