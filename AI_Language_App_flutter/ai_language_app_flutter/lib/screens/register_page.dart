import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';
import '../services/language_controller.dart';
import '../services/theme_controller.dart';

class RegisterPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const RegisterPage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _formKey = GlobalKey<FormState>();
  final _apiService = ApiService();

  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  static const Map<String, String> _languages = {
    'ar': 'العربية',
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'de': 'Deutsch',
    'tr': 'Türkçe',
  };

  String _nativeLanguage = 'ar';
  String _learningLanguage = 'en';
  String _learningLevel = 'A1';

  bool _isLoading = false;
  bool _isPasswordVisible = false;
  String? _errorMessage;

  Future<void> _register() async {
    final l10n = AppLocalizations.of(context)!;

    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_nativeLanguage == _learningLanguage) {
      setState(() {
        _errorMessage = l10n.differentLanguages;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await _apiService.register(
        name: _nameController.text.trim(),
        email: _emailController.text.trim(),
        password: _passwordController.text,
        nativeLanguage: _nativeLanguage,
        learningLanguage: _learningLanguage,
        learningLevel: _learningLevel,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.accountCreated),
        ),
      );

      Navigator.pop(context);
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _errorMessage = l10n.registrationError;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  String _languageName(
    String code,
    AppLocalizations l10n,
  ) {
    switch (code) {
      case 'ar':
        return l10n.arabic;
      case 'en':
        return l10n.english;
      case 'fr':
        return l10n.french;
      case 'es':
        return l10n.spanish;
      case 'de':
        return 'Deutsch';
      case 'tr':
        return 'Türkçe';
      default:
        return code;
    }
  }

  String _levelName(
    String level,
    AppLocalizations l10n,
  ) {
    switch (level) {
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
        return level;
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: theme.colorScheme.onSurface,
        elevation: 0,
        actions: [
          IconButton(
            tooltip: theme.brightness == Brightness.dark
                ? l10n.lightMode
                : l10n.darkMode,
            onPressed: () {
              widget.themeController.setThemeMode(
                theme.brightness == Brightness.dark
                    ? ThemeMode.light
                    : ThemeMode.dark,
              );
            },
            icon: Icon(
              theme.brightness == Brightness.dark
                  ? Icons.light_mode_rounded
                  : Icons.dark_mode_rounded,
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(
              24,
              8,
              24,
              30,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                maxWidth: 460,
              ),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      l10n.createYourAccount,
                      style: theme.textTheme.headlineSmall
                          ?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.createAccountSubtitle,
                      style: TextStyle(
                        color:
                            theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 26),
                    Container(
                      padding: const EdgeInsets.all(22),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surface,
                        borderRadius:
                            BorderRadius.circular(28),
                        border: Border.all(
                          color: theme.dividerColor
                              .withOpacity(0.2),
                        ),
                      ),
                      child: Column(
                        children: [
                          TextFormField(
                            controller: _nameController,
                            textInputAction:
                                TextInputAction.next,
                            autofillHints: const [
                              AutofillHints.name,
                            ],
                            decoration: InputDecoration(
                              labelText: l10n.name,
                              prefixIcon: const Icon(
                                Icons.person_outline_rounded,
                              ),
                              border:
                                  const OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null ||
                                  value.trim().length < 2) {
                                return l10n.usernameMinLength;
                              }

                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _emailController,
                            keyboardType:
                                TextInputType.emailAddress,
                            textInputAction:
                                TextInputAction.next,
                            autofillHints: const [
                              AutofillHints.email,
                            ],
                            decoration: InputDecoration(
                              labelText: l10n.email,
                              prefixIcon: const Icon(
                                Icons.email_outlined,
                              ),
                              border:
                                  const OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null ||
                                  !value.contains('@')) {
                                return l10n.enterEmail;
                              }

                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller:
                                _passwordController,
                            obscureText:
                                !_isPasswordVisible,
                            textInputAction:
                                TextInputAction.next,
                            autofillHints: const [
                              AutofillHints.newPassword,
                            ],
                            decoration: InputDecoration(
                              labelText: l10n.password,
                              helperText:
                                  l10n.passwordHelper,
                              prefixIcon: const Icon(
                                Icons.lock_outline_rounded,
                              ),
                              suffixIcon: IconButton(
                                tooltip: _isPasswordVisible
                                    ? l10n
                                        .passwordVisibilityHide
                                    : l10n
                                        .passwordVisibilityShow,
                                onPressed: () {
                                  setState(() {
                                    _isPasswordVisible =
                                        !_isPasswordVisible;
                                  });
                                },
                                icon: Icon(
                                  _isPasswordVisible
                                      ? Icons
                                          .visibility_off_outlined
                                      : Icons
                                          .visibility_outlined,
                                ),
                              ),
                              border:
                                  const OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null ||
                                  value.length < 8) {
                                return l10n.passwordMinLength;
                              }

                              return null;
                            },
                          ),
                          const SizedBox(height: 20),
                          _LanguageSelector(
                            label: l10n.nativeLanguageLabel,
                            icon:
                                Icons.translate_rounded,
                            value: _nativeLanguage,
                            languages: _languages,
                            languageName: (code) =>
                                _languageName(
                              code,
                              l10n,
                            ),
                            onChanged: (value) {
                              if (value != null) {
                                setState(() {
                                  _nativeLanguage = value;
                                });
                              }
                            },
                          ),
                          const SizedBox(height: 16),
                          _LanguageSelector(
                            label:
                                l10n.languageYouWantToLearn,
                            icon:
                                Icons.school_outlined,
                            value: _learningLanguage,
                            languages: _languages,
                            languageName: (code) =>
                                _languageName(
                              code,
                              l10n,
                            ),
                            onChanged: (value) {
                              if (value != null) {
                                setState(() {
                                  _learningLanguage = value;
                                });
                              }
                            },
                          ),
                          const SizedBox(height: 16),
                          _LevelSelector(
                            value: _learningLevel,
                            levelName: (level) =>
                                _levelName(
                              level,
                              l10n,
                            ),
                            onChanged: (value) {
                              if (value != null) {
                                setState(() {
                                  _learningLevel = value;
                                });
                              }
                            },
                          ),
                          if (_errorMessage != null) ...[
                            const SizedBox(height: 18),
                            _RegisterError(
                              message: _errorMessage!,
                            ),
                          ],
                          const SizedBox(height: 24),
                          SizedBox(
                            height: 54,
                            width: double.infinity,
                            child: FilledButton(
                              onPressed:
                                  _isLoading ? null : _register,
                              style:
                                  FilledButton.styleFrom(
                                shape:
                                    RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.circular(
                                    16,
                                  ),
                                ),
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                      width: 22,
                                      height: 22,
                                      child:
                                          CircularProgressIndicator(
                                        strokeWidth: 2.5,
                                        color: Colors.white,
                                      ),
                                    )
                                  : Text(
                                      l10n.createAccountButton,
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LanguageSelector extends StatelessWidget {
  final String label;
  final IconData icon;
  final String value;
  final Map<String, String> languages;
  final String Function(String code) languageName;
  final ValueChanged<String?> onChanged;

  const _LanguageSelector({
    required this.label,
    required this.icon,
    required this.value,
    required this.languages,
    required this.languageName,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
      ),
      items: languages.keys.map(
        (code) {
          return DropdownMenuItem<String>(
            value: code,
            child: Text(
              languageName(code),
            ),
          );
        },
      ).toList(),
      onChanged: onChanged,
    );
  }
}

class _LevelSelector extends StatelessWidget {
  final String value;
  final String Function(String level) levelName;
  final ValueChanged<String?> onChanged;

  const _LevelSelector({
    required this.value,
    required this.levelName,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(
        labelText: l10n.yourLearningLevel,
        prefixIcon: const Icon(
          Icons.bar_chart_rounded,
        ),
        border: const OutlineInputBorder(),
      ),
      items: [
        DropdownMenuItem(
          value: 'A1',
          child: Text(levelName('A1')),
        ),
        DropdownMenuItem(
          value: 'A2',
          child: Text(levelName('A2')),
        ),
        DropdownMenuItem(
          value: 'B1',
          child: Text(levelName('B1')),
        ),
        DropdownMenuItem(
          value: 'B2',
          child: Text(levelName('B2')),
        ),
        DropdownMenuItem(
          value: 'C1',
          child: Text(levelName('C1')),
        ),
        DropdownMenuItem(
          value: 'C2',
          child: Text(levelName('C2')),
        ),
      ],
      onChanged: onChanged,
    );
  }
}

class _RegisterError extends StatelessWidget {
  final String message;

  const _RegisterError({
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Text(
        message,
        style: TextStyle(
          color: theme.colorScheme.onErrorContainer,
        ),
      ),
    );
  }
}