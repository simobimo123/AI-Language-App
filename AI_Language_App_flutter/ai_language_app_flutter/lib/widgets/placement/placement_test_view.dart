import 'package:flutter/material.dart';

import '../../controllers/placement_test_controller.dart';
import '../../core/language/language_controller.dart';
import '../../core/theme/theme_controller.dart';

class PlacementTestView extends StatelessWidget {
  final PlacementTestController controller;
  final ThemeController themeController;
  final LanguageController languageController;

  const PlacementTestView({
    super.key,
    required this.controller,
    required this.themeController,
    required this.languageController,
  });

  bool get isArabic => languageController.locale.languageCode == 'ar';

  String text({
    required String ar,
    required String en,
  }) =>
      isArabic ? ar : en;

  String levelName(String level) =>
      level == 'PRE_A1' ? 'Pre-A1' : level;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (controller.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (controller.isFinished) {
      return _FinishedView(
        level: controller.finalLevel ?? controller.currentLevel,
        text: text,
      );
    }

    return controller.isQuizMode
        ? _QuizView(
            controller: controller,
            theme: theme,
            text: text,
            levelName: levelName,
          )
        : _WordsView(
            controller: controller,
            theme: theme,
            text: text,
            levelName: levelName,
          );
  }
}

class _WordsView extends StatelessWidget {
  final PlacementTestController controller;
  final ThemeData theme;
  final String Function({
    required String ar,
    required String en,
  }) text;
  final String Function(String) levelName;

  const _WordsView({
    required this.controller,
    required this.theme,
    required this.text,
    required this.levelName,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          text(
            ar: 'اختبار المفردات',
            en: 'Vocabulary test',
          ),
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          text(
            ar: 'اختر الكلمات التي تعرف معناها. اترك الكلمات التي لا تعرفها بدون تحديد.',
            en: 'Select the words you know. Leave unknown words unselected.',
          ),
          style: TextStyle(
            color: theme.colorScheme.onSurfaceVariant,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 18),
        _LevelCard(
          icon: Icons.school_rounded,
          label: text(
            ar: 'المستوى الحالي: ${levelName(controller.currentLevel)}',
            en: 'Current level: ${levelName(controller.currentLevel)}',
          ),
          theme: theme,
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: controller.words.map((word) {
            final selected =
                controller.selectedWordIds.contains(word.id);

            return FilterChip(
              label: Text(word.word),
              selected: selected,
              onSelected: (_) =>
                  controller.toggleWord(word.id),
              avatar: Icon(
                selected
                    ? Icons.check_rounded
                    : Icons.text_fields_rounded,
              ),
            );
          }).toList(),
        ),
        if (controller.errorMessage != null) ...[
          const SizedBox(height: 20),
          _ErrorCard(
            message: controller.errorMessage!,
            onRetry: controller.retry,
          ),
        ],
        const SizedBox(height: 20),
        SizedBox(
          height: 54,
          child: FilledButton(
            onPressed:
                controller.isEvaluating
                    ? null
                    : controller.evaluateWords,
            child: controller.isEvaluating
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                    ),
                  )
                : Text(
                    text(
                      ar: 'متابعة',
                      en: 'Continue',
                    ),
                  ),
          ),
        ),
      ],
    );
  }
}

class _QuizView extends StatelessWidget {
  final PlacementTestController controller;
  final ThemeData theme;
  final String Function({
    required String ar,
    required String en,
  }) text;
  final String Function(String) levelName;

  const _QuizView({
    required this.controller,
    required this.theme,
    required this.text,
    required this.levelName,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          text(
            ar: 'اختبار التأكيد',
            en: 'Confirmation test',
          ),
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          text(
            ar: 'أجب عن الأسئلة التالية للتأكد من مستواك.',
            en: 'Answer the following questions to confirm your level.',
          ),
          style: TextStyle(
            color: theme.colorScheme.onSurfaceVariant,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 18),
        _LevelCard(
          icon: Icons.quiz_rounded,
          label: text(
            ar: 'مستوى الاختبار: ${levelName(controller.currentLevel)}',
            en: 'Test level: ${levelName(controller.currentLevel)}',
          ),
          theme: theme,
        ),
        const SizedBox(height: 20),
        ...controller.quizQuestions.asMap().entries.map((entry) {
          final questionNumber = entry.key + 1;
          final question = entry.value;
          final selected =
              controller.quizAnswers[question.id];

          return Card(
            margin: const EdgeInsets.only(bottom: 14),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$questionNumber. ${question.question}',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),

                  RadioGroup<int>(
                    groupValue: selected,

                    // RadioGroup الجديد يتطلب callback غير nullable.
                    // أثناء التقييم نتجاهل أي تغيير بدل تمرير null.
                    onChanged: (value) {
                      if (controller.isEvaluating) {
                        return;
                      }

                      if (value != null) {
                        controller.selectQuizAnswer(
                          question.id,
                          value,
                        );
                      }
                    },

                    child: Column(
                      children: List.generate(
                        question.choices.length,
                        (index) {
                          return RadioListTile<int>(
                            value: index,
                            title: Text(
                              question.choices[index],
                            ),
                            contentPadding:
                                EdgeInsets.zero,
                          );
                        },
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
        if (controller.errorMessage != null)
          _ErrorCard(
            message: controller.errorMessage!,
            onRetry: controller.retry,
          ),
        const SizedBox(height: 8),
        SizedBox(
          height: 54,
          child: FilledButton(
            onPressed: controller.canSubmitQuiz
                ? controller.evaluateQuiz
                : null,
            child: controller.isEvaluating
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                    ),
                  )
                : Text(
                    text(
                      ar: 'إنهاء الاختبار',
                      en: 'Finish test',
                    ),
                  ),
          ),
        ),
      ],
    );
  }
}

class _LevelCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final ThemeData theme;

  const _LevelCard({
    required this.icon,
    required this.label,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: theme.colorScheme.onPrimaryContainer,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color:
                    theme.colorScheme.onPrimaryContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  final Future<void> Function() onRetry;

  const _ErrorCard({
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Text(message),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(
                Icons.refresh_rounded,
              ),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _FinishedView extends StatelessWidget {
  final String level;

  final String Function({
    required String ar,
    required String en,
  }) text;

  const _FinishedView({
    required this.level,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.emoji_events_rounded,
              size: 64,
            ),
            const SizedBox(height: 16),
            Text(
              text(
                ar: 'تم تحديد مستواك',
                en: 'Your level has been determined',
              ),
              style: Theme.of(context)
                  .textTheme
                  .headlineSmall
                  ?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              level,
              style:
                  Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      ),
    );
  }
}