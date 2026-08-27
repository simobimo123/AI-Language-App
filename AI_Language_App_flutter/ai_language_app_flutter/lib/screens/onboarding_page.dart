import 'package:flutter/material.dart';

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

  // =========================================================
  // Application languages
  // =========================================================

  final List<Map<String, String>> appLanguages = const [
    {'code': 'ar', 'name': 'العربية'},
    {'code': 'en', 'name': 'English'},
    {'code': 'fr', 'name': 'Français'},
    {'code': 'es', 'name': 'Español'},
    {'code': 'zh', 'name': '中文'},
    {'code': 'ja', 'name': '日本語'},
    {'code': 'ko', 'name': '한국어'},
  ];

  // =========================================================
  // User languages
  // =========================================================

  final List<Map<String, String>> languages = const [
    {'code': 'ar', 'name_ar': 'العربية', 'name_en': 'Arabic'},
    {'code': 'en', 'name_ar': 'الإنجليزية', 'name_en': 'English'},
    {'code': 'fr', 'name_ar': 'الفرنسية', 'name_en': 'French'},
    {'code': 'es', 'name_ar': 'الإسبانية', 'name_en': 'Spanish'},
    {'code': 'de', 'name_ar': 'الألمانية', 'name_en': 'German'},
    {'code': 'it', 'name_ar': 'الإيطالية', 'name_en': 'Italian'},
    {'code': 'tr', 'name_ar': 'التركية', 'name_en': 'Turkish'},
    {'code': 'pt', 'name_ar': 'البرتغالية', 'name_en': 'Portuguese'},
    {'code': 'ja', 'name_ar': 'اليابانية', 'name_en': 'Japanese'},
    {'code': 'ko', 'name_ar': 'الكورية', 'name_en': 'Korean'},
    {'code': 'zh', 'name_ar': 'الصينية', 'name_en': 'Chinese'},
  ];

  // =========================================================
  // Initialization
  // =========================================================

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

        selectedAppLanguage = widget.languageController.locale.languageCode;

        isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        selectedAppLanguage = widget.languageController.locale.languageCode;

        isLoading = false;
      });
    }
  }

  // =========================================================
  // Localization helpers
  // =========================================================

  bool get isArabic => widget.languageController.isArabic;

  String text({required String ar, required String en}) {
    return isArabic ? ar : en;
  }

  String languageName(Map<String, String> language) {
    return isArabic ? language['name_ar'] ?? '' : language['name_en'] ?? '';
  }

  // =========================================================
  // Validation
  // =========================================================

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

  // =========================================================
  // Application language
  // =========================================================

  Future<void> selectApplicationLanguage(String code) async {
    if (isSaving) return;

    setState(() {
      selectedAppLanguage = code;
    });

    await widget.languageController.setLanguage(code);

    if (!mounted) return;

    setState(() {});
  }

  // =========================================================
  // Continue
  // =========================================================

  Future<void> continueStep() async {
    if (!canContinue || isSaving) {
      return;
    }

    if (currentStep < 2) {
      setState(() {
        currentStep++;
      });

      return;
    }

    await saveOnboardingData();
  }

  // =========================================================
  // Back
  // =========================================================

  void previousStep() {
    if (isSaving) return;

    if (currentStep > 0) {
      setState(() {
        currentStep--;
      });
    }
  }

  // =========================================================
  // Save onboarding data
  // =========================================================

  Future<void> saveOnboardingData() async {
    if (selectedNativeLanguage == null ||
        selectedLearningLanguage == null ||
        userName == null ||
        userEmail == null) {
      showError(
        text(
          ar: 'تعذر قراءة بيانات المستخدم.',
          en: 'Could not read user information.',
        ),
      );

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

      showError(
        text(
          ar: 'حدث خطأ أثناء حفظ إعداداتك.',
          en: 'An error occurred while saving your settings.',
        ),
      );
    }
  }

  // =========================================================
  // Placement test preparation
  // =========================================================

  Future<void> showTestPreparationDialog() async {
    if (selectedLearningLanguage == null) {
      return;
    }

    final shouldStart = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        final theme = Theme.of(dialogContext);

        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
          ),
          title: Text(
            text(ar: 'إعداد اختبار تحديد المستوى', en: 'Placement Test'),
          ),
          content: Text(
            text(
              ar: 'الخطوة التالية هي اختبار بسيط لتحديد مستواك في اللغة التي اخترتها.\n\nلن تختار المستوى بنفسك؛ سيحدده النظام بناءً على إجاباتك.',
              en: 'The next step is a short test to determine your level in the language you selected.\n\nYou will not choose the level yourself; the system will determine it from your answers.',
            ),
            style: theme.textTheme.bodyMedium,
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },
              child: Text(text(ar: 'لاحقًا', en: 'Later')),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },
              child: Text(text(ar: 'بدء الاختبار', en: 'Start test')),
            ),
          ],
        );
      },
    );

    if (shouldStart != true || !mounted || selectedLearningLanguage == null) {
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

    if (!mounted) return;

    if (result == null || result.isEmpty) {
      return;
    }

    // -------------------------------------------------------
    // The PlacementTestPage already finalized the profile
    // on the backend.
    // -------------------------------------------------------

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

  // =========================================================
  // Error
  // =========================================================

  void showError(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  // =========================================================
  // Step title
  // =========================================================

  String get currentTitle {
    switch (currentStep) {
      case 0:
        return text(ar: 'اختر لغة التطبيق', en: 'Choose app language');

      case 1:
        return text(ar: 'ما لغتك الأم؟', en: 'What is your native language?');

      case 2:
        return text(
          ar: 'ماذا تريد أن تتعلم؟',
          en: 'What do you want to learn?',
        );

      default:
        return '';
    }
  }

  String get currentDescription {
    switch (currentStep) {
      case 0:
        return text(
          ar: 'اختر اللغة التي تريد استخدامها لواجهة التطبيق.',
          en: 'Choose the language you want to use for the app interface.',
        );

      case 1:
        return text(
          ar: 'سنستخدم هذه اللغة لاحقًا لمساعدتك في الشرح والترجمة.',
          en: 'We will use this language later for explanations and translations.',
        );

      case 2:
        return text(
          ar: 'اختر اللغة التي تريد تعلمها. بعد ذلك سنجري اختبارًا لتحديد مستواك تلقائيًا.',
          en: 'Choose the language you want to learn. Then we will automatically determine your level.',
        );

      default:
        return '';
    }
  }

  // =========================================================
  // App language card
  // =========================================================

  Widget buildAppLanguageCard(Map<String, String> language, ThemeData theme) {
    final code = language['code']!;

    final name = language['name']!;

    final selected = selectedAppLanguage == code;

    return GestureDetector(
      onTap: isSaving
          ? null
          : () {
              selectApplicationLanguage(code);
            },
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
                  fontWeight: selected ? FontWeight.bold : FontWeight.w500,
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

  // =========================================================
  // User language card
  // =========================================================

  Widget buildUserLanguageCard(
    Map<String, String> language,
    ThemeData theme,
    String? selectedCode,
  ) {
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
                      text(
                        ar: 'لا يمكنك اختيار لغتك الأم كلغة للتعلم.',
                        en: 'You cannot choose your native language as your learning language.',
                      ),
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
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
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
                  fontWeight: selected ? FontWeight.bold : FontWeight.w500,
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

  // =========================================================
  // Current step content
  // =========================================================

  Widget buildStepContent(ThemeData theme) {
    if (currentStep == 0) {
      return Column(
        children: appLanguages
            .map((language) => buildAppLanguageCard(language, theme))
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

  // =========================================================
  // Build
  // =========================================================

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (isLoading) {
      return Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        body: Center(
          child: CircularProgressIndicator(color: theme.colorScheme.primary),
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
                icon: const Icon(Icons.arrow_back_rounded),
              )
            : null,
        title: Text(text(ar: 'إعداد حسابك', en: 'Set up your account')),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
              child: Column(
                children: [
                  Row(
                    children: List.generate(3, (index) {
                      final active = index <= currentStep;

                      return Expanded(
                        child: Container(
                          height: 5,
                          margin: EdgeInsets.only(right: index == 2 ? 0 : 6),
                          decoration: BoxDecoration(
                            color: active
                                ? theme.colorScheme.primary
                                : theme.dividerColor.withValues(alpha: 0.30),
                            borderRadius: BorderRadius.circular(20),
                          ),
                        ),
                      );
                    }),
                  ),
                  const SizedBox(height: 24),
                  Align(
                    alignment: AlignmentDirectional.centerStart,
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
                    alignment: AlignmentDirectional.centerStart,
                    child: Text(
                      currentDescription,
                      style: TextStyle(
                        fontSize: 14,
                        height: 1.5,
                        color: theme.textTheme.bodyMedium?.color?.withValues(alpha: 
                          0.70,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: buildStepContent(theme),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: (!canContinue || isSaving) ? null : continueStep,
                  style: ElevatedButton.styleFrom(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: isSaving
                      ? SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: theme.colorScheme.onPrimary,
                          ),
                        )
                      : Text(
                          currentStep == 2
                              ? text(
                                  ar: 'حفظ والمتابعة',
                                  en: 'Save and continue',
                                )
                              : text(ar: 'متابعة', en: 'Continue'),
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
