class LessonVocabularyItem {
  final String word;
  final String translation;
  final String? partOfSpeech;
  final String? pronunciation;

  const LessonVocabularyItem({
    required this.word,
    required this.translation,
    this.partOfSpeech,
    this.pronunciation,
  });

  factory LessonVocabularyItem.fromJson(Map<String, dynamic> json) {
    return LessonVocabularyItem(
      word: (json['word'] ?? '').toString(),
      translation: (json['translation'] ?? '').toString(),
      partOfSpeech: json['part_of_speech']?.toString(),
      pronunciation: json['pronunciation']?.toString(),
    );
  }
}

class LessonExample {
  final String targetText;
  final String translation;

  const LessonExample({
    required this.targetText,
    required this.translation,
  });

  factory LessonExample.fromJson(Map<String, dynamic> json) {
    return LessonExample(
      targetText: (json['target_text'] ?? '').toString(),
      translation: (json['translation'] ?? '').toString(),
    );
  }
}

class LessonExercise {
  final String type;
  final String question;
  final List<String> options;
  final String answer;
  final String? explanation;

  const LessonExercise({
    required this.type,
    required this.question,
    required this.options,
    required this.answer,
    this.explanation,
  });

  factory LessonExercise.fromJson(Map<String, dynamic> json) {
    return LessonExercise(
      type: (json['type'] ?? 'multiple_choice').toString(),
      question: (json['question'] ?? '').toString(),
      options: (json['options'] is List)
          ? List<String>.from(
              (json['options'] as List).map((item) => item.toString()),
            )
          : const [],
      answer: (json['answer'] ?? '').toString(),
      explanation: json['explanation']?.toString(),
    );
  }
}

class LessonContentModel {
  final int id;
  final int lessonId;
  final String status;
  final String instructionLanguage;
  final String? generatorModel;
  final int version;
  final String title;
  final String objective;
  final String introduction;
  final String explanation;
  final List<LessonVocabularyItem> vocabulary;
  final List<LessonExample> examples;
  final List<LessonExample> dialogue;
  final List<LessonExercise> exercises;

  const LessonContentModel({
    required this.id,
    required this.lessonId,
    required this.status,
    required this.instructionLanguage,
    required this.generatorModel,
    required this.version,
    required this.title,
    required this.objective,
    required this.introduction,
    required this.explanation,
    required this.vocabulary,
    required this.examples,
    required this.dialogue,
    required this.exercises,
  });

  factory LessonContentModel.fromJson(Map<String, dynamic> json) {
    final rawContent = json['content'];
    final content = rawContent is Map
        ? Map<String, dynamic>.from(rawContent)
        : <String, dynamic>{};

    return LessonContentModel(
      id: int.tryParse('${json['id']}') ?? 0,
      lessonId: int.tryParse('${json['lesson_id']}') ?? 0,
      status: (json['status'] ?? '').toString(),
      instructionLanguage: (json['instruction_language'] ?? 'ar').toString(),
      generatorModel: json['generator_model']?.toString(),
      version: int.tryParse('${json['version']}') ?? 1,
      title: (content['title'] ?? '').toString(),
      objective: (content['objective'] ?? '').toString(),
      introduction: (content['introduction'] ?? '').toString(),
      explanation: (content['explanation'] ?? '').toString(),
      vocabulary: _listOfMaps(content['vocabulary'])
          .map(LessonVocabularyItem.fromJson)
          .toList(),
      examples: _listOfMaps(content['examples'])
          .map(LessonExample.fromJson)
          .toList(),
      dialogue: _listOfMaps(content['dialogue'])
          .map(LessonExample.fromJson)
          .toList(),
      exercises: _listOfMaps(content['exercises'])
          .map(LessonExercise.fromJson)
          .toList(),
    );
  }

  static List<Map<String, dynamic>> _listOfMaps(dynamic value) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
}
