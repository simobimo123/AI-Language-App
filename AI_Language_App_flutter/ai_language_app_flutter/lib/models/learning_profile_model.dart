class LearningProfileModel {
  final int id;
  final int userId;
  final String language;
  final String level;
  final double progress;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const LearningProfileModel({
    required this.id,
    required this.userId,
    required this.language,
    required this.level,
    required this.progress,
    this.createdAt,
    this.updatedAt,
  });

  factory LearningProfileModel.fromJson(
    Map<String, dynamic> json,
  ) {
    return LearningProfileModel(
      id: _parseInt(json['id']),
      userId: _parseInt(json['user_id']),
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString().toUpperCase() ?? '',
      progress: _parseProgress(json['progress']),
      createdAt: _parseDateTime(json['created_at']),
      updatedAt: _parseDateTime(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'language': language,
      'level': level,
      'progress': progress,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
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
      parsed = double.tryParse(value?.toString() ?? '') ?? 0;
    }

    return parsed.clamp(0.0, 100.0);
  }

  static DateTime? _parseDateTime(dynamic value) {
    if (value is DateTime) {
      return value;
    }

    if (value == null) {
      return null;
    }

    return DateTime.tryParse(value.toString());
  }
}