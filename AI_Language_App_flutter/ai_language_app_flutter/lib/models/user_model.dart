class UserModel {
  final int id;
  final String name;
  final String email;
  final String? googleId;
  final String nativeLanguage;
  final String learningLanguage;
  final bool isActive;
  final DateTime? createdAt;

  const UserModel({
    required this.id,
    required this.name,
    required this.email,
    this.googleId,
    required this.nativeLanguage,
    required this.learningLanguage,
    required this.isActive,
    this.createdAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: _parseInt(json['id']),
      name: json['name']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      googleId: json['google_id']?.toString(),
      nativeLanguage: json['native_language']?.toString() ?? '',
      learningLanguage: json['learning_language']?.toString() ?? '',
      isActive: _parseBool(json['is_active'], defaultValue: true),
      createdAt: _parseDateTime(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'google_id': googleId,
      'native_language': nativeLanguage,
      'learning_language': learningLanguage,
      'is_active': isActive,
      'created_at': createdAt?.toIso8601String(),
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

  static bool _parseBool(
    dynamic value, {
    required bool defaultValue,
  }) {
    if (value is bool) {
      return value;
    }

    if (value == null) {
      return defaultValue;
    }

    final normalized = value.toString().toLowerCase();

    if (normalized == 'true' || normalized == '1') {
      return true;
    }

    if (normalized == 'false' || normalized == '0') {
      return false;
    }

    return defaultValue;
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