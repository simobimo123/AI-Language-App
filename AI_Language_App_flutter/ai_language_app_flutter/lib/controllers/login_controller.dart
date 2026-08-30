import 'package:flutter/material.dart';

import '../core/storage/storage_service.dart';
import '../repositories/auth_repository.dart';
import '../services/google_auth_service.dart';

class LoginController extends ChangeNotifier {
  final AuthRepository authRepository;
  final StorageService storageService;
  final GoogleAuthService googleAuthService;

  LoginController({
    AuthRepository? authRepository,
    StorageService? storageService,
    GoogleAuthService? googleAuthService,
  })  : authRepository = authRepository ?? AuthRepository(),
        storageService = storageService ?? StorageService(),
        googleAuthService = googleAuthService ?? GoogleAuthService();

  bool isLoading = false;
  bool isGoogleLoading = false;
  bool isPasswordVisible = false;
  String? errorMessage;

  bool get isAnyLoading => isLoading || isGoogleLoading;

  void togglePasswordVisibility() {
    isPasswordVisible = !isPasswordVisible;
    notifyListeners();
  }

  Future<bool> login({
    required String email,
    required String password,
  }) async {
    if (isAnyLoading) return false;

    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final result = await authRepository.login(
        email: email.trim(),
        password: password,
      );

      final token = result['access_token']?.toString();
      if (token == null || token.isEmpty) {
        throw const FormatException('Access token is missing');
      }

      await storageService.saveToken(token);
      return true;
    } catch (error) {
      errorMessage = error.toString();
      return false;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> loginWithGoogle() async {
    if (isAnyLoading) return false;

    isGoogleLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final idToken = await googleAuthService.signInAndGetIdToken();

      if (idToken == null || idToken.isEmpty) {
        throw const FormatException('Google ID token is missing');
      }

      final result = await authRepository.loginWithGoogle(idToken: idToken);

      final token = result['access_token']?.toString();
      if (token == null || token.isEmpty) {
        throw const FormatException('Access token is missing');
      }

      await storageService.saveToken(token);
      return true;
    } catch (error) {
      errorMessage = error.toString();
      return false;
    } finally {
      isGoogleLoading = false;
      notifyListeners();
    }
  }

  void clearError() {
    if (errorMessage == null) return;
    errorMessage = null;
    notifyListeners();
  }
}
