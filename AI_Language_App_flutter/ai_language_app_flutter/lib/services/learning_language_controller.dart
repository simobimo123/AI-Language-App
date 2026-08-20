import 'package:flutter/foundation.dart';

class LearningLanguageController extends ChangeNotifier {
  LearningLanguageController._();

  static final LearningLanguageController instance =
      LearningLanguageController._();

  String? _currentLanguage;

  String? get currentLanguage => _currentLanguage;

  void setLanguage(String language) {
    if (_currentLanguage == language) {
      return;
    }

    _currentLanguage = language;
    notifyListeners();
  }

  void clear() {
    if (_currentLanguage == null) {
      return;
    }

    _currentLanguage = null;
    notifyListeners();
  }
}