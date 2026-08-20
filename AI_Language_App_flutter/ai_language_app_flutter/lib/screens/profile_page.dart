import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../services/theme_controller.dart';
import '../services/learning_language_controller.dart';
import 'login_page.dart';

class ProfilePage extends StatefulWidget {
  final ThemeController themeController;

  const ProfilePage({super.key, required this.themeController});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final ApiService apiService = ApiService();
  final StorageService storageService = StorageService();
  final LearningLanguageController learningLanguageController =
      LearningLanguageController.instance;

  static const Map<String, String> _languages = {
    'ar': 'العربية',
    'en': 'الإنجليزية',
    'fr': 'الفرنسية',
    'es': 'الإسبانية',
    'de': 'الألمانية',
    'tr': 'التركية',
  };

  static const Map<String, String> _levels = {
    'A1': 'A1 - مبتدئ',
    'A2': 'A2 - أساسي',
    'B1': 'B1 - متوسط',
    'B2': 'B2 - فوق المتوسط',
    'C1': 'C1 - متقدم',
    'C2': 'C2 - متقن',
  };

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

      setState(() {
        name = user['name'] ?? 'Learner';
        email = user['email'] ?? '';
        userId = user['id']?.toString() ?? '';

        _nativeLanguageCode = nativeCode;
        nativeLanguage = _languageName(nativeCode);

        _currentLearningLanguageCode = currentLanguage;

        _currentLearningLevel = currentProfile?['level']?.toString();

        _learningProfiles = profiles;

        isLoading = false;
      });

      if (currentLanguage != null) {
        learningLanguageController.setLanguage(currentLanguage);
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        name = 'Unable to load profile';
      });
    }
  }

  String _languageName(String? code) {
    return _languages[code] ?? code ?? '';
  }

  String _levelName(String? level) {
    return _levels[level] ?? level ?? '';
  }

  dynamic _getProfile(String language) {
    for (final profile in _learningProfiles) {
      if (profile['language'] == language) {
        return profile;
      }
    }

    return null;
  }

  Future<void> _changeLearningLanguage(String language) async {
    if (_currentLearningLanguageCode == language) {
      return;
    }

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

      // إخبار جميع الصفحات بأن لغة التعلّم تغيرت.
      learningLanguageController.setLanguage(language);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('تم تغيير لغة التعلّم إلى ${_languageName(language)}'),
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

    final selectedLanguage = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (context) {
        final theme = Theme.of(context);

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'لغات التعلّم',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'اختر إحدى لغاتك أو أضف لغة جديدة.',
                  style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
                ),
                const SizedBox(height: 16),
                if (_learningProfiles.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 20),
                    child: Text(
                      'لا توجد لغات تعلّم بعد.',
                      textAlign: TextAlign.center,
                    ),
                  )
                else
                  ..._learningProfiles.map((profile) {
                    final language = profile['language']?.toString() ?? '';

                    final level = profile['level']?.toString() ?? '';

                    final isSelected = language == _currentLearningLanguageCode;

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
                          _languageName(language),
                          style: TextStyle(
                            fontWeight: isSelected
                                ? FontWeight.bold
                                : FontWeight.w500,
                          ),
                        ),
                        subtitle: Text(_levelName(level)),
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
                  label: const Text('إضافة لغة جديدة'),
                ),
              ],
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

  Future<void> _showAddLanguageDialog() async {
    if (_isChangingLanguage || _isAddingLanguage) {
      return;
    }

    String? selectedLanguage;
    String selectedLevel = 'A1';

    final existingLanguages = _learningProfiles
        .map((profile) => profile['language']?.toString())
        .whereType<String>()
        .toSet();

    final availableLanguages = _languages.entries.where((entry) {
      return entry.key != _nativeLanguageCode &&
          !existingLanguages.contains(entry.key);
    }).toList();

    if (availableLanguages.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('لا توجد لغات جديدة متاحة للإضافة.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    final result = await showDialog<_AddLanguageResult>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('إضافة لغة جديدة'),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24),
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    value: selectedLanguage,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'لغة التعلّم',
                      prefixIcon: Icon(Icons.language_rounded),
                      border: OutlineInputBorder(),
                    ),
                    items: availableLanguages.map((entry) {
                      return DropdownMenuItem(
                        value: entry.key,
                        child: Text(entry.value),
                      );
                    }).toList(),
                    onChanged: (value) {
                      setDialogState(() {
                        selectedLanguage = value;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: selectedLevel,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'مستواك في اللغة',
                      prefixIcon: Icon(Icons.bar_chart_rounded),
                      border: OutlineInputBorder(),
                    ),
                    items: _levels.entries.map((entry) {
                      return DropdownMenuItem(
                        value: entry.key,
                        child: Text(entry.value),
                      );
                    }).toList(),
                    onChanged: (value) {
                      if (value == null) {
                        return;
                      }

                      setDialogState(() {
                        selectedLevel = value;
                      });
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  child: const Text('إلغاء'),
                ),
                FilledButton(
                  onPressed: selectedLanguage == null
                      ? null
                      : () {
                          Navigator.pop(
                            context,
                            _AddLanguageResult(
                              language: selectedLanguage!,
                              level: selectedLevel,
                            ),
                          );
                        },
                  child: const Text('إضافة'),
                ),
              ],
            );
          },
        );
      },
    );

    if (result == null || !mounted) {
      return;
    }

    await _addLearningLanguage(language: result.language, level: result.level);
  }

  Future<void> _addLearningLanguage({
    required String language,
    required String level,
  }) async {
    setState(() {
      _isAddingLanguage = true;
    });

    try {
      final profile = await apiService.createLearningProfile(
        language: language,
        level: level,
      );

      if (!mounted) return;

      setState(() {
        _learningProfiles = [..._learningProfiles, profile];
        _isAddingLanguage = false;
      });

      await _changeLearningLanguage(language);
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

  Future<void> logout() async {
    await storageService.deleteToken();

    learningLanguageController.clear();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (_) => LoginPage(themeController: widget.themeController),
      ),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final currentProfile = _currentLearningLanguageCode == null
        ? null
        : _getProfile(_currentLearningLanguageCode!);

    final currentLearningLanguage = _languageName(_currentLearningLanguageCode);

    final currentLevel =
        currentProfile?['level']?.toString() ?? _currentLearningLevel ?? '';

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: theme.scaffoldBackgroundColor,
        elevation: 0,
        title: const Text(
          'حسابي',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
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
                  title: 'الاسم',
                  value: name,
                ),
                const SizedBox(height: 12),
                _ProfileInfoCard(
                  icon: Icons.email_outlined,
                  title: 'البريد الإلكتروني',
                  value: email,
                ),
                const SizedBox(height: 12),
                _ProfileInfoCard(
                  icon: Icons.badge_outlined,
                  title: 'رقم المستخدم',
                  value: userId,
                ),
                const SizedBox(height: 12),
                _ProfileInfoCard(
                  icon: Icons.translate_rounded,
                  title: 'لغتك الأم',
                  value: nativeLanguage,
                ),
                const SizedBox(height: 12),
                _LearningLanguageCard(
                  language: currentLearningLanguage,
                  level: _levelName(currentLevel),
                  profilesCount: _learningProfiles.length,
                  isLoading: _isChangingLanguage || _isAddingLanguage,
                  onTap: _showLearningLanguages,
                ),
                const SizedBox(height: 28),
                Text(
                  'مظهر التطبيق',
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
                    label: const Text(
                      'تسجيل الخروج',
                      style: TextStyle(fontWeight: FontWeight.w600),
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

class _AddLanguageResult {
  final String language;
  final String level;

  const _AddLanguageResult({required this.language, required this.level});
}

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
                    'لغة التعلّم',
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
                        ? 'اضغط لتبديل لغة التعلّم'
                        : 'اضغط لإضافة أو تغيير لغة',
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

class _ThemeSettingsCard extends StatelessWidget {
  final ThemeController themeController;

  const _ThemeSettingsCard({required this.themeController});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: SegmentedButton<ThemeMode>(
        segments: const [
          ButtonSegment(
            value: ThemeMode.system,
            icon: Icon(Icons.brightness_auto_rounded),
            label: Text('تلقائي'),
          ),
          ButtonSegment(
            value: ThemeMode.light,
            icon: Icon(Icons.light_mode_outlined),
            label: Text('فاتح'),
          ),
          ButtonSegment(
            value: ThemeMode.dark,
            icon: Icon(Icons.dark_mode_outlined),
            label: Text('داكن'),
          ),
        ],
        selected: {themeController.themeMode},
        onSelectionChanged: (selection) {
          themeController.setThemeMode(selection.first);
        },
        showSelectedIcon: false,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          textStyle: WidgetStatePropertyAll(theme.textTheme.labelMedium),
        ),
      ),
    );
  }
}
