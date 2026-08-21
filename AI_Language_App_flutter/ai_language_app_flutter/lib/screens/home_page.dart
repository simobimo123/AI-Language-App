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

    learningLanguageController.addListener(
      _onLearningLanguageChanged,
    );

    pages = [
      _HomeContent(
        userName: () => userName,
        onPracticePressed: _openAiPractice,
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
    learningLanguageController.removeListener(
      _onLearningLanguageChanged,
    );

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
        userName = user['name'] ?? 'Learner';
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

  void _openAiPractice() {
    final l10n = AppLocalizations.of(context)!;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          l10n.aiConversationComingSoon,
        ),
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
  final VoidCallback onPracticePressed;
  final ThemeController themeController;
  final LanguageController languageController;

  const _HomeContent({
    required this.userName,
    required this.onPracticePressed,
    required this.themeController,
    required this.languageController,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {},
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(
              20,
              20,
              20,
              30,
            ),
            children: [
              WelcomeHeader(
                userName: userName(),
                themeController: themeController,
                languageController: languageController,
              ),

              const SizedBox(height: 24),

              const LearningProgressCard(
                progress: 0,
              ),

              const SizedBox(height: 28),

              Text(
                l10n.startLearning,
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),

              const SizedBox(height: 14),

              QuickActionCard(
                icon: Icons.auto_awesome_rounded,
                title: l10n.practiceWithAI,
                description: l10n.practiceWithAIDescription,
                onTap: onPracticePressed,
              ),

              const SizedBox(height: 14),

              QuickActionCard(
                icon: Icons.menu_book_rounded,
                title: l10n.myWords,
                description: l10n.myWordsDescription,
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const WordsPage(),
                    ),
                  );
                },
              ),

              const SizedBox(height: 28),

              Text(
                l10n.yourLearning,
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),

              const SizedBox(height: 14),

              const _LearningStats(),

              const SizedBox(height: 20),

              const _DailyTip(),
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
        const SizedBox(width: 12),
        Expanded(
          child: _StatCard(
            icon: Icons.menu_book_rounded,
            value: '0',
            label: l10n.learnedWords,
          ),
        ),
        const SizedBox(width: 12),
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
      padding: const EdgeInsets.symmetric(
        horizontal: 10,
        vertical: 16,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: theme.colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        children: [
          Icon(
            icon,
            color: theme.colorScheme.primary,
            size: 24,
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            textAlign: TextAlign.center,
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
          const Icon(
            Icons.lightbulb_rounded,
            color: Colors.white,
            size: 28,
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
                const SizedBox(height: 6),
                Text(
                  l10n.dailyTipDescription,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    height: 1.4,
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