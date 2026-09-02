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
  final String id;
  final int order;
  final String type;
  final String question;
  final List<String> options;
  final String answer;
  final String? explanation;

  const LessonExercise({
    required this.id,
    required this.order,
    required this.type,
    required this.question,
    required this.options,
    required this.answer,
    this.explanation,
  });

  factory LessonExercise.fromJson(Map<String, dynamic> json) {
    return LessonExercise(
      id: (json['id'] ?? '').toString(),
      order: int.tryParse('${json['order']}') ?? 0,
      type: (json['type'] ?? 'multiple_choice').toString(),
      question: (json['question'] ?? '').toString(),
      options: (json['options'] is List)
          ? List<String>.from(
              (json['options'] as List).map(
                (item) => item.toString(),
              ),
            )
          : const [],
      answer: (json['answer'] ?? '').toString(),
      explanation: json['explanation']?.toString(),
    );
  }
}

class LessonSection {
  final String id;
  final int order;
  final String type;
  final String title;
  final String? targetText;
  final String? pronunciation;
  final String? translation;
  final String? explanation;
  final List<String> examples;

  const LessonSection({
    required this.id,
    required this.order,
    required this.type,
    required this.title,
    this.targetText,
    this.pronunciation,
    this.translation,
    this.explanation,
    required this.examples,
  });

  factory LessonSection.fromJson(Map<String, dynamic> json) {
    return LessonSection(
      id: (json['id'] ?? '').toString(),
      order: int.tryParse('${json['order']}') ?? 0,
      type: (json['type'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      targetText: json['target_text']?.toString(),
      pronunciation: json['pronunciation']?.toString(),
      translation: json['translation']?.toString(),
      explanation: json['explanation']?.toString(),
      examples: json['examples'] is List
          ? List<String>.from(
              (json['examples'] as List).map(
                (item) => item.toString(),
              ),
            )
          : const [],
    );
  }
}

class LessonReviewItem {
  final String id;
  final String question;
  final List<String> options;
  final String answer;
  final String? explanation;

  const LessonReviewItem({
    required this.id,
    required this.question,
    required this.options,
    required this.answer,
    this.explanation,
  });

  factory LessonReviewItem.fromJson(Map<String, dynamic> json) {
    return LessonReviewItem(
      id: (json['id'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      options: json['options'] is List
          ? List<String>.from(
              (json['options'] as List).map(
                (item) => item.toString(),
              ),
            )
          : const [],
      answer: (json['answer'] ?? '').toString(),
      explanation: json['explanation']?.toString(),
    );
  }
}

class LessonEndTestQuestion {
  final String id;
  final String question;
  final List<String> options;
  final String answer;
  final String? explanation;

  const LessonEndTestQuestion({
    required this.id,
    required this.question,
    required this.options,
    required this.answer,
    this.explanation,
  });

  factory LessonEndTestQuestion.fromJson(
    Map<String, dynamic> json,
  ) {
    return LessonEndTestQuestion(
      id: (json['id'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      options: json['options'] is List
          ? List<String>.from(
              (json['options'] as List).map(
                (item) => item.toString(),
              ),
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

  final List<LessonSection> sections;
  final List<LessonReviewItem> review;
  final List<LessonEndTestQuestion> endTest;

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
    required this.sections,
    required this.review,
    required this.endTest,
  });

  factory LessonContentModel.fromJson(
    Map<String, dynamic> json,
  ) {
    final rawContent = json['content'];

    final content = rawContent is Map
        ? Map<String, dynamic>.from(rawContent)
        : <String, dynamic>{};

    return LessonContentModel(
      id: int.tryParse('${json['id']}') ?? 0,
      lessonId: int.tryParse('${json['lesson_id']}') ?? 0,
      status: (json['status'] ?? '').toString(),
      instructionLanguage:
          (json['instruction_language'] ?? 'ar').toString(),
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

      sections: _listOfMaps(content['sections'])
          .map(LessonSection.fromJson)
          .toList(),

      review: _listOfMaps(content['review'])
          .map(LessonReviewItem.fromJson)
          .toList(),

      endTest: _listOfMaps(content['end_test'])
          .map(LessonEndTestQuestion.fromJson)
          .toList(),
    );
  }

  static List<Map<String, dynamic>> _listOfMaps(
    dynamic value,
  ) {
    if (value is! List) return const [];

    return value
        .whereType<Map>()
        .map(
          (item) => Map<String, dynamic>.from(item),
        )
        .toList();
  }
}
