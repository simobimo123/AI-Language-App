import 'package:flutter/material.dart';

import '../../services/api/api_service.dart';

Future<bool> showLessonReviewChoice({
  required BuildContext context,
  required String Function({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? it,
    String? ja,
    String? ko,
    String? zh,
  }) text,
}) async {
  FocusManager.instance.primaryFocus?.unfocus();

  final result = await showGeneralDialog<bool>(
    context: context,
    barrierDismissible: false,
    barrierLabel: 'lesson-review-choice',
    barrierColor: Colors.transparent,
    transitionDuration: const Duration(milliseconds: 180),
    pageBuilder: (dialogContext, _, __) {
      final theme = Theme.of(dialogContext);
      final keyboardInset = MediaQuery.viewInsetsOf(dialogContext).bottom;

      return SafeArea(
        child: Align(
          alignment: Alignment.bottomCenter,
          child: Padding(
            padding: EdgeInsets.fromLTRB(12, 12, 12, 145 + keyboardInset),
            child: Material(
              color: theme.colorScheme.surface,
              elevation: 12,
              borderRadius: BorderRadius.circular(18),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.menu_book_rounded,
                          color: theme.colorScheme.primary,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            text(
                              ar: 'هل تريد مراجعة بسيطة قبل الاختبار؟',
                              en: 'Would you like a quick review before the test?',
                              fr: 'Voulez-vous une petite révision avant le test ?',
                              es: '¿Quieres una breve revisión antes del examen?',
                              de: 'Möchtest du vor dem Test eine kurze Wiederholung?',
                              it: 'Vuoi fare un breve ripasso prima del test?',
                              ja: 'テストの前に簡単な復習をしますか？',
                              ko: '시험 전에 간단히 복습할까요?',
                              zh: '测试前要进行简短复习吗？',
                            ),
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => Navigator.of(dialogContext).pop(false),
                            child: Text(
                              text(
                                ar: 'لا',
                                en: 'No',
                                fr: 'Non',
                                es: 'No',
                                de: 'Nein',
                                it: 'No',
                                ja: 'いいえ',
                                ko: '아니요',
                                zh: '否',
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton(
                            onPressed: () => Navigator.of(dialogContext).pop(true),
                            child: Text(
                              text(
                                ar: 'نعم',
                                en: 'Yes',
                                fr: 'Oui',
                                es: 'Sí',
                                de: 'Ja',
                                it: 'Sì',
                                ja: 'はい',
                                ko: '예',
                                zh: '是',
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    },
  );

  return result ?? false;
}

Future<void> showLessonQuickReview({
  required BuildContext context,
  required ApiService apiService,
  required int lessonId,
  required String conversationId,
  required String Function({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? it,
    String? ja,
    String? ko,
    String? zh,
  }) text,
}) async {
  try {
    final data = await apiService.getLessonTranslationCheck(
      lessonId: lessonId,
      conversationId: conversationId,
    );
    final raw = data['questions'];
    final questions = raw is List
        ? raw
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .where(
              (item) =>
                  item['sentence']?.toString().trim().isNotEmpty == true,
            )
            .toList()
        : <Map<String, dynamic>>[];

    if (!context.mounted) return;

    if (questions.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            text(
              ar: 'لا توجد جمل للمراجعة في هذا الدرس.',
              en: 'There are no review sentences for this lesson.',
            ),
          ),
        ),
      );
      return;
    }

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        final theme = Theme.of(dialogContext);
        return AlertDialog(
          title: Text(
            text(
              ar: 'مراجعة سريعة',
              en: 'Quick review',
              fr: 'Révision rapide',
              es: 'Repaso rápido',
              de: 'Kurze Wiederholung',
              it: 'Ripasso rapido',
              ja: '簡単な復習',
              ko: '간단한 복습',
              zh: '快速复习',
            ),
          ),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    text(
                      ar: 'راجع الجمل التي تدربت عليها ثم انتقل إلى التحقق من التعلم.',
                      en: 'Review the sentences you practiced, then continue to the learning check.',
                      fr: 'Révisez les phrases pratiquées, puis passez à la vérification.',
                      es: 'Repasa las frases practicadas y continúa con la comprobación.',
                      de: 'Wiederhole die geübten Sätze und fahre dann mit der Lernkontrolle fort.',
                      it: 'Ripassa le frasi esercitate, poi continua con la verifica.',
                      ja: '練習した文を確認してから、学習チェックに進みましょう。',
                      ko: '연습한 문장을 복습한 후 학습 확인으로 진행하세요.',
                      zh: '复习练习过的句子，然后继续学习检查。',
                    ),
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 14),
                  ...questions.asMap().entries.map(
                    (entry) => Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${entry.key + 1}. ${entry.value['sentence']}',
                        style: theme.textTheme.bodyLarge?.copyWith(
                          height: 1.45,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(
                text(
                  ar: 'متابعة',
                  en: 'Continue',
                  fr: 'Continuer',
                  es: 'Continuar',
                  de: 'Weiter',
                  it: 'Continua',
                  ja: '続ける',
                  ko: '계속',
                  zh: '继续',
                ),
              ),
            ),
          ],
        );
      },
    );
  } catch (_) {
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          text(
            ar: 'تعذر تحميل المراجعة. يمكنك المتابعة بدونها.',
            en: 'The review could not be loaded. You can continue without it.',
          ),
        ),
      ),
    );
  }
}
