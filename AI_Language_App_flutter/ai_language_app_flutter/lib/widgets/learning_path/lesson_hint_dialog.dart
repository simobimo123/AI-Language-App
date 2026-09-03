import 'package:flutter/material.dart';

import '../../services/api/lesson_hint_api_service.dart';

Future<void> showLessonHintDialog(
  BuildContext context, {
  required LessonHint hint,
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
}) {
  return showDialog<void>(
    context: context,
    builder: (dialogContext) {
      final theme = Theme.of(dialogContext);

      return AlertDialog(
        title: Row(
          children: [
            Icon(Icons.lightbulb_rounded, color: theme.colorScheme.primary),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                text(
                  ar: 'اقتراح للإجابة',
                  en: 'Suggested answer',
                  fr: 'Réponse suggérée',
                  es: 'Respuesta sugerida',
                  de: 'Vorgeschlagene Antwort',
                  it: 'Risposta suggerita',
                  ja: '回答のヒント',
                  ko: '추천 답변',
                  zh: '建议回答',
                ),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              hint.suggestion,
              textDirection: TextDirection.ltr,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                hint.translation,
                textDirection: _direction(hint.translation),
                style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              text(
                ar: 'هذه مجرد مساعدة. أرسل الإجابة بنفسك بالكتابة أو بالصوت.',
                en: 'This is only a hint. Send the answer yourself by typing or speaking.',
                fr: 'C’est seulement une aide. Envoyez vous-même la réponse par écrit ou à l’oral.',
                es: 'Es solo una ayuda. Envía tú mismo la respuesta escribiendo o hablando.',
                de: 'Das ist nur eine Hilfe. Sende die Antwort selbst per Text oder Sprache.',
                it: 'È solo un aiuto. Invia tu la risposta scrivendo o parlando.',
                ja: 'これはヒントです。答えは自分で入力するか、音声で話してください。',
                ko: '이것은 힌트일 뿐입니다. 직접 입력하거나 음성으로 답변을 보내세요.',
                zh: '这只是提示。请你自己通过输入或语音发送答案。',
              ),
              style: theme.textTheme.bodySmall?.copyWith(height: 1.4),
            ),
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(
              text(
                ar: 'حسنًا',
                en: 'OK',
                fr: 'OK',
                es: 'Aceptar',
                de: 'OK',
                it: 'OK',
                ja: 'OK',
                ko: '확인',
                zh: '确定',
              ),
            ),
          ),
        ],
      );
    },
  );
}

TextDirection _direction(String value) {
  return RegExp(r'[\u0600-\u06FF]').hasMatch(value)
      ? TextDirection.rtl
      : TextDirection.ltr;
}
