import '../services/api/api_service.dart';

class AuthRepository {
  final ApiService apiService;

  AuthRepository({
    ApiService? apiService,
  }) : apiService = apiService ?? ApiService();

  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
  }) {
    return apiService.register(
      name: name,
      email: email,
      password: password,
    );
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) {
    return apiService.login(
      email: email,
      password: password,
    );
  }

  Future<Map<String, dynamic>> loginWithGoogle({
    required String idToken,
  }) {
    return apiService.loginWithGoogle(
      idToken: idToken,
    );
  }

  Future<Map<String, dynamic>> getCurrentUser() {
    return apiService.getCurrentUser();
  }

  Future<Map<String, dynamic>> updateCurrentUser({
    required String name,
    required String email,
    required String nativeLanguage,
    required String learningLanguage,
  }) {
    return apiService.updateCurrentUser(
      name: name,
      email: email,
      nativeLanguage: nativeLanguage,
      learningLanguage: learningLanguage,
    );
  }
}
