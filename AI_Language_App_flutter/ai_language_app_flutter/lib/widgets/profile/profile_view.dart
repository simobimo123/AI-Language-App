import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../core/theme/theme_controller.dart';

class ProfileView extends StatelessWidget {
  final String name;
  final String email;
  final String userId;
  final String nativeLanguage;
  final String currentLearningLanguage;
  final String currentLevel;
  final int profilesCount;
  final bool isChangingLanguage;
  final bool isAddingLanguage;
  final String currentAppLanguage;
  final ThemeController themeController;
  final VoidCallback onLearningLanguageTap;
  final VoidCallback onAppLanguageTap;
  final VoidCallback onLogout;

  const ProfileView({
    super.key,
    required this.name,
    required this.email,
    required this.userId,
    required this.nativeLanguage,
    required this.currentLearningLanguage,
    required this.currentLevel,
    required this.profilesCount,
    required this.isChangingLanguage,
    required this.isAddingLanguage,
    required this.currentAppLanguage,
    required this.themeController,
    required this.onLearningLanguageTap,
    required this.onAppLanguageTap,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const SizedBox(height: 10),
        Center(
          child: Container(
            width: 92,
            height: 92,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.person_rounded,
              size: 48,
              color: theme.colorScheme.onPrimaryContainer,
            ),
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: Text(
            name,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
        ),
        const SizedBox(height: 6),
        Center(
          child: Text(
            email,
            style: TextStyle(
              fontSize: 14,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const SizedBox(height: 30),
        ProfileInfoCard(icon: Icons.person_outline_rounded, title: l10n.name, value: name),
        const SizedBox(height: 12),
        ProfileInfoCard(icon: Icons.email_outlined, title: l10n.email, value: email),
        const SizedBox(height: 12),
        ProfileInfoCard(icon: Icons.badge_outlined, title: l10n.userId, value: userId),
        const SizedBox(height: 12),
        ProfileInfoCard(
          icon: Icons.translate_rounded,
          title: l10n.nativeLanguage,
          value: nativeLanguage,
        ),
        const SizedBox(height: 12),
        LearningLanguageCard(
          language: currentLearningLanguage,
          level: currentLevel,
          profilesCount: profilesCount,
          isLoading: isChangingLanguage || isAddingLanguage,
          onTap: onLearningLanguageTap,
        ),
        const SizedBox(height: 28),
        Text(
          l10n.appLanguage,
          style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        AppLanguageCard(language: currentAppLanguage, onTap: onAppLanguageTap),
        const SizedBox(height: 28),
        Text(
          l10n.appAppearance,
          style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ThemeSettingsCard(themeController: themeController),
        const SizedBox(height: 30),
        SizedBox(
          height: 52,
          child: OutlinedButton.icon(
            onPressed: onLogout,
            icon: const Icon(Icons.logout_rounded),
            label: Text(
              l10n.logout,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.red,
              side: BorderSide(color: Colors.red.shade200),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
        ),
      ],
    );
  }
}

class AppLanguageCard extends StatelessWidget {
  final String language;
  final VoidCallback onTap;

  const AppLanguageCard({super.key, required this.language, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: theme.colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(Icons.language_rounded, color: theme.colorScheme.onPrimaryContainer),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l10n.appLanguage, style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 4),
                  Text(language, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 3),
                  Text(l10n.language, style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Icon(Icons.chevron_left_rounded, color: theme.colorScheme.onSurfaceVariant),
          ],
        ),
      ),
    );
  }
}

class ProfileInfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const ProfileInfoCard({super.key, required this.icon, required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: theme.colorScheme.onPrimaryContainer),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant)),
                const SizedBox(height: 4),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class LearningLanguageCard extends StatelessWidget {
  final String language;
  final String level;
  final int profilesCount;
  final bool isLoading;
  final VoidCallback onTap;

  const LearningLanguageCard({
    super.key,
    required this.language,
    required this.level,
    required this.profilesCount,
    required this.isLoading,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return InkWell(
      onTap: isLoading ? null : onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: theme.colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(Icons.school_outlined, color: theme.colorScheme.onPrimaryContainer),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l10n.learningLanguage, style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 4),
                  Text(language, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  if (level.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(level, style: TextStyle(fontSize: 12, color: theme.colorScheme.primary, fontWeight: FontWeight.w600)),
                  ],
                  const SizedBox(height: 3),
                  Text(
                    profilesCount > 1 ? l10n.switchLearningLanguage : l10n.addOrChangeLearningLanguage,
                    style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (isLoading)
              const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
            else
              Icon(Icons.chevron_left_rounded, color: theme.colorScheme.onSurfaceVariant),
          ],
        ),
      ),
    );
  }
}

class ThemeSettingsCard extends StatelessWidget {
  final ThemeController themeController;

  const ThemeSettingsCard({super.key, required this.themeController});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: themeController,
      builder: (context, _) {
        final theme = Theme.of(context);
        final l10n = AppLocalizations.of(context)!;

        return Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: theme.colorScheme.outlineVariant),
          ),
          child: SegmentedButton<ThemeMode>(
            segments: [
              ButtonSegment(value: ThemeMode.system, icon: const Icon(Icons.brightness_auto_rounded), label: Text(l10n.auto)),
              ButtonSegment(value: ThemeMode.light, icon: const Icon(Icons.light_mode_outlined), label: Text(l10n.light)),
              ButtonSegment(value: ThemeMode.dark, icon: const Icon(Icons.dark_mode_outlined), label: Text(l10n.dark)),
            ],
            selected: {themeController.themeMode},
            onSelectionChanged: (selection) {
              if (selection.isNotEmpty) {
                themeController.setThemeMode(selection.first);
              }
            },
            showSelectedIcon: false,
            style: ButtonStyle(
              visualDensity: VisualDensity.compact,
              textStyle: WidgetStatePropertyAll(theme.textTheme.labelMedium),
            ),
          ),
        );
      },
    );
  }
}
