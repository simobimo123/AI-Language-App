class StatsModel {
  final int streakDays;
  final int learnedWords;
  final int conversations;
  final double learningProgress;
  final int completedLessons;
  final int totalLessons;

  const StatsModel({
    required this.streakDays,
    required this.learnedWords,
    required this.conversations,
    required this.learningProgress,
    required this.completedLessons,
    required this.totalLessons,
  });

  factory StatsModel.fromJson(Map<String, dynamic> json) {
    return StatsModel(
      streakDays: _parseInt(json['streak_days']),
      learnedWords: _parseInt(json['learned_words']),
      conversations: _parseInt(json['conversations']),
      learningProgress: _parseDouble(
        json['learning_progress'],
      ),
      completedLessons: _parseInt(
        json['completed_lessons'],
      ),
      totalLessons: _parseInt(
        json['total_lessons'],
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'streak_days': streakDays,
      'learned_words': learnedWords,
      'conversations': conversations,
      'learning_progress': learningProgress,
      'completed_lessons': completedLessons,
      'total_lessons': totalLessons,
    };
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(
          value?.toString() ?? '',
        ) ??
        0;
  }

  static double _parseDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(
          value?.toString() ?? '',
        ) ??
        0.0;
  }
}