
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

  String text({
    required String ar,
    required String en,
  }) {
    final lang = languageController.locale.languageCode;

    const translations = <String, Map<String, String>>{
      'اختبار المفردات': {
        'en': 'Vocabulary test',
        'fr': 'Test de vocabulaire',
        'es': 'Prueba de vocabulario',
        'zh': '词汇测试',
        'ja': '語彙テスト',
        'ko': '어휘 테스트',
        'de': 'Vokabeltest',
        'id': 'Tes kosakata',
        'it': 'Test di vocabolario',
        'nl': 'Woordenschattoets',
        'pl': 'Test słownictwa',
        'pt': 'Teste de vocabulário',
        'ru': 'Тест на словарный запас',
        'th': 'แบบทดสอบคำศัพท์',
        'tr': 'Kelime testi',
        'uk': 'Тест словникового запасу',
        'vi': 'Bài kiểm tra từ vựng',
      },
      'اختر الكلمات التي تعرف معناها. اترك الكلمات التي لا تعرفها بدون تحديد.': {
        'en':
            'Select the words you know. Leave unknown words unselected.',
        'fr':
            'Sélectionnez les mots dont vous connaissez le sens. Laissez les mots inconnus non sélectionnés.',
        'es':
            'Selecciona las palabras que conoces. Deja sin seleccionar las que no conozcas.',
        'zh': '选择你知道意思的单词。不了解的单词请不要选择。',
        'ja': '意味を知っている単語を選択してください。知らない単語は選択しないでください。',
        'ko': '의미를 아는 단어를 선택하세요. 모르는 단어는 선택하지 마세요.',
        'de':
            'Wählen Sie die Wörter aus, deren Bedeutung Sie kennen. Unbekannte Wörter bleiben abgewählt.',
        'id':
            'Pilih kata yang Anda ketahui artinya. Biarkan kata yang tidak diketahui tidak dipilih.',
        'it':
            'Seleziona le parole di cui conosci il significato. Lascia deselezionate quelle che non conosci.',
        'nl':
            'Selecteer de woorden waarvan je de betekenis kent. Laat onbekende woorden ongeselecteerd.',
        'pl':
            'Wybierz słowa, których znaczenie znasz. Nie zaznaczaj nieznanych słów.',
        'pt':
            'Selecione as palavras cujo significado você conhece. Deixe as desconhecidas sem selecionar.',
        'ru':
            'Выберите слова, значение которых вы знаете. Незнакомые слова не выбирайте.',
        'th': 'เลือกคำที่คุณรู้ความหมาย และไม่ต้องเลือกคำที่คุณไม่รู้จัก',
        'tr':
            'Anlamını bildiğiniz kelimeleri seçin. Bilmediğiniz kelimeleri seçmeden bırakın.',
        'uk':
            'Виберіть слова, значення яких ви знаєте. Незнайомі слова не вибирайте.',
        'vi': 'Chọn những từ bạn biết nghĩa. Không chọn những từ bạn chưa biết.',
      },
      'متابعة': {
        'en': 'Continue',
        'fr': 'Continuer',
        'es': 'Continuar',
        'zh': '继续',
        'ja': '続ける',
        'ko': '계속',
        'de': 'Weiter',
        'id': 'Lanjutkan',
        'it': 'Continua',
        'nl': 'Doorgaan',
        'pl': 'Dalej',
        'pt': 'Continuar',
        'ru': 'Продолжить',
        'th': 'ดำเนินการต่อ',
        'tr': 'Devam et',
        'uk': 'Продовжити',
        'vi': 'Tiếp tục',
      },
      'تم تحديد مستواك': {
        'en': 'Your level has been determined',
        'fr': 'Votre niveau a été déterminé',
        'es': 'Tu nivel ha sido determinado',
        'zh': '你的水平已确定',
        'ja': 'あなたのレベルが決まりました',
        'ko': '레벨이 결정되었습니다',
        'de': 'Ihr Niveau wurde bestimmt',
        'id': 'Tingkat Anda telah ditentukan',
        'it': 'Il tuo livello è stato determinato',
        'nl': 'Je niveau is bepaald',
        'pl': 'Twój poziom został określony',
        'pt': 'Seu nível foi determinado',
        'ru': 'Ваш уровень определён',
        'th': 'กำหนดระดับของคุณแล้ว',
        'tr': 'Seviyeniz belirlendi',
        'uk': 'Ваш рівень визначено',
        'vi': 'Trình độ của bạn đã được xác định',
      },
      'Retry': {
        'ar': 'إعادة المحاولة',
        'en': 'Retry',
        'fr': 'Réessayer',
        'es': 'Reintentar',
        'zh': '重试',
        'ja': '再試行',
        'ko': '다시 시도',
        'de': 'Erneut versuchen',
        'id': 'Coba lagi',
        'it': 'Riprova',
        'nl': 'Opnieuw proberen',
        'pl': 'Spróbuj ponownie',
        'pt': 'Tentar novamente',
        'ru': 'Повторить',
        'th': 'ลองอีกครั้ง',
        'tr': 'Tekrar dene',
        'uk': 'Повторити',
        'vi': 'Thử lại',
      },
    };

    if (lang == 'ar') {
      return ar;
    }

    return translations[ar]?[lang] ?? en;
  }

  String levelName(String level) {
    return level == 'PRE_A1' ? 'Pre-A1' : level;
  }

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

    return _WordsView(
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
            ar:
                'اختر الكلمات التي تعرف معناها. اترك الكلمات التي لا تعرفها بدون تحديد.',
            en:
                'Select the words you know. Leave unknown words unselected.',
          ),
          style: TextStyle(
            color: theme.colorScheme.onSurfaceVariant,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 18),
        _LevelCard(
          icon: Icons.school_rounded,
          label:
              '${_currentLevelLabel(context)} ${levelName(controller.currentLevel)}',
          theme: theme,
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: controller.words.map((word) {
            final selected = controller.selectedWordIds.contains(word.id);

            return FilterChip(
              label: Text(word.word),
              selected: selected,
              onSelected: (_) {
                controller.toggleWord(word.id);
              },
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
            text: text,
          ),
        ],
        const SizedBox(height: 20),
        SizedBox(
          height: 54,
          child: FilledButton(
            onPressed: controller.isEvaluating
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

  String _currentLevelLabel(BuildContext context) {
    final lang = Localizations.localeOf(context).languageCode;

    const labels = {
      'ar': 'المستوى الحالي:',
      'en': 'Current level:',
      'fr': 'Niveau actuel :',
      'es': 'Nivel actual:',
      'zh': '当前水平：',
      'ja': '現在のレベル：',
      'ko': '현재 레벨:',
      'de': 'Aktuelles Niveau:',
      'id': 'Tingkat saat ini:',
      'it': 'Livello attuale:',
      'nl': 'Huidig niveau:',
      'pl': 'Aktualny poziom:',
      'pt': 'Nível atual:',
      'ru': 'Текущий уровень:',
      'th': 'ระดับปัจจุบัน:',
      'tr': 'Mevcut seviye:',
      'uk': 'Поточний рівень:',
      'vi': 'Trình độ hiện tại:',
    };

    return labels[lang] ?? labels['en']!;
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
                color: theme.colorScheme.onPrimaryContainer,
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
  final String Function({
    required String ar,
    required String en,
  }) text;

  const _ErrorCard({
    required this.message,
    required this.onRetry,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(message),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(
                text(
                  ar: 'Retry',
                  en: 'Retry',
                ),
              ),
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
              level == 'PRE_A1' ? 'Pre-A1' : level,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      ),
    );
  }
}