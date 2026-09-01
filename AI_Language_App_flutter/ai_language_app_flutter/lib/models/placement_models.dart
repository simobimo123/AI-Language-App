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
