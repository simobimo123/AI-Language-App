import 'package:flutter/material.dart';

import '../../models/learning_lesson_model.dart';
import '../../services/api/api_service.dart';

class LessonInfoDialog extends StatefulWidget {
  final LearningLessonModel lesson;
  final VoidCallback onStart;

  const LessonInfoDialog({
    super.key,
    required this.lesson,
    required this.onStart,
  });

  @override
  State<LessonInfoDialog> createState() => _LessonInfoDialogState();
}

class _LessonInfoDialogState extends State<LessonInfoDialog> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadPreview();
  }

  Future<void> _loadPreview() async {
    try {
      final data = await _apiService.getLessonPreview(
        lessonId: widget.lesson.id,
      );
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'تعذر تحميل معلومات الدرس.';
      });
    }
  }

  String _string(String key, String fallback) {
    final value = _data?[key];
    if (value == null) return fallback;
    final text = value.toString().trim();
    return text.isEmpty ? fallback : text;
  }

  List<String> _strings(String key) {
    final value = _data?[key];
    if (value is! List) return const [];
    return value
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final title = _string('title', widget.lesson.title);
    final objective = _string('objective', 'تعلم واستخدم اللغة من خلال محادثة تفاعلية.');
    final description = _string('description', widget.lesson.subtitle);
    final learnItems = _strings('what_you_will_learn');
    final minutes = _data?['estimated_minutes'];

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 28),
      backgroundColor: Colors.transparent,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520, maxHeight: 680),
        child: Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: .18),
                blurRadius: 30,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(22, 20, 12, 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        textAlign: TextAlign.right,
                        style: TextStyle(
                          fontSize: 23,
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.onSurface,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: 'إغلاق',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
              ),
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(22, 8, 22, 12),
                  child: _loading
                      ? const Padding(
                          padding: EdgeInsets.symmetric(vertical: 70),
                          child: Center(child: CircularProgressIndicator()),
                        )
                      : _buildContent(
                          context,
                          theme,
                          objective,
                          description,
                          learnItems,
                          minutes,
                        ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(22, 8, 22, 22),
                child: SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton.icon(
                    onPressed: widget.onStart,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text(
                      'ابدأ الدرس',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    ThemeData theme,
    String objective,
    String description,
    List<String> learnItems,
    dynamic minutes,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _infoSection(
          theme,
          icon: Icons.flag_rounded,
          title: 'هدف الدرس',
          child: Text(
            objective,
            textAlign: TextAlign.right,
            style: TextStyle(
              fontSize: 14,
              height: 1.55,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const SizedBox(height: 14),
        _infoSection(
          theme,
          icon: Icons.menu_book_rounded,
          title: 'عن الدرس',
          child: Text(
            description,
            textAlign: TextAlign.right,
            style: TextStyle(
              fontSize: 14,
              height: 1.55,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        if (minutes != null) ...[
          const SizedBox(height: 14),
          _infoSection(
            theme,
            icon: Icons.schedule_rounded,
            title: 'المدة',
            child: Text(
              '$minutes دقيقة',
              textAlign: TextAlign.right,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface,
              ),
            ),
          ),
        ],
        if (learnItems.isNotEmpty) ...[
          const SizedBox(height: 14),
          _infoSection(
            theme,
            icon: Icons.auto_awesome_rounded,
            title: 'ماذا ستتعلم؟',
            child: Column(
              children: learnItems
                  .map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 9),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.check_circle_rounded,
                            size: 19,
                            color: theme.colorScheme.primary,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              item,
                              textAlign: TextAlign.right,
                              style: TextStyle(
                                fontSize: 14,
                                height: 1.45,
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(
            _error!,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              color: theme.colorScheme.error,
            ),
          ),
        ],
      ],
    );
  }

  Widget _infoSection(
    ThemeData theme, {
    required IconData icon,
    required String title,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: .42),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Text(
                title,
                textAlign: TextAlign.right,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                icon,
                size: 20,
                color: theme.colorScheme.primary,
              ),
            ],
          ),
          const SizedBox(height: 9),
          child,
        ],
      ),
    );
  }
}
