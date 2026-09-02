import 'package:flutter/material.dart';
import '../l10n/app_localizations.dart';
import '../services/api/api_service.dart';
import '../core/language/language_controller.dart';
import '../core/theme/theme_controller.dart';
import 'home_page.dart';
import 'placement_test_page.dart';

class OnboardingPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const OnboardingPage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  final ApiService apiService = ApiService();

  int currentStep = 0;
  bool isLoading = true;
  bool isSaving = false;

  String? selectedAppLanguage;
  String? selectedNativeLanguage;
  String? selectedLearningLanguage;
  String? userName;
  String? userEmail;

  // All 18 languages supported by the backend.
  // fa (Persian) and hi (Hindi) are intentionally excluded.
  final List<Map<String, String>> appLanguages = const [
    {'code': 'ar', 'name': 'العربية'},
    {'code': 'de', 'name': 'Deutsch'},
    {'code': 'en', 'name': 'English'},
    {'code': 'es', 'name': 'Español'},
    {'code': 'fr', 'name': 'Français'},
    {'code': 'id', 'name': 'Bahasa Indonesia'},
    {'code': 'it', 'name': 'Italiano'},
    {'code': 'ja', 'name': '日本語'},
    {'code': 'ko', 'name': '한국어'},
    {'code': 'nl', 'name': 'Nederlands'},
    {'code': 'pl', 'name': 'Polski'},
    {'code': 'pt', 'name': 'Português'},
    {'code': 'ru', 'name': 'Русский'},
    {'code': 'th', 'name': 'ไทย'},
    {'code': 'tr', 'name': 'Türkçe'},
    {'code': 'uk', 'name': 'Українська'},
    {'code': 'vi', 'name': 'Tiếng Việt'},
    {'code': 'zh', 'name': '中文'},
  ];

  // All 18 languages supported by the backend.
  // fa (Persian) and hi (Hindi) are intentionally excluded.
  final List<Map<String, String>> languages = const [
    {'code': 'ar', 'name_ar': 'العربية', 'name_en': 'Arabic'},
    {'code': 'de', 'name_ar': 'الألمانية', 'name_en': 'German'},
    {'code': 'en', 'name_ar': 'الإنجليزية', 'name_en': 'English'},
    {'code': 'es', 'name_ar': 'الإسبانية', 'name_en': 'Spanish'},
    {'code': 'fr', 'name_ar': 'الفرنسية', 'name_en': 'French'},
    {'code': 'id', 'name_ar': 'الإندونيسية', 'name_en': 'Indonesian'},
    {'code': 'it', 'name_ar': 'الإيطالية', 'name_en': 'Italian'},
    {'code': 'ja', 'name_ar': 'اليابانية', 'name_en': 'Japanese'},
    {'code': 'ko', 'name_ar': 'الكورية', 'name_en': 'Korean'},
    {'code': 'nl', 'name_ar': 'الهولندية', 'name_en': 'Dutch'},
    {'code': 'pl', 'name_ar': 'البولندية', 'name_en': 'Polish'},
    {'code': 'pt', 'name_ar': 'البرتغالية', 'name_en': 'Portuguese'},
    {'code': 'ru', 'name_ar': 'الروسية', 'name_en': 'Russian'},
    {'code': 'th', 'name_ar': 'التايلاندية', 'name_en': 'Thai'},
    {'code': 'tr', 'name_ar': 'التركية', 'name_en': 'Turkish'},
    {'code': 'uk', 'name_ar': 'الأوكرانية', 'name_en': 'Ukrainian'},
    {'code': 'vi', 'name_ar': 'الفيتنامية', 'name_en': 'Vietnamese'},
    {'code': 'zh', 'name_ar': 'الصينية', 'name_en': 'Chinese'},
  ];

  @override
  void initState() {
    super.initState();
    loadCurrentUser();
  }

  Future<void> loadCurrentUser() async {
    try {
      final user = await apiService.getCurrentUser();

      if (!mounted) return;

      setState(() {
        userName = user['name']?.toString();
        userEmail = user['email']?.toString();
        selectedNativeLanguage = user['native_language']?.toString();
        selectedLearningLanguage = user['learning_language']?.toString();
        selectedAppLanguage =
            widget.languageController.locale.languageCode;
        isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        selectedAppLanguage =
            widget.languageController.locale.languageCode;
        isLoading = false;
      });
    }
  }

  bool get isArabic => widget.languageController.isArabic;

  String languageName(
    Map<String, String> language,
  ) {
    return isArabic
        ? language['name_ar'] ?? ''
        : language['name_en'] ?? '';
  }

  bool get canContinue {
    switch (currentStep) {
      case 0:
        return selectedAppLanguage != null;

      case 1:
        return selectedNativeLanguage != null;

      case 2:
        return selectedLearningLanguage != null &&
            selectedLearningLanguage != selectedNativeLanguage;

      default:
        return false;
    }
  }

  Future<void> selectApplicationLanguage(String code) async {
    if (isSaving) return;

    setState(() {
      selectedAppLanguage = code;
    });

    await widget.languageController.setLanguage(code);

    if (!mounted) return;

    setState(() {});
  }

  Future<void> continueStep() async {
    if (!canContinue || isSaving) return;

    if (currentStep < 2) {
      setState(() {
        currentStep++;
      });
      return;
    }

    await saveOnboardingData();
  }

  void previousStep() {
    if (isSaving) return;

    if (currentStep > 0) {
      setState(() {
        currentStep--;
      });
    }
  }

  Future<void> saveOnboardingData() async {
    final l10n = AppLocalizations.of(context)!;

    if (selectedNativeLanguage == null ||
        selectedLearningLanguage == null ||
        userName == null ||
        userEmail == null) {
      showError(l10n.userInformationReadError);
      return;
    }

    setState(() {
      isSaving = true;
    });

    try {
      await apiService.updateCurrentUser(
        name: userName!,
        email: userEmail!,
        nativeLanguage: selectedNativeLanguage!,
        learningLanguage: selectedLearningLanguage!,
      );

      if (!mounted) return;

      setState(() {
        isSaving = false;
      });

      await showTestPreparationDialog();
    } catch (_) {
      if (!mounted) return;

      setState(() {
        isSaving = false;
      });

      showError(l10n.onboardingSaveError);
    }
  }

  Future<void> showTestPreparationDialog() async {
    final l10n = AppLocalizations.of(context)!;

    if (selectedLearningLanguage == null) return;

    final shouldStart = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        final theme = Theme.of(dialogContext);

        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
          ),
          title: Text(l10n.placementTestTitle),
          content: Text(
            l10n.placementTestDescription,
            style: theme.textTheme.bodyMedium,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(l10n.later),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: Text(l10n.startTest),
            ),
          ],
        );
      },
    );

    if (shouldStart != true ||
        !mounted ||
        selectedLearningLanguage == null) {
      return;
    }

    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => PlacementTestPage(
          themeController: widget.themeController,
          languageController: widget.languageController,
          language: selectedLearningLanguage!,
        ),
      ),
    );

    if (!mounted || result == null || result.isEmpty) {
      return;
    }

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (_) => HomePage(
          themeController: widget.themeController,
          languageController: widget.languageController,
        ),
      ),
      (route) => false,
    );
  }

  void showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
      ),
    );
  }

  String get currentTitle {
    final l10n = AppLocalizations.of(context)!;

    switch (currentStep) {
      case 0:
        return l10n.chooseAppLanguage;

      case 1:
        return l10n.nativeLanguageQuestion;

      case 2:
        return l10n.learningLanguageQuestion;

      default:
        return '';
    }
  }

  String get currentDescription {
    final l10n = AppLocalizations.of(context)!;

    switch (currentStep) {
      case 0:
        return l10n.chooseAppLanguageDescription;

      case 1:
        return l10n.nativeLanguageDescription;

      case 2:
        return l10n.learningLanguageDescription;

      default:
        return '';
    }
  }

  Widget buildAppLanguageCard(
    Map<String, String> language,
    ThemeData theme,
  ) {
    final code = language['code']!;
    final name = language['name']!;
    final selected = selectedAppLanguage == code;

    return GestureDetector(
      onTap: isSaving
          ? null
          : () => selectApplicationLanguage(code),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: selected
              ? theme.colorScheme.primary.withValues(alpha: 0.10)
              : theme.cardColor,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: selected
                ? theme.colorScheme.primary
                : theme.dividerColor.withValues(alpha: 0.35),
            width: selected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: selected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(14),
              ),
              alignment: Alignment.center,
              child: Text(
                code.toUpperCase(),
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: selected
                      ? theme.colorScheme.onPrimary
                      : theme.colorScheme.onSurface,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                name,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight:
                      selected ? FontWeight.bold : FontWeight.w500,
                ),
              ),
            ),
            if (selected)
              Icon(
                Icons.check_circle_rounded,
                color: theme.colorScheme.primary,
              ),
          ],
        ),
      ),
    );
  }

  Widget buildUserLanguageCard(
    Map<String, String> language,
    ThemeData theme,
    String? selectedCode,
  ) {
    final l10n = AppLocalizations.of(context)!;

    final code = language['code']!;
    final selected = selectedCode == code;

    return GestureDetector(
      onTap: isSaving
          ? null
          : () {
              setState(() {
                if (currentStep == 1) {
                  selectedNativeLanguage = code;

                  if (selectedLearningLanguage == code) {
                    selectedLearningLanguage = null;
                  }
                } else {
                  if (selectedNativeLanguage == code) {
                    showError(
                      l10n.nativeLanguageCannotBeLearningLanguage,
                    );
                    return;
                  }

                  selectedLearningLanguage = code;
                }
              });
            },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
        decoration: BoxDecoration(
          color: selected
              ? theme.colorScheme.primary.withValues(alpha: 0.10)
              : theme.cardColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected
                ? theme.colorScheme.primary
                : theme.dividerColor.withValues(alpha: 0.35),
            width: selected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: selected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.surfaceContainerHighest,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: Text(
                code.toUpperCase(),
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                  color: selected
                      ? theme.colorScheme.onPrimary
                      : theme.colorScheme.onSurface,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                languageName(language),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight:
                      selected ? FontWeight.bold : FontWeight.w500,
                ),
              ),
            ),
            if (selected)
              Icon(
                Icons.check_circle_rounded,
                color: theme.colorScheme.primary,
              ),
          ],
        ),
      ),
    );
  }

  Widget buildStepContent(ThemeData theme) {
    if (currentStep == 0) {
      return Column(
        children: appLanguages
            .map(
              (language) =>
                  buildAppLanguageCard(language, theme),
            )
            .toList(),
      );
    }

    return Column(
      children: languages
          .map(
            (language) => buildUserLanguageCard(
              language,
              theme,
              currentStep == 1
                  ? selectedNativeLanguage
                  : selectedLearningLanguage,
            ),
          )
          .toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    if (isLoading) {
      return Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        body: Center(
          child: CircularProgressIndicator(
            color: theme.colorScheme.primary,
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        leading: currentStep > 0
            ? IconButton(
                onPressed: isSaving ? null : previousStep,
                tooltip: l10n.back,
                icon: const Icon(Icons.arrow_back_rounded),
              )
            : null,
        title: Text(l10n.setupYourAccount),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
              child: Column(
                children: [
                  Row(
                    children: List.generate(
                      3,
                      (index) {
                        final active = index <= currentStep;

                        return Expanded(
                          child: Container(
                            height: 5,
                            margin: EdgeInsets.only(
                              right: index == 2 ? 0 : 6,
                            ),
                            decoration: BoxDecoration(
                              color: active
                                  ? theme.colorScheme.primary
                                  : theme.dividerColor
                                      .withValues(alpha: 0.30),
                              borderRadius:
                                  BorderRadius.circular(20),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 24),
                  Align(
                    alignment:
                        AlignmentDirectional.centerStart,
                    child: Text(
                      currentTitle,
                      style: const TextStyle(
                        fontSize: 25,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Align(
                    alignment:
                        AlignmentDirectional.centerStart,
                    child: Text(
                      currentDescription,
                      style: TextStyle(
                        fontSize: 14,
                        height: 1.5,
                        color: theme.textTheme.bodyMedium?.color
                            ?.withValues(alpha: 0.70),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(
                  20,
                  0,
                  20,
                  20,
                ),
                child: buildStepContent(theme),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                20,
                10,
                20,
                20,
              ),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed:
                      (!canContinue || isSaving)
                          ? null
                          : continueStep,
                  style: ElevatedButton.styleFrom(
                    shape: RoundedRectangleBorder(
                      borderRadius:
                          BorderRadius.circular(16),
                    ),
                  ),
                  child: isSaving
                      ? SizedBox(
                          width: 24,
                          height: 24,
                          child:
                              CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color:
                                theme.colorScheme.onPrimary,
                          ),
                        )
                      : Text(
                          currentStep == 2
                              ? l10n.saveAndContinue
                              : l10n.continueButton,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
