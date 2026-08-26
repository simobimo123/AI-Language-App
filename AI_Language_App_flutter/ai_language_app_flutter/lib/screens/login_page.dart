import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';
import '../services/google_auth_service.dart';
import '../core/language/language_controller.dart';
import '../core/storage/storage_service.dart';
import '../core/theme/theme_controller.dart';
import 'register_page.dart';
import 'splash_page.dart';

class LoginPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const LoginPage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();

  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  final _apiService = ApiService();
  final _storageService = StorageService();
  final _googleAuthService = GoogleAuthService();

  bool _isLoading = false;
  bool _isGoogleLoading = false;
  bool _isPasswordVisible = false;
  String? _errorMessage;

  Future<void> _login() async {
    final l10n = AppLocalizations.of(context)!;

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final result = await _apiService.login(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      await _storageService.saveToken(result['access_token'] as String);

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => SplashPage(
            themeController: widget.themeController,
            languageController: widget.languageController,
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _errorMessage = l10n.loginError;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loginWithGoogle() async {
    final l10n = AppLocalizations.of(context)!;

    setState(() {
      _isGoogleLoading = true;
      _errorMessage = null;
    });

    try {
      final idToken = await _googleAuthService.signInAndGetIdToken();

      if (idToken == null || idToken.isEmpty) {
        throw Exception('Google ID token is missing');
      }

      final result = await _apiService.loginWithGoogle(idToken: idToken);

      await _storageService.saveToken(result['access_token'] as String);

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => SplashPage(
            themeController: widget.themeController,
            languageController: widget.languageController,
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _errorMessage = l10n.loginError;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isGoogleLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context)!;

    final isDark = theme.brightness == Brightness.dark;

    final isAnyLoading = _isLoading || _isGoogleLoading;

    return Scaffold(
      backgroundColor: colorScheme.surface,
      body: Stack(
        children: [
          Positioned(
            top: -120,
            left: -100,
            child: _BackgroundCircle(
              size: 280,
              color: colorScheme.primary.withValues(alpha: isDark ? 0.12 : 0.08),
            ),
          ),
          Positioned(
            top: 120,
            right: -140,
            child: _BackgroundCircle(
              size: 300,
              color: colorScheme.secondary.withValues(alpha: isDark ? 0.10 : 0.07),
            ),
          ),
          Positioned(
            bottom: -150,
            left: -80,
            child: _BackgroundCircle(
              size: 300,
              color: colorScheme.primary.withValues(alpha: isDark ? 0.08 : 0.05),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 12, 0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      DecoratedBox(
                        decoration: BoxDecoration(
                          color: colorScheme.surfaceContainerHighest
                              .withValues(alpha: 0.7),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: IconButton(
                          tooltip: isDark ? l10n.lightMode : l10n.darkMode,
                          onPressed: isAnyLoading
                              ? null
                              : () {
                                  widget.themeController.setThemeMode(
                                    isDark ? ThemeMode.light : ThemeMode.dark,
                                  );
                                },
                          icon: AnimatedSwitcher(
                            duration: const Duration(milliseconds: 250),
                            child: Icon(
                              isDark
                                  ? Icons.light_mode_rounded
                                  : Icons.dark_mode_rounded,
                              key: ValueKey(isDark),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      keyboardDismissBehavior:
                          ScrollViewKeyboardDismissBehavior.onDrag,
                      padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 440),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              _AppLogo(
                                primaryColor: colorScheme.primary,
                                secondaryColor: colorScheme.secondary,
                              ),
                              const SizedBox(height: 28),
                              Text(
                                l10n.welcomeBackTitle,
                                textAlign: TextAlign.center,
                                style: theme.textTheme.headlineMedium?.copyWith(
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: -0.6,
                                ),
                              ),
                              const SizedBox(height: 10),
                              Text(
                                l10n.loginSubtitle,
                                textAlign: TextAlign.center,
                                style: theme.textTheme.bodyLarge?.copyWith(
                                  color: colorScheme.onSurfaceVariant,
                                  height: 1.5,
                                ),
                              ),
                              const SizedBox(height: 30),
                              Container(
                                padding: const EdgeInsets.fromLTRB(
                                  22,
                                  24,
                                  22,
                                  22,
                                ),
                                decoration: BoxDecoration(
                                  color: colorScheme.surfaceContainerLow,
                                  borderRadius: BorderRadius.circular(28),
                                  border: Border.all(
                                    color: colorScheme.outlineVariant
                                        .withValues(alpha: 0.45),
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(alpha: 
                                        isDark ? 0.18 : 0.06,
                                      ),
                                      blurRadius: 30,
                                      offset: const Offset(0, 14),
                                    ),
                                  ],
                                ),
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    Text(
                                      l10n.login,
                                      style: theme.textTheme.titleLarge
                                          ?.copyWith(
                                            fontWeight: FontWeight.w800,
                                          ),
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      l10n.loginSubtitle,
                                      style: theme.textTheme.bodyMedium
                                          ?.copyWith(
                                            color: colorScheme.onSurfaceVariant,
                                          ),
                                    ),
                                    const SizedBox(height: 22),
                                    TextFormField(
                                      controller: _emailController,
                                      enabled: !isAnyLoading,
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      autofillHints: const [
                                        AutofillHints.email,
                                      ],
                                      decoration: InputDecoration(
                                        labelText: l10n.email,
                                        prefixIcon: const Icon(
                                          Icons.email_outlined,
                                        ),
                                        filled: true,
                                        fillColor: colorScheme
                                            .surfaceContainerHighest
                                            .withValues(alpha: 0.45),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                          borderSide: BorderSide.none,
                                        ),
                                        enabledBorder: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                          borderSide: BorderSide(
                                            color: colorScheme.outlineVariant
                                                .withValues(alpha: 0.35),
                                          ),
                                        ),
                                        focusedBorder: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                          borderSide: BorderSide(
                                            color: colorScheme.primary,
                                            width: 1.5,
                                          ),
                                        ),
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
                                      controller: _passwordController,
                                      enabled: !isAnyLoading,
                                      obscureText: !_isPasswordVisible,
                                      textInputAction: TextInputAction.done,
                                      autofillHints: const [
                                        AutofillHints.password,
                                      ],
                                      onFieldSubmitted: (_) => _login(),
                                      decoration: InputDecoration(
                                        labelText: l10n.password,
                                        prefixIcon: const Icon(
                                          Icons.lock_outline_rounded,
                                        ),
                                        suffixIcon: IconButton(
                                          tooltip: _isPasswordVisible
                                              ? l10n.passwordVisibilityHide
                                              : l10n.passwordVisibilityShow,
                                          onPressed: isAnyLoading
                                              ? null
                                              : () {
                                                  setState(() {
                                                    _isPasswordVisible =
                                                        !_isPasswordVisible;
                                                  });
                                                },
                                          icon: AnimatedSwitcher(
                                            duration: const Duration(
                                              milliseconds: 200,
                                            ),
                                            child: Icon(
                                              _isPasswordVisible
                                                  ? Icons
                                                        .visibility_off_outlined
                                                  : Icons.visibility_outlined,
                                              key: ValueKey(_isPasswordVisible),
                                            ),
                                          ),
                                        ),
                                        filled: true,
                                        fillColor: colorScheme
                                            .surfaceContainerHighest
                                            .withValues(alpha: 0.45),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                          borderSide: BorderSide.none,
                                        ),
                                        enabledBorder: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                          borderSide: BorderSide(
                                            color: colorScheme.outlineVariant
                                                .withValues(alpha: 0.35),
                                          ),
                                        ),
                                        focusedBorder: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                          borderSide: BorderSide(
                                            color: colorScheme.primary,
                                            width: 1.5,
                                          ),
                                        ),
                                      ),
                                      validator: (value) {
                                        if (value == null || value.isEmpty) {
                                          return l10n.enterPassword;
                                        }

                                        return null;
                                      },
                                    ),
                                    if (_errorMessage != null) ...[
                                      const SizedBox(height: 16),
                                      _ErrorMessage(message: _errorMessage!),
                                    ],
                                    const SizedBox(height: 22),
                                    SizedBox(
                                      height: 56,
                                      child: FilledButton(
                                        onPressed: isAnyLoading ? null : _login,
                                        style: FilledButton.styleFrom(
                                          elevation: 0,
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(
                                              16,
                                            ),
                                          ),
                                        ),
                                        child: AnimatedSwitcher(
                                          duration: const Duration(
                                            milliseconds: 200,
                                          ),
                                          child: _isLoading
                                              ? const SizedBox(
                                                  key: ValueKey(
                                                    'login-loading',
                                                  ),
                                                  width: 23,
                                                  height: 23,
                                                  child:
                                                      CircularProgressIndicator(
                                                        strokeWidth: 2.5,
                                                        color: Colors.white,
                                                      ),
                                                )
                                              : Row(
                                                  key: const ValueKey(
                                                    'login-button',
                                                  ),
                                                  mainAxisAlignment:
                                                      MainAxisAlignment.center,
                                                  children: [
                                                    Text(
                                                      l10n.loginButton,
                                                      style: const TextStyle(
                                                        fontWeight:
                                                            FontWeight.w700,
                                                        fontSize: 16,
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    const Icon(
                                                      Icons
                                                          .arrow_forward_rounded,
                                                      size: 20,
                                                    ),
                                                  ],
                                                ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(height: 20),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Divider(
                                            color: colorScheme.outlineVariant
                                                .withValues(alpha: 0.5),
                                          ),
                                        ),
                                        Padding(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 12,
                                          ),
                                          child: Text(
                                            'OR',
                                            style: theme.textTheme.labelMedium
                                                ?.copyWith(
                                                  color: colorScheme
                                                      .onSurfaceVariant,
                                                  fontWeight: FontWeight.w600,
                                                ),
                                          ),
                                        ),
                                        Expanded(
                                          child: Divider(
                                            color: colorScheme.outlineVariant
                                                .withValues(alpha: 0.5),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 20),
                                    SizedBox(
                                      height: 56,
                                      child: OutlinedButton(
                                        onPressed: isAnyLoading
                                            ? null
                                            : _loginWithGoogle,
                                        style: OutlinedButton.styleFrom(
                                          backgroundColor: colorScheme.surface,
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(
                                              16,
                                            ),
                                          ),
                                          side: BorderSide(
                                            color: colorScheme.outlineVariant,
                                          ),
                                        ),
                                        child: _isGoogleLoading
                                            ? const SizedBox(
                                                width: 23,
                                                height: 23,
                                                child:
                                                    CircularProgressIndicator(
                                                      strokeWidth: 2.5,
                                                    ),
                                              )
                                            : Row(
                                                mainAxisAlignment:
                                                    MainAxisAlignment.center,
                                                children: [
                                                  const _GoogleIcon(),
                                                  const SizedBox(width: 12),
                                                  const Text(
                                                    'Continue with Google',
                                                    style: TextStyle(
                                                      fontWeight:
                                                          FontWeight.w700,
                                                      fontSize: 15,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 22),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 6,
                                ),
                                decoration: BoxDecoration(
                                  color: colorScheme.surfaceContainerHighest
                                      .withValues(alpha: 0.35),
                                  borderRadius: BorderRadius.circular(18),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      l10n.noAccount,
                                      style: TextStyle(
                                        color: colorScheme.onSurfaceVariant,
                                      ),
                                    ),
                                    TextButton(
                                      onPressed: isAnyLoading
                                          ? null
                                          : () {
                                              Navigator.push(
                                                context,
                                                MaterialPageRoute(
                                                  builder: (_) => RegisterPage(
                                                    themeController:
                                                        widget.themeController,
                                                    languageController: widget
                                                        .languageController,
                                                  ),
                                                ),
                                              );
                                            },
                                      style: TextButton.styleFrom(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 8,
                                        ),
                                      ),
                                      child: Text(
                                        l10n.createAccount,
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w700,
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
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================
// Google icon
// =============================================================

class _GoogleIcon extends StatelessWidget {
  const _GoogleIcon();

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: 22,
      height: 22,
      child: Center(
        child: Text(
          'G',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        ),
      ),
    );
  }
}

// =============================================================
// App logo
// =============================================================

class _AppLogo extends StatelessWidget {
  final Color primaryColor;
  final Color secondaryColor;

  const _AppLogo({required this.primaryColor, required this.secondaryColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 86,
      height: 86,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [primaryColor, secondaryColor],
        ),
        borderRadius: BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            color: primaryColor.withValues(alpha: 0.25),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: const Icon(
        Icons.auto_awesome_rounded,
        color: Colors.white,
        size: 40,
      ),
    );
  }
}

// =============================================================
// Background circle
// =============================================================

class _BackgroundCircle extends StatelessWidget {
  final double size;
  final Color color;

  const _BackgroundCircle({required this.size, required this.color});

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
    );
  }
}

// =============================================================
// Error message
// =============================================================

class _ErrorMessage extends StatelessWidget {
  final String message;

  const _ErrorMessage({required this.message});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: colorScheme.error.withValues(alpha: 0.15)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.error_outline_rounded,
            color: colorScheme.onErrorContainer,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: colorScheme.onErrorContainer,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
