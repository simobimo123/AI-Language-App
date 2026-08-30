import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../controllers/profile_controller.dart';

class ProfileDialogs {
  static Future<void> showAppLanguages(
    BuildContext context,
    ProfileController controller,
  ) async {
    final l10n = AppLocalizations.of(context)!;
    final current = controller.languageController.locale.languageCode;
    final selected = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (context) {
        final theme = Theme.of(context);
        return SafeArea(
          child: SizedBox(
            height: MediaQuery.of(context).size.height * .78,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l10n.appLanguage, style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(l10n.language, style: TextStyle(color: theme.colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ListView.separated(
                      physics: const BouncingScrollPhysics(),
                      itemCount: ProfileController.appLanguages.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (_, index) {
                        final entry = ProfileController.appLanguages.entries.elementAt(index);
                        final selected = entry.key == current;
                        return ListTile(
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          tileColor: selected ? theme.colorScheme.primaryContainer : theme.colorScheme.surfaceContainerHighest,
                          leading: Icon(selected ? Icons.check_circle_rounded : Icons.language_rounded,
                              color: selected ? theme.colorScheme.primary : theme.colorScheme.onSurfaceVariant),
                          title: Text(controller.appLanguageName(entry.key, l10n), style: TextStyle(fontWeight: selected ? FontWeight.bold : FontWeight.w500)),
                          trailing: selected ? Icon(Icons.check_rounded, color: theme.colorScheme.primary) : null,
                          onTap: () => Navigator.pop(context, entry.key),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
    if (selected != null && context.mounted) await controller.changeAppLanguage(selected);
  }

  static Future<void> showLearningLanguages(
    BuildContext context,
    ProfileController controller,
  ) async {
    if (controller.isChangingLanguage || controller.isAddingLanguage) return;
    final l10n = AppLocalizations.of(context)!;
    final selected = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (context) {
        final theme = Theme.of(context);
        return SafeArea(
          child: SizedBox(
            height: MediaQuery.of(context).size.height * .78,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l10n.learningLanguages, style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(l10n.chooseLearningLanguage, style: TextStyle(color: theme.colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ListView(
                      physics: const BouncingScrollPhysics(),
                      children: [
                        if (controller.learningProfiles.isEmpty)
                          Padding(padding: const EdgeInsets.symmetric(vertical: 20), child: Text(l10n.noLearningLanguages, textAlign: TextAlign.center))
                        else
                          ...controller.learningProfiles.map((profile) {
                            final language = profile['language']?.toString() ?? '';
                            final level = profile['level']?.toString() ?? '';
                            final selected = language == controller.currentLearningLanguageCode;
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                tileColor: selected ? theme.colorScheme.primaryContainer : theme.colorScheme.surfaceContainerHighest,
                                leading: Icon(selected ? Icons.check_circle_rounded : Icons.language_rounded,
                                    color: selected ? theme.colorScheme.primary : theme.colorScheme.onSurfaceVariant),
                                title: Text(controller.languageName(language, l10n), style: TextStyle(fontWeight: selected ? FontWeight.bold : FontWeight.w500)),
                                subtitle: Text(controller.levelName(level, l10n)),
                                trailing: selected ? Icon(Icons.check_rounded, color: theme.colorScheme.primary) : null,
                                onTap: () => Navigator.pop(context, language),
                              ),
                            );
                          }),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                          onPressed: () => Navigator.pop(context, '__add_language__'),
                          icon: const Icon(Icons.add_rounded),
                          label: Text(l10n.addNewLanguage),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
    if (selected == null || !context.mounted) return;
    if (selected == '__add_language__') {
      await showAddLanguage(context, controller);
    } else {
      await controller.changeLearningLanguage(context, selected);
    }
  }

  static Future<void> showAddLanguage(BuildContext context, ProfileController controller) async {
    if (controller.isChangingLanguage || controller.isAddingLanguage) return;
    final l10n = AppLocalizations.of(context)!;
    String? selected;
    final existing = controller.learningProfiles.map((p) => p['language']?.toString()).whereType<String>().toSet();
    final available = ProfileController.learningLanguageCodes.where((code) => code != controller.nativeLanguageCode && !existing.contains(code)).toList();
    if (available.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.noNewLanguagesAvailable), behavior: SnackBarBehavior.floating));
      return;
    }
    final result = await showDialog<String>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: Text(l10n.addLanguageTitle),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          content: DropdownButtonFormField<String>(
            initialValue: selected,
            isExpanded: true,
            decoration: InputDecoration(labelText: l10n.learningLanguage, prefixIcon: const Icon(Icons.language_rounded), border: const OutlineInputBorder()),
            items: available.map((code) => DropdownMenuItem(value: code, child: Text(controller.languageName(code, l10n)))).toList(),
            onChanged: (value) => setState(() => selected = value),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
            FilledButton(onPressed: selected == null ? null : () => Navigator.pop(context, selected), child: Text(l10n.add)),
          ],
        ),
      ),
    );
    if (result != null && context.mounted) await controller.startPlacementForLanguage(context, result);
  }
}
