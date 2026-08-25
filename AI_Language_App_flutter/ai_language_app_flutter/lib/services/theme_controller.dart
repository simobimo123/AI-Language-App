import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ThemeController extends ChangeNotifier {
  static const String _themeKey = 'theme_mode';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ThemeMode _themeMode = ThemeMode.system;

  ThemeMode get themeMode => _themeMode;

  Future<void> load() async {
    final savedMode = await _storage.read(key: _themeKey);

    switch (savedMode) {
      case 'light':
        _themeMode = ThemeMode.light;
        break;

      case 'dark':
        _themeMode = ThemeMode.dark;
        break;

      default:
        _themeMode = ThemeMode.system;
    }

    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;

    notifyListeners();

    await _storage.write(key: _themeKey, value: mode.name);
  }

  Future<void> resetToSystem() async {
    await setThemeMode(ThemeMode.system);
  }

  Future<void> setLightMode() async {
    await setThemeMode(ThemeMode.light);
  }

  Future<void> setDarkMode() async {
    await setThemeMode(ThemeMode.dark);
  }
}
