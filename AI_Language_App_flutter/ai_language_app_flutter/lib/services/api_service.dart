import 'dart:convert';

import 'package:http/http.dart' as http;

import 'storage_service.dart';

class ApiService {
  static const String baseUrl = 'http://192.168.11.106:8000';

  final StorageService storageService = StorageService();

  // =========================================================
  // Helpers
  // =========================================================

  Future<String> _getToken() async {
    final token = await storageService.getToken();

    if (token == null || token.isEmpty) {
      throw Exception('No access token found');
    }

    return token;
  }

  dynamic _decodeResponse(http.Response response) {
    if (response.body.isEmpty) {
      return null;
    }

    try {
      return jsonDecode(response.body);
    } catch (_) {
      return response.body;
    }
  }

  Exception _apiException(
    dynamic data,
    String fallback,
  ) {
    if (data is Map<String, dynamic> &&
        data['detail'] != null) {
      return Exception(
        data['detail'].toString(),
      );
    }

    return Exception(fallback);
  }

  // =========================================================
  // Test connection
  // =========================================================

  Future<String> testConnection() async {
    final response = await http.get(
      Uri.parse('$baseUrl/'),
    );

    if (response.statusCode == 200) {
      return response.body;
    }

    throw Exception(
      'Failed to connect to backend',
    );
  }

  // =========================================================
  // Register
  // =========================================================
  //
  // Registration only creates the account.
  //
  // The user chooses:
  // - App language
  // - Native language
  // - Learning language
  //
  // later in OnboardingPage.
  //
  // The learning level is determined by Placement Test.
  // =========================================================

  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'name': name,
        'email': email,
        'password': password,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Registration failed',
    );
  }

  // =========================================================
  // Login
  // =========================================================

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Login failed',
    );
  }

  // =========================================================
  // Google Login
  // =========================================================

  Future<Map<String, dynamic>> loginWithGoogle({
    required String idToken,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/google'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'id_token': idToken,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Google login failed',
    );
  }

  // =========================================================
  // Current user
  // =========================================================

  Future<Map<String, dynamic>> getCurrentUser() async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse('$baseUrl/auth/me'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to get current user',
    );
  }

  // =========================================================
  // Update current user
  // =========================================================
  //
  // Used by OnboardingPage to save:
  // - Native language
  // - Learning language
  //
  // This does NOT create a LearningProfile.
  // =========================================================

  Future<Map<String, dynamic>> updateCurrentUser({
    required String name,
    required String email,
    required String nativeLanguage,
    required String learningLanguage,
  }) async {
    final token = await _getToken();

    final response = await http.put(
      Uri.parse('$baseUrl/users/me'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'name': name,
        'email': email,
        'native_language': nativeLanguage,
        'learning_language': learningLanguage,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to update current user',
    );
  }

  // =========================================================
  // Get all learning profiles
  // =========================================================

  Future<List<dynamic>> getLearningProfiles() async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse('$baseUrl/learning/profiles'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return List<dynamic>.from(
        data as List,
      );
    }

    throw _apiException(
      data,
      'Failed to get learning profiles',
    );
  }

  // =========================================================
  // Get current learning profile
  // =========================================================

  Future<Map<String, dynamic>>
      getCurrentLearningProfile() async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse('$baseUrl/learning/current'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to get current learning profile',
    );
  }

  // =========================================================
  // Create learning profile
  // =========================================================
  //
  // This should be called only after Placement Test.
  //
  // Normally the Placement Test itself calls finalize,
  // but this endpoint remains available for other flows.
  // =========================================================

  Future<Map<String, dynamic>>
      createLearningProfile({
    required String language,
    required String level,
  }) async {
    final token = await _getToken();

    final response = await http.post(
      Uri.parse('$baseUrl/learning/profiles'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'language': language,
        'level': level,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to create learning profile',
    );
  }

  // =========================================================
  // Update learning profile
  // =========================================================

  Future<Map<String, dynamic>>
      updateLearningProfile({
    required String language,
    required String level,
    required double progress,
  }) async {
    final token = await _getToken();

    final response = await http.put(
      Uri.parse(
        '$baseUrl/learning/profiles/$language',
      ),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'level': level,
        'progress': progress,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to update learning profile',
    );
  }

  // =========================================================
  // Switch current learning language
  // =========================================================

  Future<Map<String, dynamic>>
      switchLearningLanguage({
    required String language,
  }) async {
    final token = await _getToken();

    final response = await http.put(
      Uri.parse(
        '$baseUrl/learning/current/$language',
      ),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to switch learning language',
    );
  }

  // =========================================================
  // Placement - Get words
  // =========================================================
  //
  // Returns exactly 20 random words for the requested level.
  //
  // Initial placement starts at A1.
  // =========================================================

  Future<Map<String, dynamic>>
      getPlacementWords({
    required String language,
    required String level,
  }) async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse(
        '$baseUrl/placement/words/$language/$level',
      ),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to get placement words',
    );
  }

  // =========================================================
  // Placement - Evaluate words
  // =========================================================
  //
  // `presentedWordIds` must contain exactly the 20 words
  // shown to the user.
  //
  // `selectedWordIds` contains the words the user knows.
  // =========================================================

  Future<Map<String, dynamic>>
      evaluatePlacementWords({
    required String language,
    required String level,
    required List<int> presentedWordIds,
    required List<int> selectedWordIds,
  }) async {
    final token = await _getToken();

    final response = await http.post(
      Uri.parse(
        '$baseUrl/placement/words/evaluate',
      ),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'language': language,
        'level': level,
        'presented_word_ids': presentedWordIds,
        'selected_word_ids': selectedWordIds,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to evaluate placement words',
    );
  }

  // =========================================================
  // Placement - Get confirmation quiz
  // =========================================================

  Future<Map<String, dynamic>>
      getPlacementQuiz({
    required String language,
    required String level,
  }) async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse(
        '$baseUrl/placement/quiz/$language/$level',
      ),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to get placement quiz',
    );
  }

  // =========================================================
  // Placement - Evaluate confirmation quiz
  // =========================================================

  Future<Map<String, dynamic>>
      evaluatePlacementQuiz({
    required String language,
    required String level,
    required List<Map<String, int>> answers,
  }) async {
    final token = await _getToken();

    final response = await http.post(
      Uri.parse(
        '$baseUrl/placement/quiz/evaluate',
      ),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'language': language,
        'level': level,
        'answers': answers,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to evaluate placement quiz',
    );
  }

  // =========================================================
  // Placement - Finalize
  // =========================================================
  //
  // This is the final step.
  //
  // The backend creates or updates the LearningProfile and
  // changes the user's current learning language.
  //
  // Possible levels:
  //
  // PRE_A1
  // A1
  // A2
  // B1
  // B2
  // C1
  // C2
  // =========================================================

  Future<Map<String, dynamic>>
      finalizePlacement({
    required String language,
    required String level,
  }) async {
    final token = await _getToken();

    final response = await http.post(
      Uri.parse(
        '$baseUrl/placement/finalize',
      ),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'language': language,
        'level': level,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to finalize placement',
    );
  }

  // =========================================================
  // Get learning path
  // =========================================================

  Future<Map<String, dynamic>>
      getLearningPath() async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse(
        '$baseUrl/learning/path',
      ),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to get learning path',
    );
  }

  // =========================================================
  // Complete lesson
  // =========================================================

  Future<Map<String, dynamic>>
      completeLesson({
    required int lessonId,
    double score = 100,
  }) async {
    final token = await _getToken();

    final response = await http.post(
      Uri.parse(
        '$baseUrl/learning/lessons/$lessonId/complete',
      ),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'score': score,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to complete lesson',
    );
  }

  // =========================================================
  // Create word
  // =========================================================

  Future<Map<String, dynamic>> createWord({
    required String word,
    required String translation,
  }) async {
    final token = await _getToken();

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

    final data = _decodeResponse(response);

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to create word',
    );
  }

  // =========================================================
  // Get words
  // =========================================================

  Future<List<dynamic>> getWords() async {
    final token = await _getToken();

    final response = await http.get(
      Uri.parse('$baseUrl/words/'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return List<dynamic>.from(
        data as List,
      );
    }

    throw _apiException(
      data,
      'Failed to get words',
    );
  }

  // =========================================================
  // Update word status
  // =========================================================

  Future<Map<String, dynamic>>
      updateWordStatus({
    required int wordId,
    required bool learned,
  }) async {
    final token = await _getToken();

    final response = await http.patch(
      Uri.parse('$baseUrl/words/$wordId'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'learned': learned,
      }),
    );

    final data = _decodeResponse(response);

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(
        data as Map,
      );
    }

    throw _apiException(
      data,
      'Failed to update word',
    );
  }

  // =========================================================
  // Delete word
  // =========================================================

  Future<void> deleteWord({
    required int wordId,
  }) async {
    final token = await _getToken();

    final response = await http.delete(
      Uri.parse('$baseUrl/words/$wordId'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200 ||
        response.statusCode == 204) {
      return;
    }

    final data = _decodeResponse(response);

    throw _apiException(
      data,
      'Failed to delete word',
    );
  }
}