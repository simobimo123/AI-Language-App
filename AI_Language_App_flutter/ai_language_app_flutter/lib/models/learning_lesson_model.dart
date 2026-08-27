enum LearningLessonStatus {
  completed,
  current,
  unlocked,
  locked,
}

class LearningLessonModel {
  final int id;
  final String language;
  final String level;
  final int unitNumber;
  final int lessonOrder;
  final String topicKey;
  final bool isTest;
  final double passingScore;

  final LearningLessonStatus status;
  final double progress;
  final double score;

  const LearningLessonModel({
    required this.id,
    required this.language,
    required this.level,
    required this.unitNumber,
    required this.lessonOrder,
    required this.topicKey,
    required this.isTest,
    required this.passingScore,
    required this.status,
    this.progress = 0,
    this.score = 0,
  });

  factory LearningLessonModel.fromJson(
    Map<String, dynamic> json,
  ) {
    final topicKey = json['topic_key']?.toString() ??
        json['topic']?.toString() ??
        '';

    final isTest =
        json['is_test'] == true || topicKey == 'level_test';

    final status = _parseStatus(json['status']);

    return LearningLessonModel(
      id: _parseInt(json['id']),
      language: json['language']?.toString() ?? '',
      level: json['level']?.toString().toUpperCase() ?? '',
      unitNumber: _parseInt(json['unit_number']),
      lessonOrder: _parseInt(
        json['lesson_order'] ?? json['order'],
      ),
      topicKey: topicKey,
      isTest: isTest,
      passingScore: _parseDouble(
        json['passing_score'],
        defaultValue: 80,
      ),
      status: status,
      progress: _parseDouble(json['progress']),
      score: _parseDouble(
        json['score'] ?? json['best_score'],
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'language': language,
      'level': level,
      'unit_number': unitNumber,
      'lesson_order': lessonOrder,
      'topic_key': topicKey,
      'is_test': isTest,
      'passing_score': passingScore,
      'status': status.name,
      'progress': progress,
      'score': score,
    };
  }

  bool get isCompleted =>
      status == LearningLessonStatus.completed;

  bool get isCurrent =>
      status == LearningLessonStatus.current;

  bool get isUnlocked =>
      status == LearningLessonStatus.unlocked ||
      isCurrent ||
      isCompleted;

  String get title {
    switch (topicKey) {
      case 'sounds_and_letters':
        return 'الأصوات والحروف';
      case 'basic_greetings':
        return 'التحيات الأساسية';
      case 'numbers_0_10':
        return 'الأرقام من 0 إلى 10';
      case 'colors':
        return 'الألوان';
      case 'family_basics':
        return 'أفراد العائلة';
      case 'everyday_objects':
        return 'الأشياء اليومية';
      case 'very_basic_phrases':
        return 'العبارات الأساسية';

      case 'alphabet':
        return 'الأبجدية';
      case 'basic_words':
        return 'الكلمات الأساسية';
      case 'numbers':
        return 'الأرقام';
      case 'greetings':
        return 'التحيات';
      case 'introductions':
        return 'التعريف بالنفس';
      case 'family':
        return 'العائلة';
      case 'simple_sentences':
        return 'الجمل البسيطة';

      case 'daily_life':
        return 'الحياة اليومية';
      case 'past_tense':
        return 'زمن الماضي';
      case 'future':
        return 'المستقبل';
      case 'shopping':
        return 'التسوق';
      case 'travel':
        return 'السفر';
      case 'health':
        return 'الصحة';
      case 'describing_people':
        return 'وصف الأشخاص';

      case 'daily_conversations':
        return 'المحادثات اليومية';
      case 'telling_stories':
        return 'سرد القصص';
      case 'work':
        return 'العمل';
      case 'opinions':
        return 'التعبير عن الآراء';
      case 'social_situations':
        return 'المواقف الاجتماعية';
      case 'media':
        return 'الإعلام والمحتوى';
      case 'extended_conversations':
        return 'المحادثات الممتدة';

      case 'debates':
        return 'المناظرات';
      case 'arguments':
        return 'الحجج والنقاش';
      case 'complex_vocabulary':
        return 'المفردات المعقدة';
      case 'idioms':
        return 'التعابير الاصطلاحية';
      case 'workplace':
        return 'بيئة العمل';
      case 'problem_solving':
        return 'حل المشكلات';
      case 'presentations':
        return 'العروض التقديمية';

      case 'language_nuance':
        return 'دقة اللغة والفروق الدقيقة';
      case 'advanced_grammar':
        return 'القواعد المتقدمة';
      case 'formal_speech':
        return 'الخطاب الرسمي';
      case 'academic_language':
        return 'اللغة الأكاديمية';
      case 'professional_language':
        return 'اللغة المهنية';
      case 'culture':
        return 'الثقافة';
      case 'critical_discussion':
        return 'النقاش النقدي';

      case 'language_mastery':
        return 'إتقان اللغة';
      case 'rhetoric':
        return 'البلاغة';
      case 'advanced_idioms':
        return 'التعابير الاصطلاحية المتقدمة';
      case 'language_register':
        return 'مستويات استخدام اللغة';
      case 'complex_debates':
        return 'المناظرات المعقدة';
      case 'interpretation':
        return 'التفسير والترجمة';
      case 'fluency':
        return 'الطلاقة';

      case 'level_test':
        return 'اختبار المستوى';

      default:
        return topicKey.replaceAll('_', ' ').trim();
    }
  }

  String get subtitle {
    switch (topicKey) {
      case 'sounds_and_letters':
        return 'تعرف على الأصوات والحروف الأساسية في اللغة.';
      case 'basic_greetings':
        return 'تعلم كيف تقول مرحبًا وتحيّي الآخرين.';
      case 'numbers_0_10':
        return 'تعلم الأرقام الأساسية من صفر إلى عشرة.';
      case 'colors':
        return 'تعلم أسماء الألوان الأساسية واستخدمها في جمل بسيطة.';
      case 'family_basics':
        return 'تعلم الكلمات الأولى للتحدث عن أفراد العائلة.';
      case 'everyday_objects':
        return 'تعرف على أسماء الأشياء التي تراها وتستخدمها يوميًا.';
      case 'very_basic_phrases':
        return 'تدرب على العبارات القصيرة والأساسية جدًا.';

      case 'alphabet':
        return 'تعلم أساسيات الأبجدية والكتابة.';
      case 'basic_words':
        return 'تعلم الكلمات الأساسية التي تحتاجها في البداية.';
      case 'numbers':
        return 'تدرب على استخدام الأرقام في مواقف مختلفة.';
      case 'greetings':
        return 'تعلم التحيات والتواصل الأولي مع الآخرين.';
      case 'introductions':
        return 'تعلم كيف تقدم نفسك وتسأل عن معلومات أساسية.';
      case 'family':
        return 'تحدث عن عائلتك وأفرادها بجمل بسيطة.';
      case 'simple_sentences':
        return 'كوّن جملك الأولى واستخدمها في مواقف يومية.';

      case 'daily_life':
        return 'تحدث عن روتينك وحياتك اليومية.';
      case 'past_tense':
        return 'تعلم استخدام الماضي للتحدث عن الأحداث السابقة.';
      case 'future':
        return 'تحدث عن الخطط والأحداث المستقبلية.';
      case 'shopping':
        return 'استخدم اللغة في مواقف التسوق والشراء.';
      case 'travel':
        return 'تدرب على اللغة المستخدمة أثناء السفر.';
      case 'health':
        return 'تحدث عن الصحة والأعراض والمواقف الصحية.';
      case 'describing_people':
        return 'تعلم كيف تصف الأشخاص ومظهرهم وشخصياتهم.';

      case 'daily_conversations':
        return 'تحدث عن المواقف والمحادثات التي تواجهها يوميًا.';
      case 'telling_stories':
        return 'تعلم كيف تحكي الأحداث والتجارب بطريقة واضحة.';
      case 'work':
        return 'استخدم اللغة في مواقف العمل والدراسة المهنية.';
      case 'opinions':
        return 'عبّر عن رأيك وناقش أفكارك بطريقة طبيعية.';
      case 'social_situations':
        return 'تدرب على مواقف اجتماعية متنوعة.';
      case 'media':
        return 'ناقش الأخبار والمحتوى ومواضيع الإعلام.';
      case 'extended_conversations':
        return 'خض محادثات أطول وأكثر تعقيدًا.';

      case 'debates':
        return 'تدرب على مناقشة الأفكار والحجج المختلفة.';
      case 'arguments':
        return 'تعلم كيف تبني الحجج وتدعم وجهة نظرك.';
      case 'complex_vocabulary':
        return 'وسّع مفرداتك واستخدم الكلمات الأكثر تعقيدًا.';
      case 'idioms':
        return 'تعلم التعابير الاصطلاحية الشائعة واستخداماتها.';
      case 'workplace':
        return 'استخدم اللغة في المواقف المهنية وبيئة العمل.';
      case 'problem_solving':
        return 'تدرب على شرح المشكلات واقتراح الحلول.';
      case 'presentations':
        return 'تعلم تقديم الأفكار والمعلومات بطريقة منظمة.';

      case 'language_nuance':
        return 'افهم الفروق الدقيقة والمعاني الدقيقة في اللغة.';
      case 'advanced_grammar':
        return 'تعمق في القواعد والتراكيب المتقدمة.';
      case 'formal_speech':
        return 'استخدم اللغة الرسمية في المواقف المناسبة.';
      case 'academic_language':
        return 'تدرب على اللغة المستخدمة في السياقات الأكاديمية.';
      case 'professional_language':
        return 'طوّر لغتك للمواقف المهنية المتقدمة.';
      case 'culture':
        return 'استكشف اللغة من خلال الثقافة والسياق الاجتماعي.';
      case 'critical_discussion':
        return 'ناقش الأفكار المعقدة بطريقة دقيقة ونقدية.';

      case 'language_mastery':
        return 'طوّر استخدامك للغة إلى مستوى متقدم جدًا.';
      case 'rhetoric':
        return 'تعلم استخدام الأساليب البلاغية والتعبير المتقدم.';
      case 'advanced_idioms':
        return 'افهم التعابير الاصطلاحية المتقدمة والمعاني المجازية.';
      case 'language_register':
        return 'تعلم اختيار أسلوب اللغة المناسب لكل سياق.';
      case 'complex_debates':
        return 'شارك في نقاشات ومناظرات ذات مستوى عالٍ من التعقيد.';
      case 'interpretation':
        return 'تدرب على فهم المعاني الدقيقة وتفسيرها.';
      case 'fluency':
        return 'طوّر طلاقتك واستخدامك الطبيعي للغة.';

      case 'level_test':
        return 'اختبر جاهزيتك للانتقال إلى المستوى التالي.';

      default:
        return 'تابع هذا الدرس لتطوير مستواك.';
    }
  }

  static LearningLessonStatus _parseStatus(dynamic value) {
    switch (value?.toString().toLowerCase()) {
      case 'completed':
        return LearningLessonStatus.completed;
      case 'current':
        return LearningLessonStatus.current;
      case 'unlocked':
        return LearningLessonStatus.unlocked;
      case 'locked':
      default:
        return LearningLessonStatus.locked;
    }
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

  static double _parseDouble(
    dynamic value, {
    double defaultValue = 0,
  }) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value?.toString() ?? '') ??
        defaultValue;
  }
}