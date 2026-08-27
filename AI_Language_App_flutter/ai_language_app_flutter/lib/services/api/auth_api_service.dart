import 'dart:convert';

import '../api/api_client.dart';

class AuthApiService {
  final ApiClient client;

  AuthApiService(this.client);

  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
  }) async {
    final response = await client.post(
      '/users',
      headers: client.jsonHeaders,
      body: jsonEncode({
        'name': name,
        'email': email,
        'password': password,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Registration failed',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await client.post(
      '/auth/login',
      headers: client.jsonHeaders,
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Login failed',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> loginWithGoogle({
    required String idToken,
  }) async {
    final response = await client.post(
      '/auth/google',
      headers: client.jsonHeaders,
      body: jsonEncode({
        'id_token': idToken,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Google login failed',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    final response = await client.get(
      '/auth/me',
      authenticated: true,
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to get current user',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> updateCurrentUser({
    required String name,
    required String email,
    required String nativeLanguage,
    required String learningLanguage,
  }) async {
    final response = await client.put(
      '/users/me',
      authenticated: true,
      headers: client.jsonHeaders,
      body: jsonEncode({
        'name': name,
        'email': email,
        'native_language': nativeLanguage,
        'learning_language': learningLanguage,
      }),
    );

    final data = client.decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(data as Map);
    }

    throw client.apiException(
      data,
      'Failed to update current user',
      statusCode: response.statusCode,
    );
  }
}