import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TutorExplanationSettings {
  TutorExplanationSettings._();

  static final TutorExplanationSettings instance =
      TutorExplanationSettings._();

  static const String key = 'tutor_explanation_language_mode';
  static const String nativeMode = 'native';
  static const String learningMode = 'learning';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<String?> getMode() async {
    final value = await _storage.read(key: key);
    if (value == nativeMode || value == learningMode) return value;
    return null;
  }

  Future<void> setMode(String mode) async {
    if (mode != nativeMode && mode != learningMode) return;
    await _storage.write(key: key, value: mode);
  }

  Future<void> clear() async {
    await _storage.delete(key: key);
  }
}

final tutorExplanationSettings = TutorExplanationSettings.instance;
