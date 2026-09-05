import 'dart:async' as async;
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/config/app_config.dart';
import '../../core/errors/api_exception.dart';
import '../../core/storage/storage_service.dart';

class ApiClient {
  static const String baseUrl = AppConfig.baseUrl;

  final StorageService storageService;

  ApiClient({
    StorageService? storageService,
  }) : storageService = storageService ?? StorageService();

  Future<String> getToken() async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw const ApiException('No access token found');
    }

    return token;
  }

  dynamic decodeResponse(http.Response response) {
    if (response.body.isEmpty) {
      return null;
    }

    try {
      return jsonDecode(response.body);
    } catch (_) {
      return response.body;
    }
  }

  ApiException apiException(
    dynamic data,
    String fallback, {
    int? statusCode,
  }) {
    String message = fallback;

    if (data is Map) {
      final detail = data['detail'];
      final apiMessage = data['message'];
      final error = data['error'];
      final value = detail ?? apiMessage ?? error;

      if (value != null && value.toString().trim().isNotEmpty) {
        message = value.toString().trim();
      }
    } else if (data is String && data.trim().isNotEmpty) {
      message = data.trim();
    }

    return ApiException(
      message,
      statusCode: statusCode,
    );
  }

  Future<http.Response> _send(
    Future<http.Response> Function(Map<String, String> headers) request, {
    bool authenticated = false,
    Map<String, String>? headers,
  }) async {
    final requestHeaders = <String, String>{
      ...?headers,
    };

    if (authenticated) {
      requestHeaders['Authorization'] = 'Bearer ${await getToken()}';
    }

    try {
      final response = await request(requestHeaders).timeout(
        const Duration(seconds: 30),
      );

      if (authenticated) {
        if (response.statusCode == 401) {
          await storageService.deleteToken();
          throw const ApiException(
            'Session expired. Please login again.',
            statusCode: 401,
          );
        }
      }

      return response;
    } on async.TimeoutException catch (e) {
      throw TimeoutException(cause: e);
    } on http.ClientException catch (e) {
      throw NetworkException(
        'Unable to connect to the server. Please check your internet connection.',
        cause: e,
      );
    } on ApiException {
      rethrow;
    } catch (e) {
      throw NetworkException(
        'A network error occurred. Please try again.',
        cause: e,
      );
    }
  }

  Future<http.Response> get(
    String path, {
    bool authenticated = false,
    Map<String, String>? headers,
  }) {
    return _send(
      (requestHeaders) => http.get(
        Uri.parse('$baseUrl$path'),
        headers: requestHeaders.isEmpty ? null : requestHeaders,
      ),
      authenticated: authenticated,
      headers: headers,
    );
  }

  Future<http.Response> post(
    String path, {
    dynamic body,
    bool authenticated = false,
    Map<String, String>? headers,
  }) {
    return _send(
      (requestHeaders) => http.post(
        Uri.parse('$baseUrl$path'),
        headers: requestHeaders,
        body: body,
      ),
      authenticated: authenticated,
      headers: headers,
    );
  }

  Future<http.Response> put(
    String path, {
    dynamic body,
    bool authenticated = false,
    Map<String, String>? headers,
  }) {
    return _send(
      (requestHeaders) => http.put(
        Uri.parse('$baseUrl$path'),
        headers: requestHeaders,
        body: body,
      ),
      authenticated: authenticated,
      headers: headers,
    );
  }

  Future<http.Response> patch(
    String path, {
    dynamic body,
    bool authenticated = false,
    Map<String, String>? headers,
  }) {
    return _send(
      (requestHeaders) => http.patch(
        Uri.parse('$baseUrl$path'),
        headers: requestHeaders,
        body: body,
      ),
      authenticated: authenticated,
      headers: headers,
    );
  }

  Future<http.Response> delete(
    String path, {
    bool authenticated = false,
    Map<String, String>? headers,
  }) {
    return _send(
      (requestHeaders) => http.delete(
        Uri.parse('$baseUrl$path'),
        headers: requestHeaders.isEmpty ? null : requestHeaders,
      ),
      authenticated: authenticated,
      headers: headers,
    );
  }

  Map<String, String> get jsonHeaders => {
        'Content-Type': 'application/json',
      };
}
