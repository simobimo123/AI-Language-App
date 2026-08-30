import 'package:flutter/material.dart';

import '../../controllers/home_stats_controller.dart';
import '../../core/language/language_controller.dart';
import '../../core/theme/theme_controller.dart';
import '../../l10n/app_localizations.dart';
import '../../services/api/api_service.dart';
import '../../services/learning_language_controller.dart';
import 'continue_learning_card.dart';
import 'current_learning_language_card.dart';
import 'daily_tip.dart';
import 'learning_progress_card.dart';
import 'learning_stats.dart';
import 'quick_action_card.dart';
import 'welcome_header.dart';

class HomeViewController extends ChangeNotifier {
  final ApiService apiService;
  final LanguageController languageController;
  final LearningLanguageController learningLanguageController;
  final HomeStatsController statsController;

  String _userName = 'Learner';
  bool _isLoading = false;

  HomeViewController({
    required this.apiService,
    required this.languageController,
    required this.learningLanguageController,
    required this.statsController,
  }) {
    statsController.addListener(_onStatsChanged);
  }

  String get userName => _userName;
  bool get isLoading => _isLoading;

  Future<void> load() async {
    if (_isLoading) return;
    _isLoading = true;
    notifyListeners();

    try {
      await Future.wait([
        _loadCurrentUser(),
        statsController.refresh(),
      ]);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() => load();

  Future<void> _loadCurrentUser() async {
    try {
      final user = await apiService.getCurrentUser();
      final value = user['name']?.toString().trim();
      _userName = value?.isNotEmpty == true ? value! : 'Learner';
    } catch (_) {
      _userName = 'Learner';
    }
  }

  void _onStatsChanged() => notifyListeners();

  void showAiPracticeMessage() {
    // The HomePage supplies the UI callback where a BuildContext is available.
  }

  void showAiPracticeMessageWithContext(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(l10n.aiConversationComingSoon),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  void dispose() {
    statsController.removeListener(_onStatsChanged);
    super.dispose();
  }
}

class HomeView extends StatelessWidget {
  final HomeViewController controller;
  final ThemeController themeController;
  final LanguageController languageController;
  final VoidCallback onLearningPathPressed;
  final VoidCallback onWordsPressed;
  final VoidCallback onPracticePressed;

  const HomeView({
    super.key,
    required this.controller,
    required this.themeController,
    required this.languageController,
    required this.onLearningPathPressed,
    required this.onWordsPressed,
    required this.onPracticePressed,
  });

  String _learningLanguageName(BuildContext context, String? code) {
    final l10n = AppLocalizations.of(context)!;
    switch (code) {
      case 'ar': return l10n.arabic;
      case 'en': return l10n.english;
      case 'fr': return l10n.french;
      case 'es': return l10n.spanish;
      case 'zh': return l10n.chinese;
      case 'ja': return l10n.japanese;
      case 'ko': return l10n.korean;
      case 'de': return 'German';
      case 'tr': return 'Turkish';
      default: return code ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final theme = Theme.of(context);
        final l10n = AppLocalizations.of(context)!;
        final code = controller.learningLanguageController.currentLanguage;
        final language = _learningLanguageName(context, code);

        return Scaffold(
          backgroundColor: theme.scaffoldBackgroundColor,
          body: SafeArea(
            child: RefreshIndicator(
              onRefresh: controller.refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(
                  parent: BouncingScrollPhysics(),
                ),
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
                children: [
                  WelcomeHeader(
                    userName: controller.userName,
                    themeController: themeController,
                    languageController: languageController,
                  ),
                  const SizedBox(height: 22),
                  if (code != null && code.isNotEmpty) ...[
                    CurrentLearningLanguageCard(
                      language: language,
                      onTap: onLearningPathPressed,
                    ),
                    const SizedBox(height: 18),
                  ],
                  LearningProgressCard(
                    progress: controller.statsController.learningProgress,
                  ),
                  const SizedBox(height: 28),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          l10n.startLearning,
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      TextButton(
                        onPressed: onLearningPathPressed,
                        child: Text(
                          l10n.yourLearning,
                          style: TextStyle(
                            color: theme.colorScheme.primary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  QuickActionCard(
                    icon: Icons.auto_awesome_rounded,
                    title: l10n.practiceWithAI,
                    description: l10n.practiceWithAIDescription,
                    onTap: onPracticePressed,
                  ),
                  const SizedBox(height: 12),
                  QuickActionCard(
                    icon: Icons.menu_book_rounded,
                    title: l10n.myWords,
                    description: l10n.myWordsDescription,
                    onTap: onWordsPressed,
                  ),
                  const SizedBox(height: 28),
                  Text(
                    l10n.yourLearning,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 14),
                  LearningStats(
                    streakDays: controller.statsController.streakDays,
                    learnedWords: controller.statsController.learnedWords,
                    conversations: controller.statsController.conversations,
                  ),
                  const SizedBox(height: 22),
                  ContinueLearningCard(onTap: onLearningPathPressed),
                  const SizedBox(height: 20),
                  const DailyTip(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
