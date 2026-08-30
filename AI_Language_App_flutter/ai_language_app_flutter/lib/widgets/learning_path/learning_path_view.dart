
import 'package:flutter/material.dart';

import '../../controllers/learning_path_controller.dart';
import '../../core/language/language_controller.dart';
import '../../models/learning_lesson_model.dart';

class LearningPathView extends StatelessWidget {
  final LearningPathController controller;
  final LanguageController languageController;
  final VoidCallback onRetry;
  final void Function(LearningLessonModel lesson) onLessonTap;

  const LearningPathView({
    super.key,
    required this.controller,
    required this.languageController,
    required this.onRetry,
    required this.onLessonTap,
  });

  String _text({
    required String ar,
    required String en,
    required String fr,
    required String es,
    required String zh,
    required String ja,
    required String ko,
  }) {
    switch (languageController.locale.languageCode) {
      case 'fr':
        return fr;
      case 'es':
        return es;
      case 'zh':
        return zh;
      case 'ja':
        return ja;
      case 'ko':
        return ko;
      case 'en':
        return en;
      case 'ar':
      default:
        return ar;
    }
  }

  String _level(String value) =>
      value.toUpperCase() == 'PRE_A1' ? 'Pre-A1' : value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (controller.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (controller.errorMessage != null) {
      return _buildError(theme);
    }

    final lessons = controller.lessons;

    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 55),
        children: [
          _buildProgressCard(theme),
          if (lessons.isEmpty) ...[
            const SizedBox(height: 38),
            _buildEmpty(theme),
          ] else ...[
            const SizedBox(height: 28),
            _buildPathHeader(theme),
            const SizedBox(height: 20),
            _buildMap(theme, lessons, context),
          ],
        ],
      ),
    );
  }

  Widget _buildProgressCard(ThemeData theme) {
    final current = _level(controller.currentLevel);
    final next = _level(controller.nextLevel);
    final progress = (controller.progress / 100).clamp(0.0, 1.0);

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primary,
            theme.colorScheme.secondary,
          ],
        ),
        borderRadius: BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withValues(alpha: .20),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: .18),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(
                  Icons.route_rounded,
                  color: Colors.white,
                  size: 28,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _text(
                        ar: 'رحلة تعلّمك',
                        en: 'Your Learning Journey',
                        fr: 'Votre parcours',
                        es: 'Tu recorrido de aprendizaje',
                        zh: '你的学习之旅',
                        ja: 'あなたの学習 journey',
                        ko: '나의 학습 여정',
                      ),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 21,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _text(
                        ar: 'تقدم خطوة بخطوة وتعلم من خلال الممارسة.',
                        en: 'Move step by step and learn through practice.',
                        fr: 'Progressez étape par étape grâce à la pratique.',
                        es: 'Avanza paso a paso y aprende mediante la práctica.',
                        zh: '一步一步前进，通过实践学习。',
                        ja: '一歩ずつ進み、実践を通して学びましょう。',
                        ko: '한 단계씩 연습하며 학습하세요.',
                      ),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _text(
                  ar: 'تقدمك الحالي',
                  en: 'Your progress',
                  fr: 'Votre progression',
                  es: 'Tu progreso',
                  zh: '当前进度',
                  ja: '現在の進捗',
                  ko: '현재 진행률',
                ),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                ),
              ),
              Text(
                '${controller.progress.round()}%',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 9,
              backgroundColor: const Color(0x40FFFFFF),
              valueColor: const AlwaysStoppedAnimation<Color>(
                Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.auto_awesome_rounded,
                color: Colors.white,
                size: 17,
              ),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  _learningLanguageLabel(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ),
              if (controller.currentLevel.isNotEmpty) ...[
                const SizedBox(width: 8),
                Flexible(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: .18),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      controller.nextLevel.isNotEmpty
                          ? '$current → $next'
                          : current,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPathHeader(ThemeData theme) {
    final current = _level(controller.currentLevel);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.flag_rounded,
              color: theme.colorScheme.onPrimaryContainer,
              size: 23,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  controller.currentLevel.isNotEmpty
                      ? _text(
                          ar: 'رحلتك في المستوى $current',
                          en: 'Your $current journey',
                          fr: 'Votre parcours $current',
                          es: 'Tu recorrido $current',
                          zh: '你的 $current 学习之旅',
                          ja: '$current の学習パス',
                          ko: '$current 학습 여정',
                        )
                      : _text(
                          ar: 'رحلتك التعليمية',
                          en: 'Your learning journey',
                          fr: 'Votre parcours',
                          es: 'Tu recorrido',
                          zh: '你的学习之旅',
                          ja: 'あなたの学習パス',
                          ko: '나의 학습 여정',
                        ),
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.onSurface,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _text(
                    ar: 'أكمل الدروس بالترتيب لفتح الخطوات التالية.',
                    en: 'Complete lessons to unlock the next steps.',
                    fr: 'Terminez les leçons pour débloquer les étapes suivantes.',
                    es: 'Completa las lecciones para desbloquear los siguientes pasos.',
                    zh: '完成课程以解锁下一步。',
                    ja: 'レッスンを完了して次のステップを解除しましょう。',
                    ko: '수업을 완료하여 다음 단계를 잠금 해제하세요.',
                  ),
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.4,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMap(
    ThemeData theme,
    List<LearningLessonModel> lessons,
    BuildContext context,
  ) {
    return Column(
      children: List.generate(
        lessons.length,
        (index) {
          final lesson = lessons[index];
          final left = index.isEven;

          return Column(
            children: [
              _buildLessonRow(
                theme,
                lesson,
                left,
                context,
              ),
              if (index < lessons.length - 1)
                _buildConnector(
                  theme,
                  lesson,
                  lessons[index + 1],
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildLessonRow(
    ThemeData theme,
    LearningLessonModel lesson,
    bool left,
    BuildContext context,
  ) {
    final compact = MediaQuery.of(context).size.width < 370;

    final node = _buildNode(
      theme,
      lesson,
      compact ? 50 : 56,
    );

    final card = Expanded(
      child: _buildCard(
        theme,
        lesson,
        left,
        compact,
      ),
    );

    return Row(
      children: left
          ? [
              card,
              const SizedBox(width: 10),
              node,
              const SizedBox(width: 2),
            ]
          : [
              const SizedBox(width: 2),
              node,
              const SizedBox(width: 10),
              card,
            ],
    );
  }

  Widget _buildCard(
    ThemeData theme,
    LearningLessonModel lesson,
    bool left,
    bool compact,
  ) {
    final current =
        lesson.status == LearningLessonStatus.current;
    final unlocked = lesson.isUnlocked;

    final background = current
        ? theme.colorScheme.primaryContainer
        : !unlocked
            ? theme.colorScheme.surfaceContainerHighest
                .withValues(alpha: .55)
            : theme.colorScheme.surface;

    return GestureDetector(
      onTap: unlocked ? () => onLessonTap(lesson) : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        padding: EdgeInsets.all(compact ? 11 : 14),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: current
                ? theme.colorScheme.primary.withValues(alpha: .5)
                : theme.colorScheme.outlineVariant.withValues(
                    alpha: unlocked ? .9 : .55,
                  ),
            width: current ? 1.7 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(
                alpha:
                    theme.brightness == Brightness.dark ? .12 : .045,
              ),
              blurRadius: current ? 14 : 9,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: left
              ? [
                  _edgeIcon(theme, lesson, compact),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _textContent(
                      theme,
                      lesson,
                      true,
                    ),
                  ),
                ]
              : [
                  Expanded(
                    child: _textContent(
                      theme,
                      lesson,
                      false,
                    ),
                  ),
                  const SizedBox(width: 10),
                  _edgeIcon(theme, lesson, compact),
                ],
        ),
      ),
    );
  }

  Widget _edgeIcon(
    ThemeData theme,
    LearningLessonModel lesson,
    bool compact,
  ) {
    final completed =
        lesson.status == LearningLessonStatus.completed;
    final current =
        lesson.status == LearningLessonStatus.current;
    final unlocked = lesson.isUnlocked;

    final bg = completed
        ? Colors.green.shade600
        : current
            ? theme.colorScheme.primary
            : unlocked
                ? theme.colorScheme.primaryContainer
                : theme.colorScheme.surfaceContainerHighest;

    final fg = completed || current
        ? Colors.white
        : unlocked
            ? theme.colorScheme.primary
            : theme.colorScheme.onSurfaceVariant;

    return Container(
      width: compact ? 38 : 43,
      height: compact ? 38 : 43,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(13),
      ),
      child: Icon(
        completed
            ? Icons.check_rounded
            : current
                ? Icons.play_arrow_rounded
                : lesson.isTest
                    ? Icons.verified_rounded
                    : _topicIcon(lesson.topicKey),
        color: fg,
        size: compact ? 20 : 22,
      ),
    );
  }

  Widget _textContent(
    ThemeData theme,
    LearningLessonModel lesson,
    bool left,
  ) {
    return Column(
      crossAxisAlignment:
          left ? CrossAxisAlignment.start : CrossAxisAlignment.end,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                lesson.title,
                textAlign:
                    left ? TextAlign.left : TextAlign.right,
                softWrap: true,
                style: TextStyle(
                  fontSize: 14.5,
                  height: 1.3,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onSurface,
                ),
              ),
            ),
            if (lesson.isTest) ...[
              const SizedBox(width: 6),
              _testBadge(theme),
            ],
          ],
        ),
        const SizedBox(height: 7),
        Text(
          lesson.subtitle,
          textAlign: left ? TextAlign.left : TextAlign.right,
          softWrap: true,
          style: TextStyle(
            fontSize: 11.5,
            height: 1.5,
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        if (lesson.status == LearningLessonStatus.current) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 10,
              vertical: 5,
            ),
            decoration: BoxDecoration(
              color: theme.colorScheme.primary,
              borderRadius: BorderRadius.circular(9),
            ),
            child: Text(
              _text(
                ar: 'ابدأ الآن',
                en: 'Start now',
                fr: 'Commencer',
                es: 'Empezar',
                zh: '立即开始',
                ja: '今すぐ開始',
                ko: '지금 시작',
              ),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _testBadge(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 7,
        vertical: 3,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(7),
      ),
      child: Text(
        _text(
          ar: 'اختبار',
          en: 'Test',
          fr: 'Test',
          es: 'Prueba',
          zh: '测试',
          ja: 'テスト',
          ko: '시험',
        ),
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.bold,
          color: theme.colorScheme.onSecondaryContainer,
        ),
      ),
    );
  }

  Widget _buildNode(
    ThemeData theme,
    LearningLessonModel lesson,
    double size,
  ) {
    final completed =
        lesson.status == LearningLessonStatus.completed;
    final current =
        lesson.status == LearningLessonStatus.current;
    final unlocked = lesson.isUnlocked;

    final bg = completed
        ? Colors.green.shade600
        : current
            ? theme.colorScheme.primary
            : unlocked
                ? theme.colorScheme.primaryContainer
                : theme.colorScheme.surfaceContainerHighest;

    final border = completed
        ? Colors.green.shade600
        : current
            ? theme.colorScheme.primary
            : theme.colorScheme.outlineVariant;

    return GestureDetector(
      onTap: unlocked ? () => onLessonTap(lesson) : null,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: bg,
          shape: BoxShape.circle,
          border: Border.all(
            color: border,
            width: current ? 3.5 : 2,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: .07),
              blurRadius: 7,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Icon(
          completed
              ? Icons.check_rounded
              : current
                  ? Icons.play_arrow_rounded
                  : lesson.isTest
                      ? Icons.verified_rounded
                      : unlocked
                          ? _topicIcon(lesson.topicKey)
                          : Icons.lock_rounded,
          size: current ? 27 : 21,
          color: completed || current
              ? Colors.white
              : unlocked
                  ? theme.colorScheme.primary
                  : theme.colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }

  Widget _buildConnector(
    ThemeData theme,
    LearningLessonModel current,
    LearningLessonModel next,
  ) {
    final completed =
        current.status == LearningLessonStatus.completed;

    return SizedBox(
      height: 34,
      child: CustomPaint(
        painter: _ConnectorPainter(
          color: completed
              ? Colors.green.shade500
              : theme.colorScheme.outlineVariant,
          locked:
              next.status == LearningLessonStatus.locked,
        ),
        child: const SizedBox.expand(),
      ),
    );
  }

  Widget _buildError(ThemeData theme) {
    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 80),
          Icon(
            Icons.cloud_off_rounded,
            size: 64,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 18),
          Text(
            _text(
              ar: 'تعذر تحميل مسار التعلم',
              en: 'Could not load the learning path',
              fr: 'Impossible de charger le parcours',
              es: 'No se pudo cargar la ruta de aprendizaje',
              zh: '无法加载学习路径',
              ja: '学習パスを読み込めませんでした',
              ko: '학습 경로를 불러오지 못했습니다',
            ),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            controller.errorMessage ?? '',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: theme.colorScheme.onSurfaceVariant,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 24),
          Center(
            child: FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(
                _text(
                  ar: 'إعادة المحاولة',
                  en: 'Try again',
                  fr: 'Réessayer',
                  es: 'Intentar de nuevo',
                  zh: '重试',
                  ja: '再試行',
                  ko: '다시 시도',
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty(ThemeData theme) {
    return Column(
      children: [
        Icon(
          Icons.route_outlined,
          size: 60,
          color: theme.colorScheme.onSurfaceVariant,
        ),
        const SizedBox(height: 16),
        Text(
          _text(
            ar: 'لا توجد دروس متاحة حاليًا',
            en: 'No lessons are currently available',
            fr: 'Aucune leçon disponible actuellement',
            es: 'No hay lecciones disponibles actualmente',
            zh: '目前没有可用课程',
            ja: '現在利用できるレッスンはありません',
            ko: '현재 이용 가능한 수업이 없습니다',
          ),
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          _text(
            ar: 'اسحب للأسفل لتحديث المسار.',
            en: 'Pull down to refresh the path.',
            fr: 'Tirez vers le bas pour actualiser.',
            es: 'Desliza hacia abajo para actualizar.',
            zh: '下拉以刷新学习路径。',
            ja: '下に引っ張って更新してください。',
            ko: '아래로 당겨 새로고침하세요.',
          ),
          textAlign: TextAlign.center,
          style: TextStyle(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  String _learningLanguageLabel() {
    return _text(
      ar: 'اللغة المستهدفة: ${_learningLanguageName()}',
      en: 'Target language: ${_learningLanguageName()}',
      fr: 'Langue cible : ${_learningLanguageName()}',
      es: 'Idioma objetivo: ${_learningLanguageName()}',
      zh: '目标语言：${_learningLanguageName()}',
      ja: '学習言語：${_learningLanguageName()}',
      ko: '학습 언어: ${_learningLanguageName()}',
    );
  }

  String _learningLanguageName() {
    const names = {
      'tr': [
        'التركية',
        'Turkish',
        'Turc',
        'Turco',
        '土耳其语',
        'トルコ語',
        '터키어',
      ],
      'en': [
        'الإنجليزية',
        'English',
        'Anglais',
        'Inglés',
        '英语',
        '英語',
        '영어',
      ],
      'fr': [
        'الفرنسية',
        'French',
        'Français',
        'Francés',
        '法语',
        'フランス語',
        '프랑스어',
      ],
      'es': [
        'الإسبانية',
        'Spanish',
        'Espagnol',
        'Español',
        '西班牙语',
        'スペイン語',
        '스페인어',
      ],
      'de': [
        'الألمانية',
        'German',
        'Allemand',
        'Alemán',
        '德语',
        'ドイツ語',
        '독일어',
      ],
      'it': [
        'الإيطالية',
        'Italian',
        'Italien',
        'Italiano',
        '意大利语',
        'イタリア語',
        '이탈리아어',
      ],
      'pt': [
        'البرتغالية',
        'Portuguese',
        'Portugais',
        'Portugués',
        '葡萄牙语',
        'ポルトガル語',
        '포르투갈어',
      ],
      'ja': [
        'اليابانية',
        'Japanese',
        'Japonais',
        'Japonés',
        '日语',
        '日本語',
        '일본어',
      ],
      'ko': [
        'الكورية',
        'Korean',
        'Coréen',
        'Coreano',
        '韩语',
        '韓国語',
        '한국어',
      ],
      'zh': [
        'الصينية',
        'Chinese',
        'Chinois',
        'Chino',
        '中文',
        '中国語',
        '중국어',
      ],
    };

    final values = names[controller.learningLanguage];

    if (values == null) {
      return controller.learningLanguage.isEmpty
          ? _text(
              ar: 'غير محددة',
              en: 'Not specified',
              fr: 'Non spécifiée',
              es: 'No especificada',
              zh: '未指定',
              ja: '未指定',
              ko: '지정되지 않음',
            )
          : controller.learningLanguage.toUpperCase();
    }

    final index = {
          'ar': 0,
          'en': 1,
          'fr': 2,
          'es': 3,
          'zh': 4,
          'ja': 5,
          'ko': 6,
        }[languageController.locale.languageCode] ??
        0;

    return values[index];
  }

  IconData _topicIcon(String key) {
    const map = {
      'sounds_and_letters': Icons.record_voice_over_rounded,
      'basic_greetings': Icons.waving_hand_rounded,
      'numbers_0_10': Icons.looks_one_rounded,
      'colors': Icons.palette_rounded,
      'family_basics': Icons.family_restroom_rounded,
      'everyday_objects': Icons.inventory_2_rounded,
      'very_basic_phrases': Icons.chat_rounded,
      'alphabet': Icons.abc_rounded,
      'basic_words': Icons.menu_book_rounded,
      'numbers': Icons.numbers_rounded,
      'greetings': Icons.waving_hand_rounded,
      'introductions': Icons.person_add_rounded,
      'family': Icons.family_restroom_rounded,
      'simple_sentences': Icons.short_text_rounded,
      'daily_life': Icons.today_rounded,
      'past_tense': Icons.history_rounded,
      'future': Icons.event_available_rounded,
      'shopping': Icons.shopping_bag_rounded,
      'travel': Icons.flight_rounded,
      'health': Icons.health_and_safety_rounded,
      'describing_people': Icons.person_search_rounded,
      'daily_conversations': Icons.chat_bubble_rounded,
      'telling_stories': Icons.auto_stories_rounded,
      'work': Icons.work_rounded,
      'opinions': Icons.forum_rounded,
      'social_situations': Icons.people_alt_rounded,
      'media': Icons.movie_rounded,
      'extended_conversations': Icons.record_voice_over_rounded,
      'debates': Icons.gavel_rounded,
      'arguments': Icons.forum_rounded,
      'complex_vocabulary': Icons.library_books_rounded,
      'idioms': Icons.format_quote_rounded,
      'workplace': Icons.business_center_rounded,
      'problem_solving': Icons.psychology_rounded,
      'presentations': Icons.present_to_all_rounded,
      'language_nuance': Icons.tune_rounded,
      'advanced_grammar': Icons.rule_rounded,
      'formal_speech': Icons.record_voice_over_rounded,
      'academic_language': Icons.school_rounded,
      'professional_language': Icons.business_rounded,
      'culture': Icons.public_rounded,
      'critical_discussion': Icons.manage_search_rounded,
      'language_mastery': Icons.workspace_premium_rounded,
      'rhetoric': Icons.campaign_rounded,
      'advanced_idioms': Icons.auto_awesome_rounded,
      'language_register': Icons.layers_rounded,
      'complex_debates': Icons.balance_rounded,
      'interpretation': Icons.translate_rounded,
      'fluency': Icons.speed_rounded,
      'level_test': Icons.verified_rounded,
    };

    return map[key] ?? Icons.menu_book_rounded;
  }
}

class _ConnectorPainter extends CustomPainter {
  final Color color;
  final bool locked;

  const _ConnectorPainter({
    required this.color,
    required this.locked,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round
      ..color = color.withValues(
        alpha: locked ? .45 : .75,
      );

    final x = size.width / 2;

    final path = Path()
      ..moveTo(x, 0)
      ..cubicTo(
        x - size.width * .10,
        size.height * .25,
        x + size.width * .10,
        size.height * .75,
        x,
        size.height,
      );

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(
    covariant _ConnectorPainter oldDelegate,
  ) {
    return oldDelegate.color != color ||
        oldDelegate.locked != locked;
  }
}
