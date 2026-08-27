import 'package:flutter/material.dart';

import '../controllers/learning_path_controller.dart';
import '../core/language/language_controller.dart';
import '../core/theme/theme_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/learning_language_controller.dart';

class LearningPathPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;

  const LearningPathPage({
    super.key,
    required this.themeController,
    required this.languageController,
  });

  @override
  State<LearningPathPage> createState() => _LearningPathPageState();
}

class _LearningPathPageState extends State<LearningPathPage> {
  late final LearningPathController _controller;

  @override
  void initState() {
    super.initState();

    _controller = LearningPathController(
      learningLanguageController:
          LearningLanguageController.instance,
    );

    _controller.addListener(_onControllerChanged);

    widget.languageController.addListener(
      _onAppLanguageChanged,
    );

    _controller.load();
  }

  @override
  void dispose() {
    _controller.removeListener(_onControllerChanged);
    _controller.dispose();

    widget.languageController.removeListener(
      _onAppLanguageChanged,
    );

    super.dispose();
  }

  void _onControllerChanged() {
    if (!mounted) {
      return;
    }

    setState(() {});
  }

  void _onAppLanguageChanged() {
    if (!mounted) {
      return;
    }

    setState(() {});
  }

  String _levelDisplayName(String level) {
    switch (level.toUpperCase()) {
      case 'PRE_A1':
        return 'Pre-A1';

      case 'A1':
        return 'A1';

      case 'A2':
        return 'A2';

      case 'B1':
        return 'B1';

      case 'B2':
        return 'B2';

      case 'C1':
        return 'C1';

      case 'C2':
        return 'C2';

      default:
        return level;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: theme.scaffoldBackgroundColor,
        elevation: 0,
        title: Text(
          _text(
            ar: 'مسار التعلّم',
            en: 'Learning Path',
            fr: 'Parcours d’apprentissage',
            es: 'Ruta de aprendizaje',
            zh: '学习路径',
            ja: '学習パス',
            ko: '학습 경로',
          ),
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: _controller.isLoading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : _controller.errorMessage != null
          ? _buildErrorState(theme)
          : _buildLearningPath(theme),
    );
  }

  Widget _buildLearningPath(ThemeData theme) {
    final lessons = _controller.lessons;

    return RefreshIndicator(
      onRefresh: _controller.refresh,
      child: lessons.isEmpty
          ? ListView(
              physics:
                  const AlwaysScrollableScrollPhysics(),
              padding:
                  const EdgeInsets.fromLTRB(
                    18,
                    8,
                    18,
                    50,
                  ),
              children: [
                _buildTopProgressCard(theme),
                const SizedBox(height: 38),
                _buildEmptyState(theme),
              ],
            )
          : ListView(
              physics:
                  const AlwaysScrollableScrollPhysics(),
              padding:
                  const EdgeInsets.fromLTRB(
                    16,
                    8,
                    16,
                    55,
                  ),
              children: [
                _buildTopProgressCard(theme),
                const SizedBox(height: 28),
                _buildPathHeader(theme),
                const SizedBox(height: 20),
                _buildLearningMap(
                  theme,
                  lessons,
                ),
              ],
            ),
    );
  }

  Widget _buildPathHeader(ThemeData theme) {
    final currentLevelName =
        _levelDisplayName(
          _controller.currentLevel,
        );

    return Padding(
      padding:
          const EdgeInsets.symmetric(horizontal: 4),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: theme
                  .colorScheme
                  .primaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.flag_rounded,
              color: theme
                  .colorScheme
                  .onPrimaryContainer,
              size: 23,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  _controller.currentLevel.isNotEmpty
                      ? _text(
                          ar:
                              'رحلتك في المستوى $currentLevelName',
                          en:
                              'Your $currentLevelName journey',
                          fr:
                              'Votre parcours $currentLevelName',
                          es:
                              'Tu recorrido $currentLevelName',
                          zh:
                              '你的 $currentLevelName 学习之旅',
                          ja:
                              '$currentLevelName の学習パス',
                          ko:
                              '$currentLevelName 학습 여정',
                        )
                      : _text(
                          ar: 'رحلتك التعليمية',
                          en:
                              'Your learning journey',
                          fr: 'Votre parcours',
                          es: 'Tu recorrido',
                          zh: '你的学习之旅',
                          ja:
                              'あなたの学習パス',
                          ko:
                              '나의 학습 여정',
                        ),
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color:
                        theme.colorScheme.onSurface,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _text(
                    ar:
                        'أكمل الدروس بالترتيب لفتح الخطوات التالية.',
                    en:
                        'Complete lessons to unlock the next steps.',
                    fr:
                        'Terminez les leçons pour débloquer les étapes suivantes.',
                    es:
                        'Completa las lecciones para desbloquear los siguientes pasos.',
                    zh:
                        '完成课程以解锁下一步。',
                    ja:
                        'レッスンを完了して次のステップを解除しましょう。',
                    ko:
                        '수업을 완료하여 다음 단계를 잠금 해제하세요.',
                  ),
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.4,
                    color:
                        theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLearningMap(
    ThemeData theme,
    List<LearningLessonModel> lessons,
  ) {
    return Column(
      children: List.generate(
        lessons.length,
        (index) {
          final lesson = lessons[index];

          final bool isLeft = index.isEven;

          return Column(
            children: [
              _buildMapLessonItem(
                theme,
                lesson,
                index,
                isLeft,
              ),
              if (index < lessons.length - 1)
                _buildPathConnector(
                  theme,
                  lesson,
                  lessons[index + 1],
                  index,
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildMapLessonItem(
    ThemeData theme,
    LearningLessonModel lesson,
    int index,
    bool isLeft,
  ) {
    final screenWidth =
        MediaQuery.of(context).size.width;

    final compact = screenWidth < 370;

    return Row(
      crossAxisAlignment:
          CrossAxisAlignment.center,
      children: [
        if (isLeft) ...[
          Expanded(
            child: _buildMapLessonCard(
              theme,
              lesson,
              index,
              isLeft,
              compact,
            ),
          ),
          const SizedBox(width: 10),
          _buildMapNode(
            theme,
            lesson,
            size: compact ? 50 : 56,
          ),
          const SizedBox(width: 2),
        ] else ...[
          const SizedBox(width: 2),
          _buildMapNode(
            theme,
            lesson,
            size: compact ? 50 : 56,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _buildMapLessonCard(
              theme,
              lesson,
              index,
              isLeft,
              compact,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildMapLessonCard(
    ThemeData theme,
    LearningLessonModel lesson,
    int index,
    bool isLeft,
    bool compact,
  ) {
    final completed = lesson.status ==
        LearningLessonStatus.completed;

    final current = lesson.status ==
        LearningLessonStatus.current;

    final unlocked = lesson.isUnlocked;

    final Color cardColor;

    if (current) {
      cardColor =
          theme.colorScheme.primaryContainer;
    } else if (completed) {
      cardColor =
          theme.colorScheme.surface;
    } else if (!unlocked) {
      cardColor = theme
          .colorScheme
          .surfaceContainerHighest
          .withValues(
            alpha: 0.55,
          );
    } else {
      cardColor =
          theme.colorScheme.surface;
    }

    return GestureDetector(
      onTap: unlocked
          ? () => _openLesson(
              lesson,
              index,
              0,
            )
          : null,
      child: AnimatedContainer(
        duration:
            const Duration(milliseconds: 220),
        padding: EdgeInsets.fromLTRB(
          compact ? 11 : 14,
          compact ? 12 : 14,
          compact ? 11 : 14,
          compact ? 12 : 14,
        ),
        decoration: BoxDecoration(
          color: cardColor,
          borderRadius:
              BorderRadius.circular(20),
          border: Border.all(
            color: current
                ? theme.colorScheme.primary
                    .withValues(alpha: 0.5)
                : theme
                    .colorScheme
                    .outlineVariant
                    .withValues(
                      alpha:
                          unlocked ? 0.9 : 0.55,
                    ),
            width: current ? 1.7 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(
                alpha:
                    theme.brightness ==
                            Brightness.dark
                        ? 0.12
                        : 0.045,
              ),
              blurRadius:
                  current ? 14 : 9,
              offset:
                  const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: isLeft
              ? [
                  _buildLessonEdgeIcon(
                    theme,
                    lesson,
                    compact,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child:
                        _buildLessonTextContent(
                      theme,
                      lesson,
                      isLeft,
                    ),
                  ),
                ]
              : [
                  Expanded(
                    child:
                        _buildLessonTextContent(
                      theme,
                      lesson,
                      isLeft,
                    ),
                  ),
                  const SizedBox(width: 10),
                  _buildLessonEdgeIcon(
                    theme,
                    lesson,
                    compact,
                  ),
                ],
        ),
      ),
    );
  }

  Widget _buildLessonEdgeIcon(
    ThemeData theme,
    LearningLessonModel lesson,
    bool compact,
  ) {
    final completed = lesson.status ==
        LearningLessonStatus.completed;

    final current = lesson.status ==
        LearningLessonStatus.current;

    final unlocked = lesson.isUnlocked;

    Color backgroundColor;
    Color iconColor;

    if (completed) {
      backgroundColor =
          Colors.green.shade600;
      iconColor = Colors.white;
    } else if (current) {
      backgroundColor =
          theme.colorScheme.primary;
      iconColor = Colors.white;
    } else if (unlocked) {
      backgroundColor =
          theme.colorScheme.primaryContainer;
      iconColor =
          theme.colorScheme.primary;
    } else {
      backgroundColor = theme
          .colorScheme
          .surfaceContainerHighest;
      iconColor =
          theme.colorScheme.onSurfaceVariant;
    }

    return AnimatedContainer(
      duration:
          const Duration(milliseconds: 220),
      width: compact ? 38 : 43,
      height: compact ? 38 : 43,
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius:
            BorderRadius.circular(13),
      ),
      child: Icon(
        completed
            ? Icons.check_rounded
            : current
            ? Icons.play_arrow_rounded
            : lesson.isTest
            ? Icons.verified_rounded
            : _topicIcon(
                lesson.topicKey,
              ),
        color: iconColor,
        size: compact ? 20 : 22,
      ),
    );
  }

  Widget _buildLessonTextContent(
    ThemeData theme,
    LearningLessonModel lesson,
    bool isLeft,
  ) {
    return Column(
      crossAxisAlignment: isLeft
          ? CrossAxisAlignment.start
          : CrossAxisAlignment.end,
      children: [
        Row(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                lesson.title,
                softWrap: true,
                textAlign: isLeft
                    ? TextAlign.left
                    : TextAlign.right,
                style: TextStyle(
                  fontSize: 14.5,
                  height: 1.3,
                  fontWeight: FontWeight.bold,
                  color: theme
                      .colorScheme
                      .onSurface,
                ),
              ),
            ),
            if (lesson.isTest) ...[
              const SizedBox(width: 6),
              _buildTestBadge(theme),
            ],
          ],
        ),
        const SizedBox(height: 7),
        Text(
          lesson.subtitle,
          softWrap: true,
          textAlign: isLeft
              ? TextAlign.left
              : TextAlign.right,
          style: TextStyle(
            fontSize: 11.5,
            height: 1.5,
            color: theme
                .colorScheme
                .onSurfaceVariant,
          ),
        ),
        if (lesson.status ==
            LearningLessonStatus.current) ...[
          const SizedBox(height: 10),
          Container(
            padding:
                const EdgeInsets.symmetric(
              horizontal: 10,
              vertical: 5,
            ),
            decoration: BoxDecoration(
              color:
                  theme.colorScheme.primary,
              borderRadius:
                  BorderRadius.circular(9),
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

  Widget _buildPathConnector(
    ThemeData theme,
    LearningLessonModel currentLesson,
    LearningLessonModel nextLesson,
    int index,
  ) {
    final currentCompleted =
        currentLesson.status ==
            LearningLessonStatus.completed;

    final nextLocked =
        nextLesson.status ==
            LearningLessonStatus.locked;

    final Color lineColor =
        currentCompleted
            ? Colors.green.shade500
            : theme.colorScheme.outlineVariant;

    return SizedBox(
      height: 34,
      child: CustomPaint(
        painter: _ConnectorPainter(
          color: lineColor,
          locked: nextLocked,
        ),
        child: const SizedBox.expand(),
      ),
    );
  }

  Widget _buildMapNode(
    ThemeData theme,
    LearningLessonModel lesson, {
    required double size,
  }) {
    final completed =
        lesson.status ==
            LearningLessonStatus.completed;

    final current =
        lesson.status ==
            LearningLessonStatus.current;

    final unlocked =
        lesson.isUnlocked;

    final Color backgroundColor;

    if (completed) {
      backgroundColor =
          Colors.green.shade600;
    } else if (current) {
      backgroundColor =
          theme.colorScheme.primary;
    } else if (unlocked) {
      backgroundColor =
          theme.colorScheme.primaryContainer;
    } else {
      backgroundColor = theme
          .colorScheme
          .surfaceContainerHighest;
    }

    final Color borderColor;

    if (completed) {
      borderColor =
          Colors.green.shade600;
    } else if (current) {
      borderColor =
          theme.colorScheme.primary;
    } else {
      borderColor =
          theme.colorScheme.outlineVariant;
    }

    return GestureDetector(
      onTap: unlocked
          ? () => _openLesson(
              lesson,
              0,
              0,
            )
          : null,
      child: AnimatedContainer(
        duration:
            const Duration(milliseconds: 250),
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: backgroundColor,
          shape: BoxShape.circle,
          border: Border.all(
            color: borderColor,
            width: current ? 3.5 : 2,
          ),
          boxShadow: current
              ? [
                  BoxShadow(
                    color: theme
                        .colorScheme
                        .primary
                        .withValues(
                          alpha: 0.28,
                        ),
                    blurRadius: 16,
                    spreadRadius: 3,
                  ),
                ]
              : [
                  BoxShadow(
                    color: Colors.black.withValues(
                      alpha:
                          theme.brightness ==
                                  Brightness.dark
                              ? 0.15
                              : 0.07,
                    ),
                    blurRadius: 7,
                    offset:
                        const Offset(0, 3),
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
              ? _topicIcon(
                  lesson.topicKey,
                )
              : Icons.lock_rounded,
          size: current ? 27 : 21,
          color: completed || current
              ? Colors.white
              : unlocked
              ? theme
                  .colorScheme
                  .primary
              : theme
                  .colorScheme
                  .onSurfaceVariant,
        ),
      ),
    );
  }

  Widget _buildTestBadge(
    ThemeData theme,
  ) {
    return Container(
      padding:
          const EdgeInsets.symmetric(
        horizontal: 7,
        vertical: 3,
      ),
      decoration: BoxDecoration(
        color: theme
            .colorScheme
            .secondaryContainer,
        borderRadius:
            BorderRadius.circular(7),
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
          color: theme
              .colorScheme
              .onSecondaryContainer,
        ),
      ),
    );
  }

  Widget _buildTopProgressCard(
    ThemeData theme,
  ) {
    final currentLevelName =
        _levelDisplayName(
      _controller.currentLevel,
    );

    final nextLevelName =
        _levelDisplayName(
      _controller.nextLevel,
    );

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primary,
            theme.colorScheme.secondary,
          ],
        ),
        borderRadius:
            BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            color: theme
                .colorScheme
                .primary
                .withValues(
                  alpha: 0.20,
                ),
            blurRadius: 20,
            offset:
                const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment:
                CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white
                      .withValues(
                    alpha: 0.18,
                  ),
                  borderRadius:
                      BorderRadius.circular(16),
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
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    Text(
                      _text(
                        ar: 'رحلة تعلّمك',
                        en:
                            'Your Learning Journey',
                        fr:
                            'Votre parcours',
                        es:
                            'Tu recorrido de aprendizaje',
                        zh:
                            '你的学习之旅',
                        ja:
                            'あなたの学習 journey',
                        ko:
                            '나의 학습 여정',
                      ),
                      softWrap: true,
                      style:
                          const TextStyle(
                        color: Colors.white,
                        fontSize: 21,
                        fontWeight:
                            FontWeight.bold,
                      ),
                    ),
                    const SizedBox(
                      height: 4,
                    ),
                    Text(
                      _text(
                        ar:
                            'تقدم خطوة بخطوة وتعلم من خلال الممارسة.',
                        en:
                            'Move step by step and learn through practice.',
                        fr:
                            'Progressez étape par étape grâce à la pratique.',
                        es:
                            'Avanza paso a paso y aprende mediante la práctica.',
                        zh:
                            '一步一步前进，通过实践学习。',
                        ja:
                            '一歩ずつ進み、実践を通して学びましょう。',
                        ko:
                            '한 단계씩 연습하며 학습하세요.',
                      ),
                      softWrap: true,
                      style:
                          const TextStyle(
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
            mainAxisAlignment:
                MainAxisAlignment
                    .spaceBetween,
            children: [
              Flexible(
                child: Text(
                  _text(
                    ar: 'تقدمك الحالي',
                    en: 'Your progress',
                    fr:
                        'Votre progression',
                    es: 'Tu progreso',
                    zh: '当前进度',
                    ja:
                        '現在の進捗',
                    ko:
                        '현재 진행률',
                  ),
                  style:
                      const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                  ),
                ),
              ),
              const SizedBox(
                width: 8,
              ),
              Text(
                '${_controller.progress.round()}%',
                style:
                    const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight:
                      FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius:
                BorderRadius.circular(20),
            child:
                LinearProgressIndicator(
              value:
                  (_controller.progress /
                          100)
                      .clamp(0, 1),
              minHeight: 9,
              backgroundColor:
                  const Color(
                0x40FFFFFF,
              ),
              valueColor:
                  const AlwaysStoppedAnimation<
                      Color>(
                Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment:
                CrossAxisAlignment.start,
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
                  softWrap: true,
                  style:
                      const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ),
              if (_controller
                  .currentLevel
                  .isNotEmpty) ...[
                const SizedBox(
                  width: 8,
                ),
                Flexible(
                  child: Container(
                    padding:
                        const EdgeInsets
                            .symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration:
                        BoxDecoration(
                      color: Colors.white
                          .withValues(
                        alpha: 0.18,
                      ),
                      borderRadius:
                          BorderRadius.circular(
                        10,
                      ),
                    ),
                    child: Text(
                      _controller
                              .nextLevel
                              .isNotEmpty
                          ? '$currentLevelName → $nextLevelName'
                          : currentLevelName,
                      textAlign:
                          TextAlign.center,
                      softWrap: true,
                      style:
                          const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight:
                            FontWeight.bold,
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

  Widget _buildErrorState(
    ThemeData theme,
  ) {
    return RefreshIndicator(
      onRefresh: _controller.refresh,
      child: ListView(
        physics:
            const AlwaysScrollableScrollPhysics(),
        padding:
            const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 80),
          Icon(
            Icons.cloud_off_rounded,
            size: 64,
            color: theme
                .colorScheme
                .onSurfaceVariant,
          ),
          const SizedBox(height: 18),
          Text(
            _text(
              ar:
                  'تعذر تحميل مسار التعلم',
              en:
                  'Could not load the learning path',
              fr:
                  'Impossible de charger le parcours',
              es:
                  'No se pudo cargar la ruta de aprendizaje',
              zh:
                  '无法加载学习路径',
              ja:
                  '学習パスを読み込めませんでした',
              ko:
                  '학습 경로를 불러오지 못했습니다',
            ),
            textAlign: TextAlign.center,
            style:
                const TextStyle(
              fontSize: 20,
              fontWeight:
                  FontWeight.bold,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            _controller.errorMessage ?? '',
            textAlign:
                TextAlign.center,
            style: TextStyle(
              color: theme
                  .colorScheme
                  .onSurfaceVariant,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 24),
          Center(
            child:
                FilledButton.icon(
              onPressed:
                  _controller.refresh,
              icon: const Icon(
                Icons.refresh_rounded,
              ),
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

  Widget _buildEmptyState(
    ThemeData theme,
  ) {
    return Column(
      children: [
        Icon(
          Icons.route_outlined,
          size: 60,
          color: theme
              .colorScheme
              .onSurfaceVariant,
        ),
        const SizedBox(height: 16),
        Text(
          _text(
            ar:
                'لا توجد دروس متاحة حاليًا',
            en:
                'No lessons are currently available',
            fr:
                'Aucune leçon disponible actuellement',
            es:
                'No hay lecciones disponibles actualmente',
            zh:
                '目前没有可用课程',
            ja:
                '現在利用できるレッスンはありません',
            ko:
                '현재 이용 가능한 수업이 없습니다',
          ),
          textAlign:
              TextAlign.center,
          style:
              const TextStyle(
            fontSize: 18,
            fontWeight:
                FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          _text(
            ar:
                'اسحب للأسفل لتحديث المسار.',
            en:
                'Pull down to refresh the path.',
            fr:
                'Tirez vers le bas pour actualiser.',
            es:
                'Desliza hacia abajo para actualizar.',
            zh:
                '下拉以刷新学习路径。',
            ja:
                '下に引っ張って更新してください。',
            ko:
                '아래로 당겨 새로고침하세요.',
          ),
          textAlign:
              TextAlign.center,
          style: TextStyle(
            color: theme
                .colorScheme
                .onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  void _openLesson(
    LearningLessonModel lesson,
    int unitIndex,
    int lessonIndex,
  ) {
    ScaffoldMessenger.of(context)
        .showSnackBar(
      SnackBar(
        content: Text(
          '${lesson.title} • ${_controller.currentLevel.isNotEmpty ? _levelDisplayName(_controller.currentLevel) : ''}',
        ),
        behavior:
            SnackBarBehavior.floating,
      ),
    );
  }

  String _text({
    required String ar,
    required String en,
    required String fr,
    required String es,
    required String zh,
    required String ja,
    required String ko,
  }) {
    switch (widget
        .languageController
        .locale
        .languageCode) {
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

  String _learningLanguageLabel() {
    final languageName =
        _learningLanguageName();

    return _text(
      ar:
          'اللغة المستهدفة: $languageName',
      en:
          'Target language: $languageName',
      fr:
          'Langue cible : $languageName',
      es:
          'Idioma objetivo: $languageName',
      zh:
          '目标语言：$languageName',
      ja:
          '学習言語：$languageName',
      ko:
          '학습 언어: $languageName',
    );
  }

  String _learningLanguageName() {
    switch (_controller.learningLanguage) {
      case 'tr':
        return _text(
          ar: 'التركية',
          en: 'Turkish',
          fr: 'Turc',
          es: 'Turco',
          zh: '土耳其语',
          ja: 'トルコ語',
          ko: '터키어',
        );

      case 'en':
        return _text(
          ar: 'الإنجليزية',
          en: 'English',
          fr: 'Anglais',
          es: 'Inglés',
          zh: '英语',
          ja: '英語',
          ko: '영어',
        );

      case 'fr':
        return _text(
          ar: 'الفرنسية',
          en: 'French',
          fr: 'Français',
          es: 'Francés',
          zh: '法语',
          ja: 'フランス語',
          ko: '프랑스어',
        );

      case 'es':
        return _text(
          ar: 'الإسبانية',
          en: 'Spanish',
          fr: 'Espagnol',
          es: 'Español',
          zh: '西班牙语',
          ja: 'スペイン語',
          ko: '스페イン어',
        );

      case 'de':
        return _text(
          ar: 'الألمانية',
          en: 'German',
          fr: 'Allemand',
          es: 'Alemán',
          zh: '德语',
          ja: 'ドイツ語',
          ko: '독일어',
        );

      case 'it':
        return _text(
          ar: 'الإيطالية',
          en: 'Italian',
          fr: 'Italien',
          es: 'Italiano',
          zh: '意大利语',
          ja: 'イタリア語',
          ko: '이탈리아어',
        );

      case 'pt':
        return _text(
          ar: 'البرتغالية',
          en: 'Portuguese',
          fr: 'Portugais',
          es: 'Portugués',
          zh: '葡萄牙语',
          ja: 'ポルトガル語',
          ko: '포르투갈어',
        );

      case 'ja':
        return _text(
          ar: 'اليابانية',
          en: 'Japanese',
          fr: 'Japonais',
          es: 'Japonés',
          zh: '日语',
          ja: '日本語',
          ko: '일본어',
        );

      case 'ko':
        return _text(
          ar: 'الكورية',
          en: 'Korean',
          fr: 'Coréen',
          es: 'Coreano',
          zh: '韩语',
          ja: '韓国語',
          ko: '한국어',
        );

      case 'zh':
        return _text(
          ar: 'الصينية',
          en: 'Chinese',
          fr: 'Chinois',
          es: 'Chino',
          zh: '中文',
          ja: '中国語',
          ko: '중국어',
        );

      default:
        return _controller
                .learningLanguage
                .isEmpty
            ? _text(
                ar: 'غير محددة',
                en: 'Not specified',
                fr: 'Non spécifiée',
                es: 'No especificada',
                zh: '未指定',
                ja: '未指定',
                ko: '지정되지 않음',
              )
            : _controller
                .learningLanguage
                .toUpperCase();
    }
  }

  IconData _topicIcon(
    String topicKey,
  ) {
    switch (topicKey) {
      case 'sounds_and_letters':
        return Icons
            .record_voice_over_rounded;

      case 'basic_greetings':
        return Icons
            .waving_hand_rounded;

      case 'numbers_0_10':
        return Icons.looks_one_rounded;

      case 'colors':
        return Icons.palette_rounded;

      case 'family_basics':
        return Icons.family_restroom_rounded;

      case 'everyday_objects':
        return Icons.inventory_2_rounded;

      case 'very_basic_phrases':
        return Icons.chat_rounded;

      case 'alphabet':
        return Icons.abc_rounded;

      case 'basic_words':
        return Icons.menu_book_rounded;

      case 'numbers':
        return Icons.numbers_rounded;

      case 'greetings':
        return Icons.waving_hand_rounded;

      case 'introductions':
        return Icons.person_add_rounded;

      case 'family':
        return Icons.family_restroom_rounded;

      case 'simple_sentences':
        return Icons.short_text_rounded;

      case 'daily_life':
        return Icons.today_rounded;

      case 'past_tense':
        return Icons.history_rounded;

      case 'future':
        return Icons.event_available_rounded;

      case 'shopping':
        return Icons.shopping_bag_rounded;

      case 'travel':
        return Icons.flight_rounded;

      case 'health':
        return Icons
            .health_and_safety_rounded;

      case 'describing_people':
        return Icons
            .person_search_rounded;

      case 'daily_conversations':
        return Icons
            .chat_bubble_rounded;

      case 'telling_stories':
        return Icons
            .auto_stories_rounded;

      case 'work':
        return Icons.work_rounded;

      case 'opinions':
        return Icons.forum_rounded;

      case 'social_situations':
        return Icons.people_alt_rounded;

      case 'media':
        return Icons.movie_rounded;

      case 'extended_conversations':
        return Icons
            .record_voice_over_rounded;

      case 'debates':
        return Icons.gavel_rounded;

      case 'arguments':
        return Icons.forum_rounded;

      case 'complex_vocabulary':
        return Icons
            .library_books_rounded;

      case 'idioms':
        return Icons.format_quote_rounded;

      case 'workplace':
        return Icons
            .business_center_rounded;

      case 'problem_solving':
        return Icons
            .psychology_rounded;

      case 'presentations':
        return Icons
            .present_to_all_rounded;

      case 'language_nuance':
        return Icons.tune_rounded;

      case 'advanced_grammar':
        return Icons.rule_rounded;

      case 'formal_speech':
        return Icons
            .record_voice_over_rounded;

      case 'academic_language':
        return Icons.school_rounded;

      case 'professional_language':
        return Icons.business_rounded;

      case 'culture':
        return Icons.public_rounded;

      case 'critical_discussion':
        return Icons
            .manage_search_rounded;

      case 'language_mastery':
        return Icons
            .workspace_premium_rounded;

      case 'rhetoric':
        return Icons.campaign_rounded;

      case 'advanced_idioms':
        return Icons.auto_awesome_rounded;

      case 'language_register':
        return Icons.layers_rounded;

      case 'complex_debates':
        return Icons.balance_rounded;

      case 'interpretation':
        return Icons.translate_rounded;

      case 'fluency':
        return Icons.speed_rounded;

      case 'level_test':
        return Icons.verified_rounded;

      default:
        return Icons.menu_book_rounded;
    }
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
  void paint(
    Canvas canvas,
    Size size,
  ) {
    final double centerX =
        size.width / 2;

    final paint = Paint()
      ..style =
          PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap =
          StrokeCap.round
      ..color = locked
          ? color.withValues(
              alpha: 0.45,
            )
          : color.withValues(
              alpha: 0.75,
            );

    final path = Path();

    path.moveTo(
      centerX,
      0,
    );

    path.cubicTo(
      centerX -
          size.width * 0.10,
      size.height * 0.25,
      centerX +
          size.width * 0.10,
      size.height * 0.75,
      centerX,
      size.height,
    );

    canvas.drawPath(
      path,
      paint,
    );

    if (locked) {
      final dotPaint = Paint()
        ..style =
            PaintingStyle.fill
        ..color = color.withValues(
          alpha: 0.5,
        );

      canvas.drawCircle(
        Offset(
          centerX,
          size.height / 2,
        ),
        3,
        dotPaint,
      );
    }
  }

  @override
  bool shouldRepaint(
    covariant _ConnectorPainter oldDelegate,
  ) {
    return oldDelegate.color != color ||
        oldDelegate.locked !=
            locked;
  }
}