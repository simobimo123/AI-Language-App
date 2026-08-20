import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../services/theme_controller.dart';

class RegisterPage extends StatefulWidget {
  final ThemeController themeController;

  const RegisterPage({
    super.key,
    required this.themeController,
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

  String _nativeLanguage = 'ar';
  String _learningLanguage = 'en';
  String _learningLevel = 'A1';

  bool _isLoading = false;
  bool _isPasswordVisible = false;
  String? _errorMessage;

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;

    if (_nativeLanguage == _learningLanguage) {
      setState(() {
        _errorMessage = 'اختر لغتين مختلفتين للبدء.';
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
        const SnackBar(
          content: Text('تم إنشاء الحساب. يمكنك تسجيل الدخول الآن.'),
        ),
      );

      Navigator.pop(context);
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _errorMessage = 'تعذّر إنشاء الحساب. قد يكون البريد مستخدمًا بالفعل.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
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

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,

      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: theme.colorScheme.onSurface,
        elevation: 0,

        actions: [
          IconButton(
            tooltip: theme.brightness == Brightness.dark
                ? 'الوضع الفاتح'
                : 'الوضع الداكن',
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
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 30),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'أنشئ حسابك',
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),

                    const SizedBox(height: 8),

                    Text(
                      'اختر لغاتك وابدأ تجربة تعلّم مصممة لك.',
                      style: TextStyle(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),

                    const SizedBox(height: 26),

                    Container(
                      padding: const EdgeInsets.all(22),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surface,
                        borderRadius: BorderRadius.circular(28),
                        border: Border.all(
                          color: theme.dividerColor.withOpacity(0.2),
                        ),
                      ),
                      child: Column(
                        children: [
                          TextFormField(
                            controller: _nameController,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.name],
                            decoration: const InputDecoration(
                              labelText: 'الاسم',
                              prefixIcon: Icon(Icons.person_outline_rounded),
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.trim().length < 2) {
                                return 'أدخل اسمًا من حرفين على الأقل.';
                              }

                              return null;
                            },
                          ),

                          const SizedBox(height: 16),

                          TextFormField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.email],
                            decoration: const InputDecoration(
                              labelText: 'البريد الإلكتروني',
                              prefixIcon: Icon(Icons.email_outlined),
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || !value.contains('@')) {
                                return 'أدخل بريدًا إلكترونيًا صحيحًا.';
                              }

                              return null;
                            },
                          ),

                          const SizedBox(height: 16),

                          TextFormField(
                            controller: _passwordController,
                            obscureText: !_isPasswordVisible,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.newPassword],
                            decoration: InputDecoration(
                              labelText: 'كلمة المرور',
                              helperText: '8 أحرف على الأقل',
                              prefixIcon: const Icon(
                                Icons.lock_outline_rounded,
                              ),
                              suffixIcon: IconButton(
                                tooltip: _isPasswordVisible
                                    ? 'إخفاء كلمة المرور'
                                    : 'إظهار كلمة المرور',
                                onPressed: () {
                                  setState(() {
                                    _isPasswordVisible =
                                        !_isPasswordVisible;
                                  });
                                },
                                icon: Icon(
                                  _isPasswordVisible
                                      ? Icons.visibility_off_outlined
                                      : Icons.visibility_outlined,
                                ),
                              ),
                              border: const OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.length < 8) {
                                return 'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل.';
                              }

                              return null;
                            },
                          ),

                          const SizedBox(height: 20),

                          _LanguageSelector(
                            label: 'لغتك الأم',
                            icon: Icons.translate_rounded,
                            value: _nativeLanguage,
                            languages: _languages,
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
                            label: 'اللغة التي تريد تعلّمها',
                            icon: Icons.school_outlined,
                            value: _learningLanguage,
                            languages: _languages,
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
                            levels: _levels,
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
                              onPressed: _isLoading ? null : _register,
                              style: FilledButton.styleFrom(
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                      width: 22,
                                      height: 22,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.5,
                                        color: Colors.white,
                                      ),
                                    )
                                  : const Text('إنشاء الحساب'),
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
  final ValueChanged<String?> onChanged;

  const _LanguageSelector({
    required this.label,
    required this.icon,
    required this.value,
    required this.languages,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: value,
      isExpanded: true,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
      ),
      items: languages.entries
          .map(
            (entry) => DropdownMenuItem(
              value: entry.key,
              child: Text(entry.value),
            ),
          )
          .toList(),
      onChanged: onChanged,
    );
  }
}

class _LevelSelector extends StatelessWidget {
  final String value;
  final Map<String, String> levels;
  final ValueChanged<String?> onChanged;

  const _LevelSelector({
    required this.value,
    required this.levels,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: value,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'مستواك في اللغة',
        prefixIcon: Icon(Icons.bar_chart_rounded),
        border: OutlineInputBorder(),
      ),
      items: levels.entries
          .map(
            (entry) => DropdownMenuItem(
              value: entry.key,
              child: Text(entry.value),
            ),
          )
          .toList(),
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