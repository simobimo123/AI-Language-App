import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/api/api_service.dart';
import '../core/language/language_controller.dart';
import '../core/storage/storage_service.dart';
import '../core/theme/theme_controller.dart';
import '../services/learning_language_controller.dart';
import '../screens/login_page.dart';
import '../screens/placement_test_page.dart';

class ProfileController extends ChangeNotifier {
  ProfileController({
    required this.themeController,
    required this.languageController,
  }) : learningLanguageController = LearningLanguageController.instance {
    learningLanguageController.addListener(_onLearningLanguageChanged);
  }

  final ThemeController themeController;
  final LanguageController languageController;
  final ApiService apiService = ApiService();
  final StorageService storageService = StorageService();
  final LearningLanguageController learningLanguageController;

  static const List<String> learningLanguageCodes = ['ar', 'en', 'fr', 'es', 'de', 'tr'];

  String name = 'Loading...';
  String email = '';
  String userId = '';
  String nativeLanguage = '';
  String? nativeLanguageCode;
  String? currentLearningLanguageCode;
  String? currentLearningLevel;
  List<dynamic> learningProfiles = [];

  bool isLoading = true;
  bool isChangingLanguage = false;
  bool isAddingLanguage = false;

  static const Map<String, String> appLanguages = {
    'ar': 'العربية',
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
    'de': 'Deutsch',
    'id': 'Bahasa Indonesia',
    'it': 'Italiano',
    'nl': 'Nederlands',
    'pl': 'Polski',
    'pt': 'Português',
    'ru': 'Русский',
    'th': 'ไทย',
    'tr': 'Türkçe',
    'uk': 'Українська',
    'vi': 'Tiếng Việt',
  };

  void _onLearningLanguageChanged() {
    final language = learningLanguageController.currentLanguage;
    if (language == null || language == currentLearningLanguageCode) return;
    currentLearningLanguageCode = language;
    currentLearningLevel = getProfile(language)?['level']?.toString();
    notifyListeners();
  }

  Future<void> loadProfile(BuildContext context) async {
    try {
      final user = await apiService.getCurrentUser();
      final profiles = await apiService.getLearningProfiles();
      if (context.mounted) {
        final nativeCode = user['native_language']?.toString();
        final currentLanguage = user['learning_language']?.toString();
        final profile = _findProfile(profiles, currentLanguage);
        final l10n = AppLocalizations.of(context)!;

        name = user['name'] ?? 'Learner';
        email = user['email'] ?? '';
        userId = user['id']?.toString() ?? '';
        nativeLanguageCode = nativeCode;
        nativeLanguage = languageName(nativeCode, l10n);
        currentLearningLanguageCode = currentLanguage;
        currentLearningLevel = profile?['level']?.toString();
        learningProfiles = profiles;
        isLoading = false;
        notifyListeners();

        if (currentLanguage != null) {
          learningLanguageController.setLanguage(currentLanguage);
        }
      }
    } catch (_) {
      isLoading = false;
      name = 'Unable to load profile';
      notifyListeners();
    }
  }

  dynamic _findProfile(List<dynamic> profiles, String? language) {
    for (final profile in profiles) {
      if (profile['language'] == language) return profile;
    }
    return null;
  }

  dynamic getProfile(String language) => _findProfile(learningProfiles, language);

  String languageName(String? code, AppLocalizations l10n) {
    switch (code) {
      case 'ar': return l10n.arabic;
      case 'en': return l10n.english;
      case 'fr': return l10n.french;
      case 'es': return l10n.spanish;
      case 'zh': return l10n.chinese;
      case 'ja': return l10n.japanese;
      case 'ko': return l10n.korean;
      default: return appLanguages[code] ?? code ?? '';
    }
  }

  String levelName(String? level, AppLocalizations l10n) {
    switch (level) {
      case 'PRE_A1': return 'Pre-A1';
      case 'A1': return l10n.levelA1;
      case 'A2': return l10n.levelA2;
      case 'B1': return l10n.levelB1;
      case 'B2': return l10n.levelB2;
      case 'C1': return l10n.levelC1;
      case 'C2': return l10n.levelC2;
      default: return level ?? '';
    }
  }

  String appLanguageName(String code, AppLocalizations l10n) => languageName(code, l10n);

  Future<void> changeAppLanguage(String code) async {
    if (languageController.locale.languageCode == code) return;
    await languageController.setLanguage(code);
    notifyListeners();
  }

  Future<void> changeLearningLanguage(BuildContext context, String language) async {
    if (currentLearningLanguageCode == language) return;
    final l10n = AppLocalizations.of(context)!;
    final messenger = ScaffoldMessenger.maybeOf(context);
    isChangingLanguage = true;
    notifyListeners();
    try {
      final result = await apiService.switchLearningLanguage(language: language);
      currentLearningLanguageCode = language;
      currentLearningLevel = result['level']?.toString();
      isChangingLanguage = false;
      learningLanguageController.setLanguage(language);
      notifyListeners();
      messenger?.showSnackBar(SnackBar(
        content: Text(l10n.learningLanguageChanged(languageName(language, l10n))),
        behavior: SnackBarBehavior.floating,
      ));
    } catch (e) {
      isChangingLanguage = false;
      notifyListeners();
      messenger?.showSnackBar(SnackBar(
        content: Text(e.toString()),
        behavior: SnackBarBehavior.floating,
      ));
    }
  }

  Future<void> startPlacementForLanguage(BuildContext context, String language) async {
    if (isChangingLanguage || isAddingLanguage) return;
    isAddingLanguage = true;
    notifyListeners();

    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => PlacementTestPage(
          themeController: themeController,
          languageController: languageController,
          language: language,
        ),
      ),
    );

    if (!context.mounted) return;
    if (result == null || result.isEmpty) {
      isAddingLanguage = false;
      notifyListeners();
      return;
    }

    final l10n = AppLocalizations.of(context)!;
    final messenger = ScaffoldMessenger.maybeOf(context);

    try {
      final profiles = await apiService.getLearningProfiles();
      learningLanguageController.setLanguage(language);
      final profile = _findProfile(profiles, language);
      learningProfiles = profiles;
      currentLearningLanguageCode = language;
      currentLearningLevel = profile?['level']?.toString();
      isAddingLanguage = false;
      notifyListeners();
      messenger?.showSnackBar(SnackBar(
        content: Text(l10n.learningLanguageChanged(languageName(language, l10n))),
        behavior: SnackBarBehavior.floating,
      ));
    } catch (e) {
      isAddingLanguage = false;
      notifyListeners();
      messenger?.showSnackBar(SnackBar(
        content: Text(e.toString()),
        behavior: SnackBarBehavior.floating,
      ));
    }
  }

  Future<void> logout(BuildContext context) async {
    await storageService.deleteToken();

    if (!context.mounted) return;

    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(
        builder: (_) => LoginPage(
          themeController: themeController,
          languageController: languageController,
        ),
      ),
      (route) => false,
    );
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);
    super.dispose();
  }
}
