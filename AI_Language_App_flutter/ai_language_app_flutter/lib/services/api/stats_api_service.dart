import '../../core/errors/api_exception.dart';
import 'api_client.dart';

class StatsApiService {
  final ApiClient client;

  StatsApiService(this.client);

  Future<Map<String, dynamic>> getHomeStats() async {
    final response = await client.get(
      '/stats',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      if (data is Map<String, dynamic>) {
        return data;
      }

      if (data is Map) {
        return Map<String, dynamic>.from(data);
      }

      throw const ApiException(
        'Invalid response format from home stats endpoint',
      );
    }

    throw client.apiException(
      data,
      'Failed to get home statistics',
      statusCode: response.statusCode,
    );
  }
}
