import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TutorExplanationSettings {
  TutorExplanationSettings._();

  static final TutorExplanationSettings instance = TutorExplanationSettings._();

  static const String key = 'tutor_explanation_language_mode';
  static const String nativeMode = 'native';
  static const String learningMode = 'learning';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<String?> getMode() async {
    final value = await _storage.read(key: key);
    if (value == nativeMode || value == learningMode) return value;
    return nativeMode;
  }

  Future<void> setMode(String mode) async {
    if (mode != nativeMode && mode != learningMode) return;
    await _storage.write(key: key, value: mode);
  }

  Future<void> clear() async {
    await _storage.delete(key: key);
  }

  static String title(String languageCode) {
    const values = {
      'ar': 'لغة شرح الأستاذ',
      'de': 'Sprache für Erklärungen des Lehrers',
      'en': 'Teacher explanation language',
      'es': 'Idioma de explicación del profesor',
      'fr': 'Langue d’explication du professeur',
      'id': 'Bahasa penjelasan guru',
      'it': 'Lingua delle spiegazioni dell’insegnante',
      'ja': '先生の説明言語',
      'ko': '선생님의 설명 언어',
      'nl': 'Uitlegtaal van de docent',
      'pl': 'Język wyjaśnień nauczyciela',
      'pt': 'Idioma das explicações do professor',
      'ru': 'Язык объяснений преподавателя',
      'th': 'ภาษาสำหรับคำอธิบายของครู',
      'tr': 'Öğretmenin açıklama dili',
      'uk': 'Мова пояснень викладача',
      'vi': 'Ngôn ngữ giải thích của giáo viên',
      'zh': '老师讲解语言',
    };
    return values[languageCode] ?? values['en']!;
  }

  static String question(String languageCode) {
    const values = {
      'ar': 'بأي لغة تريد من الأستاذ أن يشرح لك ويصحح أخطاءك؟',
      'de': 'In welcher Sprache soll der Lehrer dir Erklärungen und Korrekturen geben?',
      'en': 'Which language should the teacher use for explanations and corrections?',
      'es': '¿Qué idioma debe usar el profesor para las explicaciones y correcciones?',
      'fr': 'Dans quelle langue le professeur doit-il expliquer et corriger vos erreurs ?',
      'id': 'Bahasa apa yang harus digunakan guru untuk penjelasan dan koreksi?',
      'it': 'Quale lingua deve usare l’insegnante per spiegazioni e correzioni?',
      'ja': '説明や訂正をどの言語で行うか選んでください。',
      'ko': '선생님이 설명과 교정을 어떤 언어로 하길 원하시나요?',
      'nl': 'Welke taal moet de docent gebruiken voor uitleg en correcties?',
      'pl': 'W jakim języku nauczyciel ma udzielać wyjaśnień i poprawek?',
      'pt': 'Que idioma o professor deve usar para explicações e correções?',
      'ru': 'На каком языке преподаватель должен давать объяснения и исправления?',
      'th': 'คุณต้องการให้ครูอธิบายและแก้ไขด้วยภาษาใด?',
      'tr': 'Öğretmenin açıklamalar ve düzeltmeler için hangi dili kullanmasını istersiniz?',
      'uk': 'Якою мовою викладач має давати пояснення та виправлення?',
      'vi': 'Giáo viên nên dùng ngôn ngữ nào để giải thích và sửa lỗi?',
      'zh': '请选择老师用于讲解和纠正的语言。',
    };
    return values[languageCode] ?? values['en']!;
  }

  static String nativeLabel(String languageCode) {
    const values = {
      'ar': 'لغتي الأم',
      'de': 'Meine Muttersprache',
      'en': 'My native language',
      'es': 'Mi lengua materna',
      'fr': 'Ma langue maternelle',
      'id': 'Bahasa ibu saya',
      'it': 'La mia lingua madre',
      'ja': '母語',
      'ko': '모국어',
      'nl': 'Mijn moedertaal',
      'pl': 'Mój język ojczysty',
      'pt': 'Minha língua materna',
      'ru': 'Мой родной язык',
      'th': 'ภาษาของฉัน',
      'tr': 'Ana dilim',
      'uk': 'Моя рідна мова',
      'vi': 'Ngôn ngữ mẹ đẻ của tôi',
      'zh': '我的母语',
    };
    return values[languageCode] ?? values['en']!;
  }

  static String learningLabel(String languageCode) {
    const values = {
      'ar': 'لغة التعلم',
      'de': 'Meine Lernsprache',
      'en': 'My learning language',
      'es': 'Mi idioma de aprendizaje',
      'fr': 'Ma langue d’apprentissage',
      'id': 'Bahasa yang saya pelajari',
      'it': 'La mia lingua di apprendimento',
      'ja': '学習言語',
      'ko': '학습 언어',
      'nl': 'Mijn leertaal',
      'pl': 'Mój język nauki',
      'pt': 'Meu idioma de aprendizagem',
      'ru': 'Язык, который я изучаю',
      'th': 'ภาษาที่ฉันเรียน',
      'tr': 'Öğrendiğim dil',
      'uk': 'Мова, яку я вивчаю',
      'vi': 'Ngôn ngữ tôi đang học',
      'zh': '我的学习语言',
    };
    return values[languageCode] ?? values['en']!;
  }
}

final tutorExplanationSettings = TutorExplanationSettings.instance;
