import 'package:flutter/material.dart';

import '../services/api_service.dart';
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

  const HomePage({super.key, required this.themeController});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ApiService apiService = ApiService();

  int currentIndex = 0;

  String userName = 'Learner';

  late final List<Widget> pages;

  @override
  void initState() {
    super.initState();

    pages = [
      _HomeContent(
        userName: () => userName,
        onPracticePressed: _openAiPractice,
        themeController: widget.themeController,
      ),
      const WordsPage(),
      ProfilePage(themeController: widget.themeController),
    ];

    loadCurrentUser();
  }

  Future<void> loadCurrentUser() async {
    try {
      final user = await apiService.getCurrentUser();

      if (!mounted) return;

      setState(() {
        userName = user['name'] ?? 'Learner';
      });
    } catch (e) {
      if (!mounted) return;

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
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('ستتوفر محادثة الذكاء الاصطناعي قريبًا.')),
    );
  }

  Future<void> logout() async {
    await StorageService().deleteToken();

    if (!mounted) return;

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => LoginPage(themeController: widget.themeController),
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
  final VoidCallback onPracticePressed;
  final ThemeController themeController;

  const _HomeContent({
    required this.userName,
    required this.onPracticePressed,
    required this.themeController,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            await Future.delayed(const Duration(milliseconds: 500));
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 30),
            children: [
              WelcomeHeader(
                userName: userName(),
                themeController: themeController,
              ),

              const SizedBox(height: 24),

              const LearningProgressCard(progress: 0),

              const SizedBox(height: 28),

              Text(
                'ابدأ التعلّم',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              ),

              const SizedBox(height: 14),

              QuickActionCard(
                icon: Icons.auto_awesome_rounded,
                title: 'تدرّب مع الذكاء الاصطناعي',
                description:
                    'طوّر لغتك من خلال محادثات طبيعية.',
                onTap: onPracticePressed,
              ),

              const SizedBox(height: 14),

              QuickActionCard(
                icon: Icons.menu_book_rounded,
                title: 'كلماتي',
                description: 'راجع الكلمات التي حفظتها أثناء التعلّم.',
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const WordsPage()),
                  );
                },
              ),

              const SizedBox(height: 28),

              Text(
                'تعلّمك',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
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
    return Row(
      children: const [
        Expanded(
          child: _StatCard(
            icon: Icons.local_fire_department_rounded,
            value: '0',
            label: 'أيام متتالية',
          ),
        ),

        SizedBox(width: 12),

        Expanded(
          child: _StatCard(
            icon: Icons.menu_book_rounded,
            value: '0',
            label: 'كلمات متعلّمة',
          ),
        ),

        SizedBox(width: 12),

        Expanded(
          child: _StatCard(
            icon: Icons.chat_bubble_rounded,
            value: '0',
            label: 'محادثات',
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
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        children: [
          Icon(icon, color: theme.colorScheme.primary, size: 24),

          const SizedBox(height: 8),

          Text(
            value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 4),

          Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
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

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.lightbulb_rounded, color: Colors.white, size: 28),

          const SizedBox(width: 14),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'نصيحة يومية',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 6),

                Text(
                  'تدرّب قليلًا كل يوم؛ الاستمرارية هي مفتاح تطوير مهاراتك اللغوية.',
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
