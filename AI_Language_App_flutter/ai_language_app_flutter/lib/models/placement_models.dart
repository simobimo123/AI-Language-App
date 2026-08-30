class PlacementWord {
  final int id;
  final String word;
  final String level;
  final int? vocabularySenseId;
  final int? vocabularyFormId;

  const PlacementWord({
    required this.id,
    required this.word,
    required this.level,
    this.vocabularySenseId,
    this.vocabularyFormId,
  });

  factory PlacementWord.fromJson(Map<String, dynamic> json) {
    return PlacementWord(
      id: (json['id'] as num).toInt(),
      word: json['word']?.toString() ?? '',
      level: json['level']?.toString() ?? '',
      vocabularySenseId: (json['vocabulary_sense_id'] as num?)?.toInt(),
      vocabularyFormId: (json['vocabulary_form_id'] as num?)?.toInt(),
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'id':
        return id;
      case 'word':
        return word;
      case 'level':
        return level;
      case 'vocabulary_sense_id':
        return vocabularySenseId;
      case 'vocabulary_form_id':
        return vocabularyFormId;
      default:
        return null;
    }
  }
}

class PlacementWordsResponse {
  final String language;
  final String level;
  final List<PlacementWord> words;

  const PlacementWordsResponse({
    required this.language,
    required this.level,
    required this.words,
  });

  factory PlacementWordsResponse.fromJson(Map<String, dynamic> json) {
    final rawWords = json['words'];

    return PlacementWordsResponse(
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString() ?? '',
      words: rawWords is List
          ? rawWords
              .whereType<Map>()
              .map(
                (word) => PlacementWord.fromJson(
                  Map<String, dynamic>.from(word),
                ),
              )
              .toList()
          : const [],
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'language':
        return language;
      case 'level':
        return level;
      case 'words':
        return words;
      default:
        return null;
    }
  }
}

class PlacementWordEvaluation {
  final String language;
  final String level;
  final int totalWords;
  final int knownWords;
  final double percentage;
  final bool passed;
  final String? nextLevel;
  final String preliminaryLevel;

  const PlacementWordEvaluation({
    required this.language,
    required this.level,
    required this.totalWords,
    required this.knownWords,
    required this.percentage,
    required this.passed,
    required this.nextLevel,
    required this.preliminaryLevel,
  });

  factory PlacementWordEvaluation.fromJson(Map<String, dynamic> json) {
    return PlacementWordEvaluation(
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString() ?? '',
      totalWords: (json['total_words'] as num?)?.toInt() ?? 0,
      knownWords: (json['known_words'] as num?)?.toInt() ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0,
      passed: json['passed'] == true,
      nextLevel: json['next_level']?.toString(),
      preliminaryLevel: json['preliminary_level']?.toString() ?? '',
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'language':
        return language;
      case 'level':
        return level;
      case 'total_words':
        return totalWords;
      case 'known_words':
        return knownWords;
      case 'percentage':
        return percentage;
      case 'passed':
        return passed;
      case 'next_level':
        return nextLevel;
      case 'preliminary_level':
        return preliminaryLevel;
      default:
        return null;
    }
  }
}

class PlacementQuizQuestion {
  final int id;
  final String question;
  final List<String> choices;
  final String questionType;
  final String? explanation;

  const PlacementQuizQuestion({
    required this.id,
    required this.question,
    required this.choices,
    required this.questionType,
    required this.explanation,
  });

  factory PlacementQuizQuestion.fromJson(Map<String, dynamic> json) {
    final rawChoices = json['choices'];

    return PlacementQuizQuestion(
      id: (json['id'] as num).toInt(),
      question: json['question']?.toString() ?? '',
      choices: rawChoices is List
          ? rawChoices.map((choice) => choice.toString()).toList()
          : const [],
      questionType:
          json['question_type']?.toString() ?? 'multiple_choice',
      explanation: json['explanation']?.toString(),
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'id':
        return id;
      case 'question':
        return question;
      case 'choices':
        return choices;
      case 'question_type':
        return questionType;
      case 'explanation':
        return explanation;
      default:
        return null;
    }
  }
}

class PlacementQuizResponse {
  final String language;
  final String level;
  final List<PlacementQuizQuestion> questions;

  const PlacementQuizResponse({
    required this.language,
    required this.level,
    required this.questions,
  });

  factory PlacementQuizResponse.fromJson(Map<String, dynamic> json) {
    final rawQuestions = json['questions'];

    return PlacementQuizResponse(
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString() ?? '',
      questions: rawQuestions is List
          ? rawQuestions
              .whereType<Map>()
              .map(
                (question) => PlacementQuizQuestion.fromJson(
                  Map<String, dynamic>.from(question),
                ),
              )
              .toList()
          : const [],
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'language':
        return language;
      case 'level':
        return level;
      case 'questions':
        return questions;
      default:
        return null;
    }
  }
}

class PlacementQuizEvaluation {
  final String language;
  final String level;
  final int totalQuestions;
  final int correctAnswers;
  final double percentage;
  final bool passed;
  final String finalLevel;

  const PlacementQuizEvaluation({
    required this.language,
    required this.level,
    required this.totalQuestions,
    required this.correctAnswers,
    required this.percentage,
    required this.passed,
    required this.finalLevel,
  });

  factory PlacementQuizEvaluation.fromJson(Map<String, dynamic> json) {
    return PlacementQuizEvaluation(
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString() ?? '',
      totalQuestions: (json['total_questions'] as num?)?.toInt() ?? 0,
      correctAnswers: (json['correct_answers'] as num?)?.toInt() ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0,
      passed: json['passed'] == true,
      finalLevel: json['final_level']?.toString() ?? '',
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'language':
        return language;
      case 'level':
        return level;
      case 'total_questions':
        return totalQuestions;
      case 'correct_answers':
        return correctAnswers;
      case 'percentage':
        return percentage;
      case 'passed':
        return passed;
      case 'final_level':
        return finalLevel;
      default:
        return null;
    }
  }
}

class PlacementFinalizeResponse {
  final String message;
  final int? attemptId;
  final String language;
  final String level;
  final double progress;

  const PlacementFinalizeResponse({
    required this.message,
    required this.attemptId,
    required this.language,
    required this.level,
    required this.progress,
  });

  factory PlacementFinalizeResponse.fromJson(Map<String, dynamic> json) {
    return PlacementFinalizeResponse(
      message: json['message']?.toString() ?? '',
      attemptId: (json['attempt_id'] as num?)?.toInt(),
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString() ?? '',
      progress: (json['progress'] as num?)?.toDouble() ?? 0,
    );
  }

  dynamic operator [](String key) {
    switch (key) {
      case 'message':
        return message;
      case 'attempt_id':
        return attemptId;
      case 'language':
        return language;
      case 'level':
        return level;
      case 'progress':
        return progress;
      default:
        return null;
    }
  }
}
