class LessonChatStoredMessage {
  final String role;
  final String text;

  const LessonChatStoredMessage({
    required this.role,
    required this.text,
  });
}

class LessonChatStoredSession {
  final int lessonId;
  final String stage;
  String? conversationId;
  final List<LessonChatStoredMessage> messages;
  final Map<int, String> translations;
  bool completed;

  LessonChatStoredSession({
    required this.lessonId,
    required this.stage,
    this.conversationId,
    List<LessonChatStoredMessage>? messages,
    Map<int, String>? translations,
    this.completed = false,
  }) : messages = List<LessonChatStoredMessage>.from(messages ?? const []),
       translations = Map<int, String>.from(translations ?? const {});

  LessonChatStoredSession copy() {
    return LessonChatStoredSession(
      lessonId: lessonId,
      stage: stage,
      conversationId: conversationId,
      messages: messages,
      translations: translations,
      completed: completed,
    );
  }
}

class LessonChatSessionStore {
  LessonChatSessionStore._();

  static final LessonChatSessionStore instance = LessonChatSessionStore._();

  final Map<String, LessonChatStoredSession> _sessions = {};

  String _key(int lessonId, String stage) =>
      '$lessonId:${stage.trim().toLowerCase()}';

  LessonChatStoredSession? get({
    required int lessonId,
    required String stage,
  }) {
    return _sessions[_key(lessonId, stage)];
  }

  LessonChatStoredSession getOrCreate({
    required int lessonId,
    required String stage,
  }) {
    final key = _key(lessonId, stage);

    return _sessions.putIfAbsent(
      key,
      () => LessonChatStoredSession(
        lessonId: lessonId,
        stage: stage,
      ),
    );
  }

  void save(LessonChatStoredSession session) {
    _sessions[_key(session.lessonId, session.stage)] = session;
  }

  void clear({
    required int lessonId,
    required String stage,
  }) {
    _sessions.remove(_key(lessonId, stage));
  }

  void clearLesson(int lessonId) {
    _sessions.removeWhere(
      (_, session) => session.lessonId == lessonId,
    );
  }

  void clearAll() {
    _sessions.clear();
  }
}

final lessonChatSessionStore = LessonChatSessionStore.instance;
