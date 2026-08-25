import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class LanguageController extends ChangeNotifier {
  static const String _languageKey = 'app_language';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  static const Set<String> _supportedLanguageCodes = {
    'ar',
    'en',
    'fr',
    'es',
    'zh',
    'ja',
    'ko',
  };

  Locale _locale = const Locale('ar');

  Locale get locale => _locale;

  bool get isArabic => _locale.languageCode == 'ar';

  Future<void> load() async {
    final savedLanguage = await _storage.read(key: _languageKey);

    if (savedLanguage != null &&
        savedLanguage.isNotEmpty &&
        _supportedLanguageCodes.contains(savedLanguage)) {
      // المستخدم سبق له اختيار لغة داخل التطبيق.
      _locale = Locale(savedLanguage);
    } else {
      // أول تشغيل: استخدم لغة الجهاز إذا كانت مدعومة.
      final deviceLocale = WidgetsBinding.instance.platformDispatcher.locale;

      final deviceLanguageCode = deviceLocale.languageCode.toLowerCase();

      if (_supportedLanguageCodes.contains(deviceLanguageCode)) {
        _locale = Locale(deviceLanguageCode);
      } else {
        // لغة الجهاز غير مدعومة.
        _locale = const Locale('ar');
      }
    }

    notifyListeners();
  }

  Future<void> setLanguage(String languageCode) async {
    final normalizedCode = languageCode.toLowerCase();

    if (!_supportedLanguageCodes.contains(normalizedCode)) {
      return;
    }

    if (_locale.languageCode == normalizedCode) {
      return;
    }

    _locale = Locale(normalizedCode);

    await _storage.write(key: _languageKey, value: normalizedCode);

    notifyListeners();
  }

  Future<void> resetToDeviceLanguage() async {
    await _storage.delete(key: _languageKey);

    final deviceLocale = WidgetsBinding.instance.platformDispatcher.locale;

    final deviceLanguageCode = deviceLocale.languageCode.toLowerCase();

    if (_supportedLanguageCodes.contains(deviceLanguageCode)) {
      _locale = Locale(deviceLanguageCode);
    } else {
      _locale = const Locale('ar');
    }

    notifyListeners();
  }
}
