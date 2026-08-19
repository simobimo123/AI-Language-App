import 'dart:convert';

import 'package:http/http.dart' as http;

import 'storage_service.dart';

class ApiService {
  static const String baseUrl = 'http://192.168.11.106:8000';

  final StorageService storageService = StorageService();

  // =========================
  // Test connection
  // =========================

  Future<String> testConnection() async {
    final response = await http.get(Uri.parse('$baseUrl/'));

    if (response.statusCode == 200) {
      return response.body;
    }

    throw Exception('Failed to connect to backend');
  }

  // =========================
  // Register
  // =========================

  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    required String nativeLanguage,
    required String learningLanguage,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'name': name,
        'email': email,
        'password': password,
        'native_language': nativeLanguage,
        'learning_language': learningLanguage,
      }),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200 || response.statusCode == 201) {
      return data;
    }

    throw Exception(data['detail'] ?? 'Registration failed');
  }

  // =========================
  // Login
  // =========================

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(data['detail'] ?? 'Login failed');
  }

  // =========================
  // Current user
  // =========================

  Future<Map<String, dynamic>> getCurrentUser() async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw Exception('No access token found');
    }

    final response = await http.get(
      Uri.parse('$baseUrl/auth/me'),
      headers: {'Authorization': 'Bearer $token'},
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(data['detail'] ?? 'Failed to get current user');
  }

  // =========================
  // Create word
  // =========================

  Future<Map<String, dynamic>> createWord({
    required String word,
    required String translation,
  }) async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw Exception('No access token found');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/words/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'word': word,
        'translation': translation,
        'learned': false,
      }),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200 || response.statusCode == 201) {
      return data;
    }

    throw Exception(data['detail'] ?? 'Failed to create word');
  }

  // =========================
  // Get words
  // =========================

  Future<List<dynamic>> getWords() async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw Exception('No access token found');
    }

    final response = await http.get(
      Uri.parse('$baseUrl/words/'),
      headers: {'Authorization': 'Bearer $token'},
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(data['detail'] ?? 'Failed to get words');
  }

  // =========================
  // Update word status
  // =========================

  Future<Map<String, dynamic>> updateWordStatus({
    required int wordId,
    required bool learned,
  }) async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw Exception('No access token found');
    }

    final response = await http.patch(
      Uri.parse('$baseUrl/words/$wordId'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({'learned': learned}),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(data['detail'] ?? 'Failed to update word');
  }

  // =========================
  // Delete word
  // =========================

  Future<void> deleteWord({required int wordId}) async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw Exception('No access token found');
    }

    final response = await http.delete(
      Uri.parse('$baseUrl/words/$wordId'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200 || response.statusCode == 204) {
      return;
    }

    final data = jsonDecode(response.body);

    throw Exception(data['detail'] ?? 'Failed to delete word');
  }
}
