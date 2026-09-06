import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../services/api/api_service.dart';
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
  final ApiService _api = ApiService();

  bool _loading = true;
  String? _error;
  String _learnStatus = 'available';
  String _teachingStatus = 'locked';
  String _practiceStatus = 'locked';

  String _locale() => widget.languageController.locale.languageCode;

  String _t({required String ar, required String en, String? fr, String? es, String? de}) {
    switch (_locale()) {
      case 'fr': return fr ?? en;
      case 'es': return es ?? en;
      case 'de': return de ?? en;
      case 'ar':
      default: return ar;
    }
  }

  bool get _learnCompleted => _learnStatus == 'completed';
  bool get _teachingCompleted => _teachingStatus == 'completed';
  bool get _practiceCompleted => _practiceStatus == 'completed';

  Future<void> _loadStages() async {
    setState(() { _loading = true; _error = null; });
    try {
      final data = await _api.getLessonStages(lessonId: widget.lesson.id);
      final stages = data['stages'] is Map
          ? Map<String, dynamic>.from(data['stages'] as Map)
          : <String, dynamic>{};
      String readStatus(String key, String fallback) {
        final raw = stages[key];
        return raw is Map && raw['status'] != null ? raw['status'].toString() : fallback;
      }
      if (!mounted) return;
      setState(() {
        _learnStatus = readStatus('learn', 'available');
        _teachingStatus = readStatus('teaching', _learnCompleted ? 'available' : 'locked');
        _practiceStatus = readStatus('practice', _teachingCompleted ? 'available' : 'locked');
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = _t(ar: 'تعذر تحميل حالة مراحل الدرس.', en: 'Could not load the lesson stage status.');
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _loadStages();
  }

  Future<void> _saveStage(String stage, {String? conversationId}) async {
    await _api.completeLessonStage(
      lessonId: widget.lesson.id,
      stage: stage,
      conversationId: conversationId,
    );
    await _loadStages();
  }

  Future<void> _openLearn() async {
    final completed = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (_) => LessonLearnPage(lesson: widget.lesson, languageController: widget.languageController),
    ));
    if (!mounted || completed != true) return;
    try {
      await _saveStage('learn');
    } catch (_) {
      if (!mounted) return;
      _showSaveError();
    }
  }

  Future<void> _openTeaching() async {
    if (!_learnCompleted) return;
    final completed = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (_) => LessonPage(lesson: widget.lesson, languageController: widget.languageController),
    ));
    if (!mounted || completed != true) return;
    try {
      await _saveStage('teaching');
    } catch (_) {
      if (!mounted) return;
      _showSaveError();
    }
  }

  Future<void> _openPractice() async {
    if (!_teachingCompleted) return;
    final completed = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (_) => LessonPracticePage(lesson: widget.lesson, languageController: widget.languageController),
    ));
    if (!mounted || completed != true) return;
    try {
      await _saveStage('practice');
      if (mounted && _practiceCompleted) {
        await Future<void>.delayed(const Duration(milliseconds: 250));
        if (mounted) Navigator.of(context).pop(true);
      }
    } catch (_) {
      if (!mounted) return;
      _showSaveError();
    }
  }

  void _showSaveError() {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(_t(
        ar: 'تعذر حفظ حالة المرحلة على الخادم.',
        en: 'Could not save the stage status on the server.',
      )),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final completedCount = [_learnCompleted, _teachingCompleted, _practiceCompleted].where((v) => v).length;
    final progress = completedCount / 3;

    return Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [theme.colorScheme.primary.withValues(alpha: .10), theme.scaffoldBackgroundColor],
          ),
        ),
        child: SafeArea(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : CustomScrollView(
                  slivers: [
                    SliverToBoxAdapter(child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 8, 20, 8),
                      child: Row(children: [
                        IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.arrow_back_rounded)),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(_t(ar: 'الدرس ${widget.lesson.lessonOrder}', en: 'Lesson ${widget.lesson.lessonOrder}', fr: 'Leçon ${widget.lesson.lessonOrder}', es: 'Lección ${widget.lesson.lessonOrder}', de: 'Lektion ${widget.lesson.lessonOrder}'), style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 3),
                          Text(widget.lesson.title, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900)),
                        ])),
                        IconButton(onPressed: _loadStages, icon: const Icon(Icons.refresh_rounded)),
                      ]),
                    )),
                    if (_error != null) SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.fromLTRB(20, 8, 20, 0), child: Text(_error!, style: TextStyle(color: theme.colorScheme.error)))),
                    SliverToBoxAdapter(child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 10, 20, 24),
                      child: Container(
                        padding: const EdgeInsets.all(22),
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(28), color: theme.colorScheme.primary, boxShadow: [BoxShadow(color: theme.colorScheme.primary.withValues(alpha: .22), blurRadius: 28, offset: const Offset(0, 13))]),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [const Icon(Icons.route_rounded, color: Colors.white, size: 30), const SizedBox(width: 14), Expanded(child: Text(_t(ar: 'مسار الدرس', en: 'Lesson journey', fr: 'Parcours de la leçon', es: 'Ruta de la lección', de: 'Lernweg der Lektion'), style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900))), Text('$completedCount/3', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))]),
                          const SizedBox(height: 16),
                          Text(_t(ar: 'أكمل المراحل بالترتيب. حالة كل مرحلة محفوظة على الخادم، لذلك تبقى معك عند إعادة فتح الدرس.', en: 'Complete the stages in order. Each stage is saved on the server and remains available when you reopen the lesson.'), style: const TextStyle(color: Colors.white70, height: 1.45)),
                          const SizedBox(height: 18),
                          ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: progress, minHeight: 9, backgroundColor: Colors.white.withValues(alpha: .18), valueColor: const AlwaysStoppedAnimation(Colors.white))),
                          const SizedBox(height: 8),
                          Text('${(progress * 100).round()}%', style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.w800)),
                        ]),
                      ),
                    )),
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 34),
                      sliver: SliverList.list(children: [
                        _StageCard(number: '01', icon: Icons.auto_stories_rounded, color: theme.colorScheme.primary, title: _t(ar: 'التعلّم التفاعلي', en: 'Interactive learning', fr: 'Apprentissage interactif', es: 'Aprendizaje interactivo', de: 'Interaktives Lernen'), description: _t(ar: 'تعلّم جمل الدرس من خلال الفهم والأسئلة والتفاعل.', en: 'Learn the lesson sentences through understanding, questions, and interaction.'), status: _learnStatus, action: _learnCompleted ? _t(ar: 'مراجعة المرحلة', en: 'Review stage') : _t(ar: 'ابدأ المرحلة 1', en: 'Start stage 1'), onTap: _openLearn),
                        _Connector(completed: _learnCompleted),
                        _StageCard(number: '02', icon: Icons.psychology_rounded, color: const Color(0xFF7C4DFF), title: _t(ar: 'التعليم مع الذكاء الاصطناعي', en: 'AI teaching', fr: 'Enseignement avec l’IA', es: 'Enseñanza con IA', de: 'Lernen mit KI'), description: _t(ar: 'مدرّس ذكي يشرح، يصحح، يعطي تلميحات ويقيّم استعدادك.', en: 'An AI tutor teaches, corrects, gives hints, and evaluates your readiness.'), status: _teachingStatus, action: _teachingCompleted ? _t(ar: 'مراجعة المرحلة', en: 'Review stage') : _t(ar: 'ابدأ المرحلة 2', en: 'Start stage 2'), lockedText: _t(ar: 'أكمل المرحلة 1 لفتح هذه المرحلة', en: 'Complete stage 1 to unlock this stage'), onTap: _openTeaching),
                        _Connector(completed: _teachingCompleted),
                        _StageCard(number: '03', icon: Icons.forum_rounded, color: const Color(0xFF00A88F), title: _t(ar: 'الممارسة التفاعلية', en: 'Interactive practice', fr: 'Pratique interactive', es: 'Práctica interactiva', de: 'Interaktives Üben'), description: _t(ar: 'استخدم أهداف الدرس في محادثة طبيعية مع الذكاء الاصطناعي.', en: 'Use the lesson goals in a natural conversation with AI.'), status: _practiceStatus, action: _practiceCompleted ? _t(ar: 'مكتملة', en: 'Completed') : _t(ar: 'ابدأ المرحلة 3', en: 'Start stage 3'), lockedText: _t(ar: 'أكمل المرحلة 2 لفتح هذه المرحلة', en: 'Complete stage 2 to unlock this stage'), onTap: _openPractice),
                      ]),
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
  const _Connector({required this.completed});
  @override
  Widget build(BuildContext context) => SizedBox(height: 28, child: Align(alignment: AlignmentDirectional.centerStart, child: Container(width: 3, margin: const EdgeInsetsDirectional.only(start: 39), decoration: BoxDecoration(color: completed ? Theme.of(context).colorScheme.primary : Theme.of(context).colorScheme.outlineVariant, borderRadius: BorderRadius.circular(99)))));
}

class _StageCard extends StatelessWidget {
  final String number, title, description, status, action;
  final IconData icon;
  final Color color;
  final String? lockedText;
  final VoidCallback onTap;

  const _StageCard({required this.number, required this.icon, required this.color, required this.title, required this.description, required this.status, required this.action, this.lockedText, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final enabled = status != 'locked';
    final completed = status == 'completed';
    final borderColor = enabled ? color.withValues(alpha: .28) : theme.colorScheme.outlineVariant.withValues(alpha: .75);
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 180), opacity: enabled ? 1 : .58,
      child: Material(color: theme.colorScheme.surface, elevation: enabled ? 1.5 : 0, borderRadius: BorderRadius.circular(26), child: InkWell(onTap: enabled ? onTap : null, borderRadius: BorderRadius.circular(26), child: Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(borderRadius: BorderRadius.circular(26), border: Border.all(color: borderColor)), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(width: 64, height: 64, decoration: BoxDecoration(color: color.withValues(alpha: .12), borderRadius: BorderRadius.circular(21)), child: Icon(completed ? Icons.check_rounded : enabled ? icon : Icons.lock_rounded, color: color, size: 29)),
        const SizedBox(width: 15),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Text(number, style: TextStyle(color: color, fontWeight: FontWeight.w900, letterSpacing: 1.2)), const SizedBox(width: 9), Expanded(child: Text(title, style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900)))]),
          const SizedBox(height: 7), Text(description, style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: .68), height: 1.4)),
          const SizedBox(height: 13),
          if (!enabled && lockedText != null) Text(lockedText!, style: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: .58), fontWeight: FontWeight.w700)) else FilledButton.tonal(onPressed: onTap, child: Text(action)),
        ])),
      ]))))),
    );
  }
}
