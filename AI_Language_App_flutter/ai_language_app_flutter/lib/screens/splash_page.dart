import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../core/language/language_controller.dart';
import '../core/storage/storage_service.dart';
import '../core/theme/theme_controller.dart';
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

    // ---------------------------------------------------------
    // No token -> Login
    // ---------------------------------------------------------

    if (token == null || token.isEmpty) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => LoginPage(
            themeController: widget.themeController,
            languageController: widget.languageController,
          ),
        ),
      );

      return;
    }

    // ---------------------------------------------------------
    // Token exists -> check onboarding status
    // ---------------------------------------------------------

    try {
      await apiService.getCurrentLearningProfile();

      if (!mounted) return;

      // Learning profile exists -> onboarding completed
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => HomePage(
            themeController: widget.themeController,
            languageController: widget.languageController,
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;

      // No learning profile yet -> new user
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
