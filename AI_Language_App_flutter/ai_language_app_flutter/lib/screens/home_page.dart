import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';
import '../services/language_controller.dart';
import '../services/learning_language_controller.dart';
import '../services/storage_service.dart';
import '../services/theme_controller.dart';
import '../widgets/bottom_nav_bar.dart';
import '../widgets/home/learning_progress_card.dart';
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

  int currentIndex = 0;

  String userName = 'Learner';

  late final List<Widget> pages;

  @override
  void initState() {
    super.initState();

    learningLanguageController.addListener(_onLearningLanguageChanged);

    pages = [
      _HomeContent(
        userName: () => userName,
        onRefresh: loadCurrentUser,
        onPracticePressed: _openAiPractice,
        onLearningPathPressed: _openLearningPath,
        onWordsPressed: _openWords,
        themeController: widget.themeController,
        languageController: widget.languageController,
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

    loadCurrentUser();
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);
    super.dispose();
  }

  void _onLearningLanguageChanged() {
    if (!mounted) {
      return;
    }

    loadCurrentUser();
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
    } catch (e) {
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
      body: IndexedStack(index: currentIndex, children: pages),
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

  const _HomeContent({
    required this.userName,
    required this.onRefresh,
    required this.onPracticePressed,
    required this.onLearningPathPressed,
    required this.onWordsPressed,
    required this.themeController,
    required this.languageController,
  });

  String _learningLanguageName(BuildContext context, String? code) {
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
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
            children: [
              WelcomeHeader(
                userName: userName(),
                themeController: themeController,
                languageController: languageController,
              ),

              const SizedBox(height: 22),

              if (learningLanguageCode != null &&
                  learningLanguageCode.isNotEmpty) ...[
                _CurrentLearningLanguageCard(
                  language: learningLanguage,
                  onTap: onLearningPathPressed,
                ),

                const SizedBox(height: 18),
              ],

              const LearningProgressCard(progress: 0),

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

              const _LearningStats(),

              const SizedBox(height: 22),

              _ContinueLearningCard(onTap: onLearningPathPressed),

              const SizedBox(height: 20),

              const _DailyTip(),
            ],
          ),
        ),
      ),
    );
  }
}

class _CurrentLearningLanguageCard extends StatelessWidget {
  final String language;
  final VoidCallback onTap;

  const _CurrentLearningLanguageCard({
    required this.language,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Ink(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                theme.colorScheme.primaryContainer,
                theme.colorScheme.secondaryContainer,
              ],
            ),
            borderRadius: BorderRadius.circular(22),
          ),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface.withOpacity(0.85),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  Icons.school_rounded,
                  color: theme.colorScheme.primary,
                  size: 27,
                ),
              ),

              const SizedBox(width: 14),

              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.learningLanguage,
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSurfaceVariant,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      language,
                      style: TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                  ],
                ),
              ),

              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface.withOpacity(0.85),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.arrow_forward_rounded,
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LearningStats extends StatelessWidget {
  const _LearningStats();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Row(
      children: [
        Expanded(
          child: _StatCard(
            icon: Icons.local_fire_department_rounded,
            value: '0',
            label: l10n.streakDays,
          ),
        ),

        const SizedBox(width: 10),

        Expanded(
          child: _StatCard(
            icon: Icons.menu_book_rounded,
            value: '0',
            label: l10n.learnedWords,
          ),
        ),

        const SizedBox(width: 10),

        Expanded(
          child: _StatCard(
            icon: Icons.chat_bubble_rounded,
            value: '0',
            label: l10n.conversations,
          ),
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;

  const _StatCard({
    required this.icon,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      constraints: const BoxConstraints(minHeight: 122),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: theme.colorScheme.outlineVariant),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.shadow.withOpacity(0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: theme.colorScheme.primary, size: 22),
          ),

          const SizedBox(height: 9),

          Text(
            value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 3),

          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 11,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _ContinueLearningCard extends StatelessWidget {
  final VoidCallback onTap;

  const _ContinueLearningCard({required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Ink(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: theme.colorScheme.outlineVariant),
          ),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  Icons.play_arrow_rounded,
                  color: theme.colorScheme.primary,
                  size: 30,
                ),
              ),

              const SizedBox(width: 14),

              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.startLearning,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      l10n.yourLearning,
                      style: TextStyle(
                        fontSize: 13,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 8),

              Icon(
                Icons.chevron_right_rounded,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DailyTip extends StatelessWidget {
  const _DailyTip();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.14),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(
              Icons.lightbulb_rounded,
              color: Colors.white,
              size: 24,
            ),
          ),

          const SizedBox(width: 14),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.dailyTip,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 7),

                Text(
                  l10n.dailyTipDescription,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    height: 1.45,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
