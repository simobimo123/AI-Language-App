import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/errors/api_exception.dart';
import 'api_client.dart';

class LessonStageAiChunk {
  final String type;
  final String? text;
  final String? conversationId;
  final String? action;
  final String? targetId;
  final double? confidence;
  final bool axisCompleted;
  final bool lessonCompleted;
  final String? message;

  const LessonStageAiChunk({
    required this.type,
    this.text,
    this.conversationId,
    this.action,
    this.targetId,
    this.confidence,
    this.axisCompleted = false,
    this.lessonCompleted = false,
    this.message,
  });

  factory LessonStageAiChunk.fromJson(Map<String, dynamic> json) {
    final rawConfidence = json['confidence'];
    return LessonStageAiChunk(
      type: json['type']?.toString() ?? 'unknown',
      text: json['text']?.toString(),
      conversationId: json['conversation_id']?.toString(),
      action: json['action']?.toString(),
      targetId: json['target_id']?.toString(),
      confidence: rawConfidence is num ? rawConfidence.toDouble() : double.tryParse(rawConfidence?.toString() ?? ''),
      axisCompleted: json['axis_completed'] == true,
      lessonCompleted: json['lesson_completed'] == true,
      message: json['message']?.toString(),
    );
  }
}

class LessonStageAiApiService {
  final ApiClient _client;

  LessonStageAiApiService(this._client);

  Stream<LessonStageAiChunk> chat({
    required int lessonId,
    required String stage,
    required String message,
    String? conversationId,
  }) async* {
    final token = await _client.getToken();
    final request = http.Request(
      'POST',
      Uri.parse('${ApiClient.baseUrl}/ai/lesson/stage-chat'),
    );

    request.headers.addAll({
      ..._client.jsonHeaders,
      'Authorization': 'Bearer $token',
      'Accept': 'text/event-stream',
    });
    request.body = jsonEncode({
      'lesson_id': lessonId,
      'stage': stage,
      'message': message,
      if (conversationId != null && conversationId.isNotEmpty)
        'conversation_id': conversationId,
    });

    final client = http.Client();
    try {
      late final http.StreamedResponse response;
      try {
        response = await client.send(request).timeout(const Duration(seconds: 60));
      } on TimeoutException {
        throw NetworkException('The connection timed out. Please try again.');
      } on http.ClientException catch (e) {
        throw NetworkException('Unable to connect to the server.', cause: e);
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

      String? eventName;
      final dataLines = <String>[];

      LessonStageAiChunk? parseEvent() {
        if (dataLines.isEmpty) return null;
        final payload = dataLines.join('\n');
        dataLines.clear();
        try {
          final decoded = jsonDecode(payload);
          if (decoded is Map) {
            final map = Map<String, dynamic>.from(decoded);
            map['type'] ??= eventName ?? 'unknown';
            return LessonStageAiChunk.fromJson(map);
          }
        } catch (_) {
          if (eventName != null) {
            return LessonStageAiChunk(type: eventName!, text: payload);
          }
        } finally {
          eventName = null;
        }
        return null;
      }

      await for (final line in response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (line.startsWith('event:')) {
          eventName = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.add(line.substring(5).trimLeft());
        } else if (line.isEmpty && dataLines.isNotEmpty) {
          final chunk = parseEvent();
          if (chunk != null) yield chunk;
        }
      }

      if (dataLines.isNotEmpty) {
        final chunk = parseEvent();
        if (chunk != null) yield chunk;
      }
    } finally {
      client.close();
    }
  }
}
