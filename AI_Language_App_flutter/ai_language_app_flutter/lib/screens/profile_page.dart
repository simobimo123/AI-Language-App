import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';
import '../core/language/language_controller.dart';
import '../core/storage/storage_service.dart';
import '../core/theme/theme_controller.dart';
import '../services/learning_language_controller.dart';
import 'login_page.dart';
import 'placement_test_page.dart';

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
  final ApiService apiService = ApiService();
  final StorageService storageService = StorageService();

  final LearningLanguageController learningLanguageController =
      LearningLanguageController.instance;

  static const Map<String, String> _appLanguages = {
    'ar': 'العربية',
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
  };

  static const List<String> _learningLanguageCodes = [
    'ar',
    'en',
    'fr',
    'es',
    'de',
    'tr',
  ];

  String name = 'Loading...';
  String email = '';
  String userId = '';
  String nativeLanguage = '';

  String? _nativeLanguageCode;
  String? _currentLearningLanguageCode;
  String? _currentLearningLevel;

  List<dynamic> _learningProfiles = [];

  bool isLoading = true;
  bool _isChangingLanguage = false;
  bool _isAddingLanguage = false;

  @override
  void initState() {
    super.initState();

    learningLanguageController.addListener(_onLearningLanguageChanged);

    loadProfile();
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);

    super.dispose();
  }

  void _onLearningLanguageChanged() {
    final language = learningLanguageController.currentLanguage;

    if (language == null ||
        language == _currentLearningLanguageCode ||
        !mounted) {
      return;
    }

    setState(() {
      _currentLearningLanguageCode = language;

      final profile = _getProfile(language);

      _currentLearningLevel = profile?['level']?.toString();
    });
  }

  Future<void> loadProfile() async {
    try {
      final user = await apiService.getCurrentUser();

      final profiles = await apiService.getLearningProfiles();

      if (!mounted) return;

      final nativeCode = user['native_language']?.toString();

      final currentLanguage = user['learning_language']?.toString();

      dynamic currentProfile;

      for (final profile in profiles) {
        if (profile['language'] == currentLanguage) {
          currentProfile = profile;
          break;
        }
      }

      final l10n = AppLocalizations.of(context)!;

      setState(() {
        name = user['name'] ?? 'Learner';

        email = user['email'] ?? '';

        userId = user['id']?.toString() ?? '';

        _nativeLanguageCode = nativeCode;

        nativeLanguage = _learningLanguageName(nativeCode, l10n);

        _currentLearningLanguageCode = currentLanguage;

        _currentLearningLevel = currentProfile?['level']?.toString();

        _learningProfiles = profiles;

        isLoading = false;
      });

      if (currentLanguage != null) {
        learningLanguageController.setLanguage(currentLanguage);
      }
    } catch (_) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        name = 'Unable to load profile';
      });
    }
  }

  String _learningLanguageName(String? code, AppLocalizations l10n) {
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
        return _germanName(l10n);

      case 'tr':
        return _turkishName(l10n);

      default:
        return code ?? '';
    }
  }

  String _germanName(AppLocalizations l10n) {
    switch (widget.languageController.locale.languageCode) {
      case 'ar':
        return 'الألمانية';

      case 'fr':
        return 'Allemand';

      case 'es':
        return 'Alemán';

      case 'ja':
        return 'ドイツ語';

      case 'ko':
        return '독일어';

      case 'zh':
        return '德语';

      case 'en':
      default:
        return 'German';
    }
  }

  String _turkishName(AppLocalizations l10n) {
    switch (widget.languageController.locale.languageCode) {
      case 'ar':
        return 'التركية';

      case 'fr':
        return 'Turc';

      case 'es':
        return 'Turco';

      case 'ja':
        return 'トルコ語';

      case 'ko':
        return '터키어';

      case 'zh':
        return '土耳其语';

      case 'en':
      default:
        return 'Turkish';
    }
  }

  String _levelName(String? level, AppLocalizations l10n) {
    switch (level) {
      case 'PRE_A1':
        return 'Pre-A1';

      case 'A1':
        return l10n.levelA1;

      case 'A2':
        return l10n.levelA2;

      case 'B1':
        return l10n.levelB1;

      case 'B2':
        return l10n.levelB2;

      case 'C1':
        return l10n.levelC1;

      case 'C2':
        return l10n.levelC2;

      default:
        return level ?? '';
    }
  }

  String _appLanguageName(String code, AppLocalizations l10n) {
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

      default:
        return code;
    }
  }

  dynamic _getProfile(String language) {
    for (final profile in _learningProfiles) {
      if (profile['language'] == language) {
        return profile;
      }
    }

    return null;
  }

  Future<void> _changeAppLanguage(String languageCode) async {
    if (widget.languageController.locale.languageCode == languageCode) {
      return;
    }

    await widget.languageController.setLanguage(languageCode);

    if (!mounted) return;

    setState(() {});
  }

  Future<void> _showAppLanguages() async {
    final l10n = AppLocalizations.of(context)!;

    final currentLanguage = widget.languageController.locale.languageCode;

    final selectedLanguage = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (context) {
        final theme = Theme.of(context);

        final maxHeight = MediaQuery.of(context).size.height * 0.78;

        return SafeArea(
          child: SizedBox(
            height: maxHeight,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.appLanguage,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    l10n.language,
                    style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
                  ),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ListView.separated(
                      physics: const BouncingScrollPhysics(),
                      itemCount: _appLanguages.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final entry = _appLanguages.entries.elementAt(index);

                        final isSelected = entry.key == currentLanguage;

                        return ListTile(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                          tileColor: isSelected
                              ? theme.colorScheme.primaryContainer
                              : theme.colorScheme.surfaceContainerHighest,
                          leading: Icon(
                            isSelected
                                ? Icons.check_circle_rounded
                                : Icons.language_rounded,
                            color: isSelected
                                ? theme.colorScheme.primary
                                : theme.colorScheme.onSurfaceVariant,
                          ),
                          title: Text(
                            _appLanguageName(entry.key, l10n),
                            style: TextStyle(
                              fontWeight: isSelected
                                  ? FontWeight.bold
                                  : FontWeight.w500,
                            ),
                          ),
                          trailing: isSelected
                              ? Icon(
                                  Icons.check_rounded,
                                  color: theme.colorScheme.primary,
                                )
                              : null,
                          onTap: () {
                            Navigator.pop(context, entry.key);
                          },
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

    if (selectedLanguage == null || !mounted) {
      return;
    }

    await _changeAppLanguage(selectedLanguage);
  }

  Future<void> _changeLearningLanguage(String language) async {
    if (_currentLearningLanguageCode == language) {
      return;
    }

    final l10n = AppLocalizations.of(context)!;

    setState(() {
      _isChangingLanguage = true;
    });

    try {
      final result = await apiService.switchLearningLanguage(
        language: language,
      );

      if (!mounted) return;

      setState(() {
        _currentLearningLanguageCode = language;

        _currentLearningLevel = result['level']?.toString();

        _isChangingLanguage = false;
      });

      learningLanguageController.setLanguage(language);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            l10n.learningLanguageChanged(_learningLanguageName(language, l10n)),
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isChangingLanguage = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _showLearningLanguages() async {
    if (_isChangingLanguage || _isAddingLanguage) {
      return;
    }

    final l10n = AppLocalizations.of(context)!;

    final selectedLanguage = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (context) {
        final theme = Theme.of(context);

        final maxHeight = MediaQuery.of(context).size.height * 0.78;

        return SafeArea(
          child: SizedBox(
            height: maxHeight,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.learningLanguages,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    l10n.chooseLearningLanguage,
                    style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
                  ),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ListView(
                      physics: const BouncingScrollPhysics(),
                      children: [
                        if (_learningProfiles.isEmpty)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 20),
                            child: Text(
                              l10n.noLearningLanguages,
                              textAlign: TextAlign.center,
                            ),
                          )
                        else
                          ..._learningProfiles.map((profile) {
                            final language =
                                profile['language']?.toString() ?? '';

                            final level = profile['level']?.toString() ?? '';

                            final isSelected =
                                language == _currentLearningLanguageCode;

                            return Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                tileColor: isSelected
                                    ? theme.colorScheme.primaryContainer
                                    : theme.colorScheme.surfaceContainerHighest,
                                leading: Icon(
                                  isSelected
                                      ? Icons.check_circle_rounded
                                      : Icons.language_rounded,
                                  color: isSelected
                                      ? theme.colorScheme.primary
                                      : theme.colorScheme.onSurfaceVariant,
                                ),
                                title: Text(
                                  _learningLanguageName(language, l10n),
                                  style: TextStyle(
                                    fontWeight: isSelected
                                        ? FontWeight.bold
                                        : FontWeight.w500,
                                  ),
                                ),
                                subtitle: Text(_levelName(level, l10n)),
                                trailing: isSelected
                                    ? Icon(
                                        Icons.check_rounded,
                                        color: theme.colorScheme.primary,
                                      )
                                    : null,
                                onTap: () {
                                  Navigator.pop(context, language);
                                },
                              ),
                            );
                          }),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                          onPressed: () {
                            Navigator.pop(context, '__add_language__');
                          },
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

    if (selectedLanguage == null || !mounted) {
      return;
    }

    if (selectedLanguage == '__add_language__') {
      await _showAddLanguageDialog();
      return;
    }

    await _changeLearningLanguage(selectedLanguage);
  }

  // =========================================================
  // Add new learning language
  // =========================================================
  //
  // IMPORTANT:
  //
  // The user chooses ONLY the language.
  //
  // The level is determined by PlacementTestPage.
  // =========================================================

  Future<void> _showAddLanguageDialog() async {
    if (_isChangingLanguage || _isAddingLanguage) {
      return;
    }

    final l10n = AppLocalizations.of(context)!;

    String? selectedLanguage;

    final existingLanguages = _learningProfiles
        .map((profile) => profile['language']?.toString())
        .whereType<String>()
        .toSet();

    final availableLanguages = _learningLanguageCodes.where((code) {
      return code != _nativeLanguageCode && !existingLanguages.contains(code);
    }).toList();

    if (availableLanguages.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.noNewLanguagesAvailable),
          behavior: SnackBarBehavior.floating,
        ),
      );

      return;
    }

    final selected = await showDialog<String>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text(l10n.addLanguageTitle),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24),
              ),
              content: DropdownButtonFormField<String>(
                initialValue: selectedLanguage,
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: l10n.learningLanguage,
                  prefixIcon: const Icon(Icons.language_rounded),
                  border: const OutlineInputBorder(),
                ),
                items: availableLanguages.map((code) {
                  return DropdownMenuItem<String>(
                    value: code,
                    child: Text(_learningLanguageName(code, l10n)),
                  );
                }).toList(),
                onChanged: (value) {
                  setDialogState(() {
                    selectedLanguage = value;
                  });
                },
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  child: Text(l10n.cancel),
                ),
                FilledButton(
                  onPressed: selectedLanguage == null
                      ? null
                      : () {
                          Navigator.pop(context, selectedLanguage);
                        },
                  child: Text(l10n.add),
                ),
              ],
            );
          },
        );
      },
    );

    if (selected == null || !mounted) {
      return;
    }

    await _startPlacementForLanguage(selected);
  }

  // =========================================================
  // Start placement for a new language
  // =========================================================

  Future<void> _startPlacementForLanguage(String language) async {
    if (_isChangingLanguage || _isAddingLanguage) {
      return;
    }

    setState(() {
      _isAddingLanguage = true;
    });

    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => PlacementTestPage(
          themeController: widget.themeController,
          languageController: widget.languageController,
          language: language,
        ),
      ),
    );

    if (!mounted) return;

    // -------------------------------------------------------
    // PlacementTestPage finalizes the profile on the backend.
    //
    // If the user leaves the test before finishing, there is
    // no profile yet, so we simply stay in the current screen.
    // -------------------------------------------------------

    if (result == null || result.isEmpty) {
      setState(() {
        _isAddingLanguage = false;
      });

      return;
    }

    try {
      // -----------------------------------------------------
      // Refresh all profiles after placement.
      // -----------------------------------------------------

      final profiles = await apiService.getLearningProfiles();

      // -----------------------------------------------------
      // The finalize endpoint also switches the backend
      // current learning language.
      //
      // We make the local state match that result.
      // -----------------------------------------------------

      learningLanguageController.setLanguage(language);

      if (!mounted) return;

      dynamic newProfile;

      for (final profile in profiles) {
        if (profile['language'] == language) {
          newProfile = profile;
          break;
        }
      }

      setState(() {
        _learningProfiles = profiles;

        _currentLearningLanguageCode = language;

        _currentLearningLevel = newProfile?['level']?.toString();

        _isAddingLanguage = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10nLearningLanguageAdded(language)),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isAddingLanguage = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  String l10nLearningLanguageAdded(String language) {
    final l10n = AppLocalizations.of(context)!;

    return l10n.learningLanguageChanged(_learningLanguageName(language, l10n));
  }

  Future<void> logout() async {
    await storageService.deleteToken();

    learningLanguageController.clear();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (_) => LoginPage(
          themeController: widget.themeController,
          languageController: widget.languageController,
        ),
      ),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final l10n = AppLocalizations.of(context)!;

    final currentProfile = _currentLearningLanguageCode == null
        ? null
        : _getProfile(_currentLearningLanguageCode!);

    final currentLearningLanguage = _learningLanguageName(
      _currentLearningLanguageCode,
      l10n,
    );

    final currentLevel =
        currentProfile?['level']?.toString() ?? _currentLearningLevel ?? '';

    final currentAppLanguageCode =
        widget.languageController.locale.languageCode;

    final currentAppLanguage = _appLanguageName(currentAppLanguageCode, l10n);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: theme.scaffoldBackgroundColor,
        elevation: 0,
        title: Text(
          l10n.account,
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
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
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
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

                _ProfileInfoCard(
                  icon: Icons.person_outline_rounded,
                  title: l10n.name,
                  value: name,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.email_outlined,
                  title: l10n.email,
                  value: email,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.badge_outlined,
                  title: l10n.userId,
                  value: userId,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.translate_rounded,
                  title: l10n.nativeLanguage,
                  value: nativeLanguage,
                ),

                const SizedBox(height: 12),

                _LearningLanguageCard(
                  language: currentLearningLanguage,
                  level: _levelName(currentLevel, l10n),
                  profilesCount: _learningProfiles.length,
                  isLoading: _isChangingLanguage || _isAddingLanguage,
                  onTap: _showLearningLanguages,
                ),

                const SizedBox(height: 28),

                Text(
                  l10n.appLanguage,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 12),

                _AppLanguageCard(
                  language: currentAppLanguage,
                  onTap: _showAppLanguages,
                ),

                const SizedBox(height: 28),

                Text(
                  l10n.appAppearance,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 12),

                _ThemeSettingsCard(themeController: widget.themeController),

                const SizedBox(height: 30),

                SizedBox(
                  height: 52,
                  child: OutlinedButton.icon(
                    onPressed: logout,
                    icon: const Icon(Icons.logout_rounded),
                    label: Text(
                      l10n.logout,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: BorderSide(color: Colors.red.shade200),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

// =========================================================
// App language card
// =========================================================

class _AppLanguageCard extends StatelessWidget {
  final String language;
  final VoidCallback onTap;

  const _AppLanguageCard({required this.language, required this.onTap});

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
              child: Icon(
                Icons.language_rounded,
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),

            const SizedBox(width: 14),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.appLanguage,
                    style: TextStyle(
                      fontSize: 12,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    language,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    l10n.language,
                    style: TextStyle(
                      fontSize: 12,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(width: 8),

            Icon(
              Icons.chevron_left_rounded,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }
}

// =========================================================
// Profile info card
// =========================================================

class _ProfileInfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _ProfileInfoCard({
    required this.icon,
    required this.title,
    required this.value,
  });

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
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 12,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
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

// =========================================================
// Learning language card
// =========================================================

class _LearningLanguageCard extends StatelessWidget {
  final String language;
  final String level;
  final int profilesCount;
  final bool isLoading;
  final VoidCallback onTap;

  const _LearningLanguageCard({
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
              child: Icon(
                Icons.school_outlined,
                color: theme.colorScheme.onPrimaryContainer,
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
                    ),
                  ),

                  const SizedBox(height: 4),

                  Text(
                    language,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),

                  if (level.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      level,
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],

                  const SizedBox(height: 3),

                  Text(
                    profilesCount > 1
                        ? l10n.switchLearningLanguage
                        : l10n.addOrChangeLearningLanguage,
                    style: TextStyle(
                      fontSize: 12,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(width: 8),

            if (isLoading)
              const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2.5),
              )
            else
              Icon(
                Icons.chevron_left_rounded,
                color: theme.colorScheme.onSurfaceVariant,
              ),
          ],
        ),
      ),
    );
  }
}

// =========================================================
// Theme settings
// =========================================================

class _ThemeSettingsCard extends StatelessWidget {
  final ThemeController themeController;

  const _ThemeSettingsCard({required this.themeController});

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
              ButtonSegment<ThemeMode>(
                value: ThemeMode.system,
                icon: const Icon(Icons.brightness_auto_rounded),
                label: Text(l10n.auto),
              ),
              ButtonSegment<ThemeMode>(
                value: ThemeMode.light,
                icon: const Icon(Icons.light_mode_outlined),
                label: Text(l10n.light),
              ),
              ButtonSegment<ThemeMode>(
                value: ThemeMode.dark,
                icon: const Icon(Icons.dark_mode_outlined),
                label: Text(l10n.dark),
              ),
            ],
            selected: <ThemeMode>{themeController.themeMode},
            onSelectionChanged: (selection) {
              if (selection.isEmpty) {
                return;
              }

              final selectedMode = selection.first;

              themeController.setThemeMode(selectedMode);
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
