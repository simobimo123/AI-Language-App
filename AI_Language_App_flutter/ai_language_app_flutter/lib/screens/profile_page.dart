import 'package:flutter/material.dart';

import '../controllers/profile_controller.dart';
import '../l10n/app_localizations.dart';
import '../core/theme/theme_controller.dart';
import '../core/language/language_controller.dart';
import '../widgets/profile/profile_dialogs.dart';
import '../widgets/profile/profile_view.dart';

class ProfilePage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const ProfilePage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  late final ProfileController controller;

  @override
  void initState() {
    super.initState();
    controller = ProfileController(
      themeController: widget.themeController,
      languageController: widget.languageController,
    );
    controller.loadProfile(context);
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final l10n = AppLocalizations.of(context)!;
        final currentProfile = controller.currentLearningLanguageCode == null
            ? null
            : controller.getProfile(controller.currentLearningLanguageCode!);
        final currentLevel = currentProfile?['level']?.toString() ??
            controller.currentLearningLevel ??
            '';
        final appLanguageCode = widget.languageController.locale.languageCode;

        return Scaffold(
          backgroundColor: Theme.of(context).scaffoldBackgroundColor,
          appBar: AppBar(
            backgroundColor: Theme.of(context).scaffoldBackgroundColor,
            elevation: 0,
            title: Text(
              l10n.account,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
          ),
          body: controller.isLoading
              ? const Center(child: CircularProgressIndicator())
              : ProfileView(
                  name: controller.name,
                  email: controller.email,
                  userId: controller.userId,
                  nativeLanguage: controller.nativeLanguage,
                  currentLearningLanguage: controller.languageName(
                    controller.currentLearningLanguageCode,
                    l10n,
                  ),
                  currentLevel: controller.levelName(currentLevel, l10n),
                  profilesCount: controller.learningProfiles.length,
                  isChangingLanguage: controller.isChangingLanguage,
                  isAddingLanguage: controller.isAddingLanguage,
                  currentAppLanguage: controller.appLanguageName(
                    appLanguageCode,
                    l10n,
                  ),
                  themeController: widget.themeController,
                  onLearningLanguageTap: () =>
                      ProfileDialogs.showLearningLanguages(context, controller),
                  onAppLanguageTap: () =>
                      ProfileDialogs.showAppLanguages(context, controller),
                  onLogout: () => controller.logout(context),
                ),
        );
      },
    );
  }
}
