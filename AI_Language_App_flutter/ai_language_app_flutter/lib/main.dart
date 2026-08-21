import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'l10n/app_localizations.dart';
import 'screens/splash_page.dart';
import 'services/language_controller.dart';
import 'services/theme_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final themeController = ThemeController();
  final languageController = LanguageController();

  await themeController.load();
  await languageController.load();

  runApp(
    MyApp(
      themeController: themeController,
      languageController: languageController,
    ),
  );
}

class MyApp extends StatelessWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const MyApp({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([
        themeController,
        languageController,
      ]),
      builder: (context, _) {
        final locale = languageController.locale;

        return MaterialApp(
          debugShowCheckedModeBanner: false,

          title: 'AI Language Tutor',

          locale: locale,

          supportedLocales: const [
            Locale('ar'),
            Locale('en'),
            Locale('fr'),
            Locale('es'),
            Locale('zh'),
            Locale('ja'),
            Locale('ko'),
          ],

          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],

          themeMode: themeController.themeMode,

          theme: _buildTheme(Brightness.light),
          darkTheme: _buildTheme(Brightness.dark),

          builder: (context, child) {
            return Directionality(
              textDirection: locale.languageCode == 'ar'
                  ? TextDirection.rtl
                  : TextDirection.ltr,
              child: child!,
            );
          },

          home: SplashPage(
            themeController: themeController,
            languageController: languageController,
          ),
        );
      },
    );
  }

  ThemeData _buildTheme(Brightness brightness) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF635BDB),
      brightness: brightness,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,

      scaffoldBackgroundColor: brightness == Brightness.dark
          ? const Color(0xFF121217)
          : const Color(0xFFF7F7FB),

      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: colorScheme.onSurface,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,

        fillColor: brightness == Brightness.dark
            ? const Color(0xFF202027)
            : Colors.white,

        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 18,
        ),

        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),

        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colorScheme.outlineVariant,
          ),
        ),

        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colorScheme.primary,
            width: 2,
          ),
        ),
      ),
    );
  }
}