import 'package:flutter/material.dart';

import '../core/errors/api_exception.dart';
import '../core/language/language_controller.dart';
import '../core/storage/storage_service.dart';
import '../core/theme/theme_controller.dart';
import '../services/api/api_service.dart';
import 'home_page.dart';
import 'login_page.dart';
import 'onboarding_page.dart';

class SplashPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const SplashPage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  final StorageService storageService = StorageService();
  final ApiService apiService = ApiService();

  @override
  void initState() {
    super.initState();
    checkLogin();
  }

  Future<void> checkLogin() async {
    final token = await storageService.getToken();

    if (!mounted) return;

    if (token == null || token.isEmpty) {
      _goToLogin();
      return;
    }

    try {
      await apiService.getCurrentLearningProfile();

      if (!mounted) return;
      _goToHome();
    } on ApiException catch (e) {
      if (!mounted) return;

      if (e.isUnauthorized) {
        await storageService.deleteToken();
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Your session has expired. Please login again.'),
            duration: Duration(seconds: 3),
          ),
        );
        _goToLogin();
      } else if (e.isNotFound) {
        _goToOnboarding();
      } else {
        _showStartupError(e);
      }
    } catch (e) {
      if (!mounted) return;
      _showStartupError(e);
    }
  }

  void _goToLogin() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => LoginPage(
          themeController: widget.themeController,
          languageController: widget.languageController,
        ),
      ),
    );
  }

  void _goToHome() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => HomePage(
          themeController: widget.themeController,
          languageController: widget.languageController,
        ),
      ),
    );
  }

  void _goToOnboarding() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => OnboardingPage(
          themeController: widget.themeController,
          languageController: widget.languageController,
        ),
      ),
    );
  }

  void _showStartupError(Object error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(error.toString()),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 82,
              height: 82,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    theme.colorScheme.primary,
                    theme.colorScheme.secondary,
                  ],
                ),
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: theme.colorScheme.primary.withValues(alpha: 0.22),
                    blurRadius: 28,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: const Icon(
                Icons.auto_awesome_rounded,
                color: Colors.white,
                size: 38,
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: theme.colorScheme.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
