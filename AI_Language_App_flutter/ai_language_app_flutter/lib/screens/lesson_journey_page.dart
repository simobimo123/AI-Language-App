import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import 'lesson_learn_page.dart';
import 'lesson_page.dart';

class LessonJourneyPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;

  const LessonJourneyPage({super.key, required this.lesson, required this.languageController});

  @override
  State<LessonJourneyPage> createState() => _LessonJourneyPageState();
}

class _LessonJourneyPageState extends State<LessonJourneyPage> {
  bool _learnCompleted = false;
  bool _teachingCompleted = false;

  String _t(String ar, String en) => widget.languageController.locale.languageCode == 'ar' ? ar : en;

  Future<void> _openLearn() async {
    final completed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => LessonLearnPage(lesson: widget.lesson, languageController: widget.languageController)));
    if (completed == true && mounted) setState(() => _learnCompleted = true);
  }

  Future<void> _openTeaching() async {
    final completed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => LessonPage(lesson: widget.lesson, languageController: widget.languageController)));
    if (completed == true && mounted) setState(() => _teachingCompleted = true);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final progress = widget.lesson.progress.clamp(0, 1).toDouble();
    final canTeach = _learnCompleted || widget.lesson.progress >= .33 || widget.lesson.isCompleted;
    final canPractice = _teachingCompleted;

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [theme.colorScheme.primary.withOpacity(.12), theme.scaffoldBackgroundColor])),
        child: SafeArea(
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.fromLTRB(12, 10, 20, 12), child: Row(children: [IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.arrow_back_rounded)), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(_t('الدرس ${widget.lesson.lessonOrder}', 'Lesson ${widget.lesson.lessonOrder}'), style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.w800)), const SizedBox(height: 3), Text(widget.lesson.title, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900))]))]))),
              SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.fromLTRB(20, 8, 20, 22), child: Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(borderRadius: BorderRadius.circular(28), color: theme.colorScheme.primary, boxShadow: [BoxShadow(color: theme.colorScheme.primary.withOpacity(.20), blurRadius: 26, offset: const Offset(0, 12))]), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Container(width: 52, height: 52, decoration: BoxDecoration(color: Colors.white.withOpacity(.16), borderRadius: BorderRadius.circular(18)), child: const Icon(Icons.route_rounded, color: Colors.white, size: 28)), const SizedBox(width: 14), Expanded(child: Text(_t('ثلاث مراحل، هدف واحد', 'Three stages, one goal'), style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)))]), const SizedBox(height: 16), Text(_t('نتعلم الجمل، نفهمها مع المدرّس، ثم نستخدمها في محادثة مرتبطة بالدرس.', 'Learn the sentences, understand them with your tutor, then use them naturally in the same lesson.'), style: const TextStyle(color: Colors.white, height: 1.45)), const SizedBox(height: 18), ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: progress, minHeight: 8, backgroundColor: Colors.white.withOpacity(.18), valueColor: const AlwaysStoppedAnimation(Colors.white))), const SizedBox(height: 7), Text('${(progress * 100).round()}%', style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.w800))])))),
              SliverPadding(padding: const EdgeInsets.fromLTRB(20, 0, 20, 30), sliver: SliverList(delegate: SliverChildListDelegate([
                _AxisCard(number: '01', icon: Icons.auto_stories_rounded, color: theme.colorScheme.primary, title: _t('التعلّم التفاعلي', 'Interactive learning'), subtitle: _t('شرح + أسئلة + تطبيق في نفس التجربة التعليمية.', 'Teaching + questions + guided practice in one learning experience.'), enabled: true, done: _learnCompleted, action: _t('ابدأ التعلّم', 'Start learning'), locked: '', onTap: _openLearn),
                const SizedBox(height: 14),
                _AxisCard(number: '02', icon: Icons.psychology_rounded, color: const Color(0xFF7C4DFF), title: _t('التعليم مع الذكاء الاصطناعي', 'AI teaching'), subtitle: _t('مدرّس ذكي يعلّم جمل هذا الدرس ويصحح أخطاءك.', 'An AI tutor teaches this lesson and gives personalized correction.'), enabled: canTeach, done: _teachingCompleted, action: _t('ابدأ مع AI', 'Learn with AI'), locked: _t('أكمل المحور الأول أولًا', 'Complete stage one first'), onTap: _openTeaching),
                const SizedBox(height: 14),
                _AxisCard(number: '03', icon: Icons.forum_rounded, color: const Color(0xFF00A88F), title: _t('ممارسة الجمل', 'Sentence practice'), subtitle: _t('محادثة طبيعية تستخدم الجمل التي تعلمتها في نفس الدرس.', 'A natural conversation using the sentences from this lesson.'), enabled: canPractice, done: false, action: _t('ابدأ الممارسة', 'Start practice'), locked: _t('أكمل التعليم مع AI أولًا', 'Complete AI teaching first'), onTap: () => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_t('محور الممارسة سيستخدم نفس جمل الدرس.', 'The practice stage will use the same lesson sentences.'))))),
              ]))),
            ],
          ),
        ),
      ),
    );
  }
}

class _AxisCard extends StatelessWidget {
  final String number; final IconData icon; final Color color; final String title; final String subtitle; final bool enabled; final bool done; final String action; final String locked; final VoidCallback onTap;
  const _AxisCard({required this.number, required this.icon, required this.color, required this.title, required this.subtitle, required this.enabled, required this.done, required this.action, required this.locked, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context); final muted = theme.colorScheme.onSurface.withOpacity(.58);
    return Material(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(24), child: InkWell(onTap: enabled ? onTap : null, borderRadius: BorderRadius.circular(24), child: AnimatedOpacity(duration: const Duration(milliseconds: 180), opacity: enabled ? 1 : .52, child: Padding(padding: const EdgeInsets.all(18), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(width: 58, height: 58, decoration: BoxDecoration(color: color.withOpacity(.12), borderRadius: BorderRadius.circular(19)), child: Icon(done ? Icons.check_rounded : enabled ? icon : Icons.lock_rounded, color: color)),
      const SizedBox(width: 15), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(number, style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 12)), const SizedBox(height: 3), Text(title, style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900)), const SizedBox(height: 6), Text(subtitle, style: TextStyle(color: muted, height: 1.45)), const SizedBox(height: 14), Text(done ? '✓ ${theme.brightness == Brightness.dark ? 'Completed' : 'مكتمل'}' : enabled ? action : locked, style: TextStyle(color: color, fontWeight: FontWeight.w800))])), const SizedBox(width: 8), Icon(done ? Icons.check_circle_rounded : enabled ? Icons.arrow_forward_ios_rounded : Icons.lock_outline_rounded, size: 18, color: muted),
    ])))));
  }
}
