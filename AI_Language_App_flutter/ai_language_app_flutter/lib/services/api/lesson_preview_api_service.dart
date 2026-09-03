import 'api_client.dart';

class LessonPreviewApiService {
  final ApiClient client;

  LessonPreviewApiService(this.client);

  Future<Map<String, dynamic>> getLessonPreview({required int lessonId}) async {
    final response = await client.get(
      '/lesson-preview/$lessonId',
      authenticated: true,
    );
    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to get lesson preview',
      statusCode: response.statusCode,
    );
  }
}
