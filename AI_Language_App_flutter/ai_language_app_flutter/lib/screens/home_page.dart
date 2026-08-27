import 'package:flutter/material.dart';

import '../controllers/home_stats_controller.dart';
import '../core/language/language_controller.dart';
import '../core/storage/storage_service.dart';
import '../core/theme/theme_controller.dart';
import '../l10n/app_localizations.dart';
import '../services/api/api_service.dart';
import '../services/learning_language_controller.dart';
import '../widgets/bottom_nav_bar.dart';
import '../widgets/home/continue_learning_card.dart';
import '../widgets/home/current_learning_language_card.dart';
import '../widgets/home/daily_tip.dart';
import '../widgets/home/learning_progress_card.dart';
import '../widgets/home/learning_stats.dart';
import '../widgets/home/quick_action_card.dart';
import '../widgets/home/welcome_header.dart';
import 'learning_path_page.dart';
import 'login_page.dart';
import 'profile_page.dart';
import 'words_page.dart';

class HomePage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const HomePage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ApiService apiService = ApiService();

  final LearningLanguageController learningLanguageController =
      LearningLanguageController.instance;

  late final HomeStatsController homeStatsController;

  int currentIndex = 0;

  String userName = 'Learner';

  late final List<Widget> pages;

  @override
  void initState() {
    super.initState();

    homeStatsController = HomeStatsController();

    homeStatsController.addListener(_onHomeStatsChanged);

    learningLanguageController.addListener(
      _onLearningLanguageChanged,
    );

    pages = [
      _HomeContent(
        userName: () => userName,
        onRefresh: loadHomeData,
        onPracticePressed: _openAiPractice,
        onLearningPathPressed: _openLearningPath,
        onWordsPressed: _openWords,
        themeController: widget.themeController,
        languageController: widget.languageController,
        statsController: homeStatsController,
      ),
      LearningPathPage(
        themeController: widget.themeController,
        languageController: widget.languageController,
      ),
      const WordsPage(),
      ProfilePage(
        themeController: widget.themeController,
        languageController: widget.languageController,
      ),
    ];

    loadHomeData();
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(
      _onLearningLanguageChanged,
    );

    homeStatsController.removeListener(
      _onHomeStatsChanged,
    );

    homeStatsController.dispose();

    super.dispose();
  }

  void _onHomeStatsChanged() {
    if (!mounted) {
      return;
    }

    setState(() {});
  }

  void _onLearningLanguageChanged() {
    if (!mounted) {
      return;
    }

    loadHomeData();
  }

  Future<void> loadHomeData() async {
    await Future.wait([
      loadCurrentUser(),
      homeStatsController.refresh(),
    ]);
  }

  Future<void> loadCurrentUser() async {
    try {
      final user = await apiService.getCurrentUser();

      if (!mounted) {
        return;
      }

      setState(() {
        userName = user['name']?.toString().trim().isNotEmpty == true
            ? user['name'].toString()
            : 'Learner';
      });
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        userName = 'Learner';
      });
    }
  }

  void onNavigationChanged(int index) {
    setState(() {
      currentIndex = index;
    });
  }

  void _openLearningPath() {
    setState(() {
      currentIndex = 1;
    });
  }

  void _openWords() {
    setState(() {
      currentIndex = 2;
    });
  }

  void _openAiPractice() {
    final l10n = AppLocalizations.of(context)!;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(l10n.aiConversationComingSoon),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> logout() async {
    await StorageService().deleteToken();

    learningLanguageController.clear();

    if (!mounted) {
      return;
    }

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: currentIndex,
        children: pages,
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: currentIndex,
        onItemSelected: onNavigationChanged,
      ),
    );
  }
}

class _HomeContent extends StatelessWidget {
  final String Function() userName;
  final Future<void> Function() onRefresh;
  final VoidCallback onPracticePressed;
  final VoidCallback onLearningPathPressed;
  final VoidCallback onWordsPressed;
  final ThemeController themeController;
  final LanguageController languageController;
  final HomeStatsController statsController;

  const _HomeContent({
    required this.userName,
    required this.onRefresh,
    required this.onPracticePressed,
    required this.onLearningPathPressed,
    required this.onWordsPressed,
    required this.themeController,
    required this.languageController,
    required this.statsController,
  });

  String _learningLanguageName(
    BuildContext context,
    String? code,
  ) {
    final l10n = AppLocalizations.of(context)!;

    switch (code) {
      case 'ar':
        return l10n.arabic;
      case 'en':
        return l10n.english;
      case 'fr':
        return l10n.french;
      case 'es':
        return l10n.spanish;
      case 'zh':
        return l10n.chinese;
      case 'ja':
        return l10n.japanese;
      case 'ko':
        return l10n.korean;
      case 'de':
        return 'German';
      case 'tr':
        return 'Turkish';
      default:
        return code ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    final learningLanguageCode =
        LearningLanguageController.instance.currentLanguage;

    final learningLanguage = _learningLanguageName(
      context,
      learningLanguageCode,
    );

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(
              parent: BouncingScrollPhysics(),
            ),
            padding: const EdgeInsets.fromLTRB(
              20,
              18,
              20,
              32,
            ),
            children: [
              WelcomeHeader(
                userName: userName(),
                themeController: themeController,
                languageController: languageController,
              ),

              const SizedBox(height: 22),

              if (learningLanguageCode != null &&
                  learningLanguageCode.isNotEmpty) ...[
                CurrentLearningLanguageCard(
                  language: learningLanguage,
                  onTap: onLearningPathPressed,
                ),
                const SizedBox(height: 18),
              ],

              LearningProgressCard(
                progress: statsController.learningProgress,
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
                streakDays: statsController.streakDays,
                learnedWords: statsController.learnedWords,
                conversations: statsController.conversations,
              ),

              const SizedBox(height: 22),

              ContinueLearningCard(
                onTap: onLearningPathPressed,
              ),

              const SizedBox(height: 20),

              const DailyTip(),
            ],
          ),
        ),
      ),
    );
  }
}