import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/config/app_config.dart';
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
      throw Exception('No access token found');
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

  Exception apiException(
    dynamic data,
    String fallback, {
    int? statusCode,
  }) {
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return Exception(detail.toString());
      }

      final message = data['message'];

      if (message != null && message.toString().trim().isNotEmpty) {
        return Exception(message.toString());
      }

      final error = data['error'];

      if (error != null && error.toString().trim().isNotEmpty) {
        return Exception(error.toString());
      }
    }

    if (data is String && data.trim().isNotEmpty) {
      return Exception(data.trim());
    }

    if (statusCode != null) {
      return Exception('$fallback (HTTP $statusCode)');
    }

    return Exception(fallback);
  }

  Future<http.Response> get(
    String path, {
    bool authenticated = false,
    Map<String, String>? headers,
  }) async {
    final requestHeaders = <String, String>{
      ...?headers,
    };

    if (authenticated) {
      requestHeaders['Authorization'] =
          'Bearer ${await getToken()}';
    }

    return http.get(
      Uri.parse('$baseUrl$path'),
      headers: requestHeaders.isEmpty
          ? null
          : requestHeaders,
    );
  }

  Future<http.Response> post(
    String path, {
    dynamic body,
    bool authenticated = false,
    Map<String, String>? headers,
  }) async {
    final requestHeaders = <String, String>{
      ...?headers,
    };

    if (authenticated) {
      requestHeaders['Authorization'] =
          'Bearer ${await getToken()}';
    }

    return http.post(
      Uri.parse('$baseUrl$path'),
      headers: requestHeaders,
      body: body,
    );
  }

  Future<http.Response> put(
    String path, {
    dynamic body,
    bool authenticated = false,
    Map<String, String>? headers,
  }) async {
    final requestHeaders = <String, String>{
      ...?headers,
    };

    if (authenticated) {
      requestHeaders['Authorization'] =
          'Bearer ${await getToken()}';
    }

    return http.put(
      Uri.parse('$baseUrl$path'),
      headers: requestHeaders,
      body: body,
    );
  }

  Future<http.Response> patch(
    String path, {
    dynamic body,
    bool authenticated = false,
    Map<String, String>? headers,
  }) async {
    final requestHeaders = <String, String>{
      ...?headers,
    };

    if (authenticated) {
      requestHeaders['Authorization'] =
          'Bearer ${await getToken()}';
    }

    return http.patch(
      Uri.parse('$baseUrl$path'),
      headers: requestHeaders,
      body: body,
    );
  }

  Future<http.Response> delete(
    String path, {
    bool authenticated = false,
    Map<String, String>? headers,
  }) async {
    final requestHeaders = <String, String>{
      ...?headers,
    };

    if (authenticated) {
      requestHeaders['Authorization'] =
          'Bearer ${await getToken()}';
    }

    return http.delete(
      Uri.parse('$baseUrl$path'),
      headers: requestHeaders.isEmpty
          ? null
          : requestHeaders,
    );
  }

  Map<String, String> get jsonHeaders => {
        'Content-Type': 'application/json',
      };
}