import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class LanguageController extends ChangeNotifier {
  static const String _languageKey = 'app_language';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Locale _locale = const Locale('ar');

  Locale get locale => _locale;

  bool get isArabic => _locale.languageCode == 'ar';

  Future<void> load() async {
    final savedLanguage = await _storage.read(key: _languageKey);

    if (savedLanguage == null || savedLanguage.isEmpty) {
      _locale = const Locale('ar');
    } else {
      _locale = Locale(savedLanguage);
    }

    notifyListeners();
  }

  Future<void> setLanguage(String languageCode) async {
    if (_locale.languageCode == languageCode) {
      return;
    }

    _locale = Locale(languageCode);

    await _storage.write(key: _languageKey, value: languageCode);

    notifyListeners();
  }
}
