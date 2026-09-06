import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import 'lesson_learn_page.dart';
import 'lesson_page.dart';
import 'lesson_practice_page.dart';

class LessonJourneyPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;

  const LessonJourneyPage({
    super.key,
    required this.lesson,
    required this.languageController,
  });

  @override
  State<LessonJourneyPage> createState() => _LessonJourneyPageState();
}

class _LessonJourneyPageState extends State<LessonJourneyPage> {
  bool _learnCompleted = false;
  bool _teachingCompleted = false;
  bool _practiceCompleted = false;

  String _locale() => widget.languageController.locale.languageCode;

  String _t({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
  }) {
    switch (_locale()) {
      case 'fr':
        return fr ?? en;
      case 'es':
        return es ?? en;
      case 'de':
        return de ?? en;
      case 'ar':
      default:
        return ar;
    }
  }

  Future<void> _openLearn() async {
    final completed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LessonLearnPage(
          lesson: widget.lesson,
          languageController: widget.languageController,
        ),
      ),
    );

    if (!mounted) return;
    if (completed == true) setState(() => _learnCompleted = true);
  }

  Future<void> _openTeaching() async {
    final completed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LessonPage(
          lesson: widget.lesson,
          languageController: widget.languageController,
        ),
      ),
    );

    if (!mounted) return;
    if (completed == true) setState(() => _teachingCompleted = true);
  }

  Future<void> _openPractice() async {
    final completed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LessonPracticePage(
          lesson: widget.lesson,
          languageController: widget.languageController,
        ),
      ),
    );

    if (!mounted) return;
    if (completed == true) {
      setState(() => _practiceCompleted = true);
      await Future<void>.delayed(const Duration(milliseconds: 250));
      if (mounted) Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final completedStages = [
      _learnCompleted,
      _teachingCompleted,
      _practiceCompleted,
    ].where((value) => value).length;
    final journeyProgress = completedStages / 3;
    final canTeaching = _learnCompleted;
    final canPractice = _teachingCompleted;

    return Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              theme.colorScheme.primary.withOpacity(.10),
              theme.scaffoldBackgroundColor,
            ],
          ),
        ),
        child: SafeArea(
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 8, 20, 8),
                  child: Row(
                    children: [
                      IconButton(
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.arrow_back_rounded),
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _t(
                                ar: 'الدرس ${widget.lesson.lessonOrder}',
                                en: 'Lesson ${widget.lesson.lessonOrder}',
                                fr: 'Leçon ${widget.lesson.lessonOrder}',
                                es: 'Lección ${widget.lesson.lessonOrder}',
                                de: 'Lektion ${widget.lesson.lessonOrder}',
                              ),
                              style: TextStyle(
                                color: theme.colorScheme.primary,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              widget.lesson.title,
                              style: theme.textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 10, 20, 24),
                  child: Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(28),
                      color: theme.colorScheme.primary,
                      boxShadow: [
                        BoxShadow(
                          color: theme.colorScheme.primary.withOpacity(.22),
                          blurRadius: 28,
                          offset: const Offset(0, 13),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 54,
                              height: 54,
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(.16),
                                borderRadius: BorderRadius.circular(18),
                              ),
                              child: const Icon(
                                Icons.route_rounded,
                                color: Colors.white,
                                size: 29,
                              ),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Text(
                                _t(
                                  ar: 'مسار الدرس',
                                  en: 'Lesson journey',
                                  fr: 'Parcours de la leçon',
                                  es: 'Ruta de la lección',
                                  de: 'Lernweg der Lektion',
                                ),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                            Text(
                              '$completedStages/3',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                                fontSize: 16,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _t(
                            ar: 'ثلاث مراحل منفصلة. أكمل كل مرحلة ثم عد إلى المسار لفتح المرحلة التالية.',
                            en: 'Three separate stages. Complete each stage, then return to the journey to unlock the next one.',
                            fr: 'Trois étapes distinctes. Terminez chaque étape pour débloquer la suivante.',
                            es: 'Tres etapas separadas. Completa cada etapa para desbloquear la siguiente.',
                            de: 'Drei getrennte Phasen. Schließe jede Phase ab, um die nächste freizuschalten.',
                          ),
                          style: const TextStyle(
                            color: Colors.white70,
                            height: 1.45,
                          ),
                        ),
                        const SizedBox(height: 18),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(99),
                          child: LinearProgressIndicator(
                            value: journeyProgress,
                            minHeight: 9,
                            backgroundColor: Colors.white.withOpacity(.18),
                            valueColor: const AlwaysStoppedAnimation(Colors.white),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '${(journeyProgress * 100).round()}%',
                          style: const TextStyle(
                            color: Colors.white70,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 34),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    _StageNode(
                      number: '01',
                      icon: Icons.auto_stories_rounded,
                      title: _t(
                        ar: 'التعلّم التفاعلي',
                        en: 'Interactive learning',
                        fr: 'Apprentissage interactif',
                        es: 'Aprendizaje interactivo',
                        de: 'Interaktives Lernen',
                      ),
                      description: _t(
                        ar: 'تعلّم جمل الدرس: شاهد، افهم، أجب، ثم انتقل إلى الجملة التالية.',
                        en: 'Learn the lesson sentences: see, understand, answer, then move to the next sentence.',
                        fr: 'Apprenez les phrases avec explication et questions.',
                        es: 'Aprende las frases con explicación y preguntas.',
                        de: 'Lerne die Sätze mit Erklärung und Fragen.',
                      ),
                      enabled: true,
                      completed: _learnCompleted,
                      color: theme.colorScheme.primary,
                      action: _t(
                        ar: _learnCompleted ? 'مراجعة المرحلة' : 'ابدأ المرحلة 1',
                        en: _learnCompleted ? 'Review stage' : 'Start stage 1',
                      ),
                      lockedText: '',
                      onTap: _openLearn,
                    ),
                    _Connector(
                      completed: _learnCompleted,
                      color: theme.colorScheme.primary,
                    ),
                    _StageNode(
                      number: '02',
                      icon: Icons.psychology_rounded,
                      title: _t(
                        ar: 'التعليم مع الذكاء الاصطناعي',
                        en: 'AI teaching',
                        fr: 'Enseignement avec l’IA',
                        es: 'Enseñanza con IA',
                        de: 'Lernen mit KI',
                      ),
                      description: _t(
                        ar: 'مدرّس ذكي يقودك، يصحح أخطاءك، يعطيك تلميحات ويقرر متى أصبحت جاهزًا.',
                        en: 'An AI tutor guides you, corrects mistakes, gives hints, and decides when you are ready.',
                        fr: 'Un tuteur IA vous guide et corrige vos erreurs.',
                        es: 'Un tutor de IA te guía y corrige tus errores.',
                        de: 'Ein KI-Tutor führt dich und korrigiert deine Fehler.',
                      ),
                      enabled: canTeaching,
                      completed: _teachingCompleted,
                      color: const Color(0xFF7C4DFF),
                      action: _t(
                        ar: _teachingCompleted ? 'مراجعة المرحلة' : 'ابدأ المرحلة 2',
                        en: _teachingCompleted ? 'Review stage' : 'Start stage 2',
                      ),
                      lockedText: _t(
                        ar: 'أكمل المرحلة 1 لفتح هذه المرحلة',
                        en: 'Complete stage 1 to unlock this stage',
                      ),
                      onTap: _openTeaching,
                    ),
                    _Connector(
                      completed: _teachingCompleted,
                      color: const Color(0xFF7C4DFF),
                    ),
                    _StageNode(
                      number: '03',
                      icon: Icons.forum_rounded,
                      title: _t(
                        ar: 'الممارسة التفاعلية',
                        en: 'Interactive practice',
                        fr: 'Pratique interactive',
                        es: 'Práctica interactiva',
                        de: 'Interaktives Üben',
                      ),
                      description: _t(
                        ar: 'محادثة طبيعية مع الذكاء الاصطناعي تستخدم جمل الدرس في سياقات مختلفة.',
                        en: 'A natural AI conversation that uses the lesson sentences in different contexts.',
                        fr: 'Une conversation naturelle avec l’IA utilisant les phrases de la leçon.',
                        es: 'Una conversación natural con IA usando las frases de la lección.',
                        de: 'Ein natürliches Gespräch mit KI mit den Sätzen der Lektion.',
                      ),
                      enabled: canPractice,
                      completed: _practiceCompleted,
                      color: const Color(0xFF00A88F),
                      action: _practiceCompleted
                          ? _t(ar: 'مكتملة', en: 'Completed')
                          : _t(ar: 'ابدأ المرحلة 3', en: 'Start stage 3'),
                      lockedText: _t(
                        ar: 'أكمل المرحلة 2 لفتح هذه المرحلة',
                        en: 'Complete stage 2 to unlock this stage',
                      ),
                      onTap: _openPractice,
                    ),
                  ]),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Connector extends StatelessWidget {
  final bool completed;
  final Color color;

  const _Connector({required this.completed, required this.color});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 28,
      child: Align(
        alignment: AlignmentDirectional.centerStart,
        child: Container(
          width: 3,
          margin: const EdgeInsetsDirectional.only(start: 39),
          decoration: BoxDecoration(
            color: completed
                ? color
                : Theme.of(context).colorScheme.outlineVariant,
            borderRadius: BorderRadius.circular(99),
          ),
        ),
      ),
    );
  }
}

class _StageNode extends StatelessWidget {
  final String number;
  final IconData icon;
  final String title;
  final String description;
  final bool enabled;
  final bool completed;
  final Color color;
  final String action;
  final String lockedText;
  final VoidCallback onTap;

  const _StageNode({
    required this.number,
    required this.icon,
    required this.title,
    required this.description,
    required this.enabled,
    required this.completed,
    required this.color,
    required this.action,
    required this.lockedText,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurface.withOpacity(.62);
    final borderColor = enabled
        ? color.withOpacity(.28)
        : theme.colorScheme.outlineVariant.withOpacity(.75);

    return AnimatedOpacity(
      duration: const Duration(milliseconds: 180),
      opacity: enabled ? 1 : .58,
      child: Material(
        color: theme.colorScheme.surface,
        elevation: enabled ? 1.5 : 0,
        shadowColor: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(26),
        child: InkWell(
          onTap: enabled ? onTap : null,
          borderRadius: BorderRadius.circular(26),
          child: Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: borderColor),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Stack(
                  alignment: Alignment.center,
                  children: [
                    Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        color: color.withOpacity(.12),
                        borderRadius: BorderRadius.circular(21),
                      ),
                      child: Icon(
                        completed
                            ? Icons.check_rounded
                            : enabled
                                ? icon
                                : Icons.lock_rounded,
                        color: color,
                        size: 29,
                      ),
                    ),
                    Positioned(
                      bottom: -2,
                      right: -2,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surface,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: borderColor),
                        ),
                        child: Text(
                          number,
                          style: TextStyle(
                            color: color,
                            fontSize: 9,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 15),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              style: theme.textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                          Icon(
                            completed
                                ? Icons.check_circle_rounded
                                : enabled
                                    ? Icons.arrow_forward_ios_rounded
                                    : Icons.lock_outline_rounded,
                            size: 19,
                            color: completed ? color : muted,
                          ),
                        ],
                      ),
                      const SizedBox(height: 7),
                      Text(
                        description,
                        style: TextStyle(color: muted, height: 1.45),
                      ),
                      const SizedBox(height: 15),
                      Text(
                        completed
                            ? '✓ ${_completedLabel(context)}'
                            : enabled
                                ? action
                                : lockedText,
                        style: TextStyle(
                          color: enabled || completed ? color : muted,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _completedLabel(BuildContext context) {
    // Keep this independent from the theme so dark mode never changes the
    // language of the UI.
    final locale = Localizations.localeOf(context).languageCode;
    switch (locale) {
      case 'ar':
        return 'مكتملة';
      case 'fr':
        return 'Terminée';
      case 'es':
        return 'Completada';
      case 'de':
        return 'Abgeschlossen';
      default:
        return 'Completed';
    }
  }
}
