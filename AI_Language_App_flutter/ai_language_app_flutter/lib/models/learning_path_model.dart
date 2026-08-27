import 'learning_lesson_model.dart';

class LearningPathModel {
  final String language;
  final String level;
  final String nextLevel;
  final double progress;
  final int completedLessons;
  final int totalLessons;
  final List<LearningLessonModel> lessons;

  const LearningPathModel({
    required this.language,
    required this.level,
    required this.nextLevel,
    required this.progress,
    required this.completedLessons,
    required this.totalLessons,
    required this.lessons,
  });

  factory LearningPathModel.fromJson(
    Map<String, dynamic> json,
  ) {
    final rawLessons = json['lessons'];

    final lessons = rawLessons is List
        ? rawLessons
            .whereType<Map>()
            .map(
              (lesson) => LearningLessonModel.fromJson(
                Map<String, dynamic>.from(lesson),
              ),
            )
            .toList()
        : <LearningLessonModel>[];

    int completedLessons = _parseInt(
      json['completed_lessons'],
    );

    int totalLessons = _parseInt(
      json['total_lessons'],
    );

    double progress = _parseProgress(
      json['progress'],
    );

    final nonTestLessons = lessons
        .where((lesson) => !lesson.isTest)
        .toList();

    if (totalLessons == 0) {
      totalLessons = nonTestLessons.length;
    }

    if (completedLessons == 0) {
      completedLessons = nonTestLessons
          .where((lesson) => lesson.isCompleted)
          .length;
    }

    if (progress == 0 && totalLessons > 0) {
      progress = (completedLessons / totalLessons) * 100;
    }

    return LearningPathModel(
      language: (
        json['language'] ??
        json['learning_language'] ??
        ''
      )
          .toString()
          .toLowerCase(),
      level: (
        json['level'] ??
        json['current_level'] ??
        ''
      )
          .toString()
          .toUpperCase(),
      nextLevel: (
        json['next_level'] ??
        ''
      )
          .toString()
          .toUpperCase(),
      progress: progress,
      completedLessons: completedLessons,
      totalLessons: totalLessons,
      lessons: lessons,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'language': language,
      'level': level,
      'next_level': nextLevel,
      'progress': progress,
      'completed_lessons': completedLessons,
      'total_lessons': totalLessons,
      'lessons': lessons
          .map((lesson) => lesson.toJson())
          .toList(),
    };
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static double _parseProgress(dynamic value) {
    double parsed;

    if (value is num) {
      parsed = value.toDouble();
    } else {
      parsed = double.tryParse(value?.toString() ?? '') ??
          0;
    }

    return parsed.clamp(0.0, 100.0);
  }
}