import 'package:flutter/material.dart';

import '../controllers/home_stats_controller.dart';
import '../core/language/language_controller.dart';
import '../core/theme/theme_controller.dart';
import '../services/api/api_service.dart';
import '../services/learning_language_controller.dart';
import '../widgets/bottom_nav_bar.dart';
import '../widgets/home/home_view.dart';
import 'learning_path_page.dart';
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
  late final HomeViewController _viewController;
  late final List<Widget> pages;

  int currentIndex = 0;
  String userName = 'Learner';

  @override
  void initState() {
    super.initState();

    homeStatsController = HomeStatsController();
    _viewController = HomeViewController(
      apiService: apiService,
      languageController: widget.languageController,
      learningLanguageController: learningLanguageController,
      statsController: homeStatsController,
    );

    _viewController.addListener(_onViewChanged);
    learningLanguageController.addListener(_onLearningLanguageChanged);

    pages = [
      HomeView(
        controller: _viewController,
        themeController: widget.themeController,
        languageController: widget.languageController,
        onLearningPathPressed: _openLearningPath,
        onWordsPressed: _openWords,
        onPracticePressed: _viewController.showAiPracticeMessage,
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

    _viewController.load();
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);
    _viewController.removeListener(_onViewChanged);
    _viewController.dispose();
    super.dispose();
  }

  void _onViewChanged() {
    if (!mounted) return;
    setState(() {
      userName = _viewController.userName;
    });
  }

  void _onLearningLanguageChanged() {
    if (!mounted) return;
    _viewController.refresh();
  }

  void _openLearningPath() {
    setState(() => currentIndex = 1);
  }

  void _openWords() {
    setState(() => currentIndex = 2);
  }

  void onNavigationChanged(int index) {
    setState(() => currentIndex = index);
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
