import 'package:flutter/material.dart';

import '../services/api/api_service.dart';

class AddWordDialog extends StatefulWidget {
  const AddWordDialog({super.key});

  @override
  State<AddWordDialog> createState() => _AddWordDialogState();
}

class _AddWordDialogState extends State<AddWordDialog> {
  final ApiService apiService = ApiService();

  final wordController = TextEditingController();
  final translationController = TextEditingController();

  bool isSaving = false;

  String t(BuildContext context, String key) {
    final lang = Localizations.localeOf(context).languageCode;
    const values = {
      'ar': {
        'title': 'إضافة كلمة', 'word': 'الكلمة', 'wordHint': 'أدخل كلمة',
        'translation': 'الترجمة', 'translationHint': 'أدخل الترجمة',
        'cancel': 'إلغاء', 'saving': 'جارٍ الحفظ...', 'save': 'حفظ',
      },
      'en': {
        'title': 'Add Word', 'word': 'Word', 'wordHint': 'Enter a word',
        'translation': 'Translation', 'translationHint': 'Enter the translation',
        'cancel': 'Cancel', 'saving': 'Saving...', 'save': 'Save',
      },
      'fr': {
        'title': 'Ajouter un mot', 'word': 'Mot', 'wordHint': 'Entrez un mot',
        'translation': 'Traduction', 'translationHint': 'Entrez la traduction',
        'cancel': 'Annuler', 'saving': 'Enregistrement...', 'save': 'Enregistrer',
      },
      'es': {
        'title': 'Añadir palabra', 'word': 'Palabra', 'wordHint': 'Introduce una palabra',
        'translation': 'Traducción', 'translationHint': 'Introduce la traducción',
        'cancel': 'Cancelar', 'saving': 'Guardando...', 'save': 'Guardar',
      },
      'zh': {
        'title': '添加单词', 'word': '单词', 'wordHint': '输入单词',
        'translation': '翻译', 'translationHint': '输入翻译',
        'cancel': '取消', 'saving': '保存中...', 'save': '保存',
      },
      'ja': {
        'title': '単語を追加', 'word': '単語', 'wordHint': '単語を入力',
        'translation': '翻訳', 'translationHint': '翻訳を入力',
        'cancel': 'キャンセル', 'saving': '保存中...', 'save': '保存',
      },
      'ko': {
        'title': '단어 추가', 'word': '단어', 'wordHint': '단어를 입력하세요',
        'translation': '번역', 'translationHint': '번역을 입력하세요',
        'cancel': '취소', 'saving': '저장 중...', 'save': '저장',
      },
    };
    return values[lang]?[key] ?? values['en']![key]!;
  }

  @override
  void dispose() {
    wordController.dispose();
    translationController.dispose();
    super.dispose();
  }

  Future<void> saveWord() async {
    final word = wordController.text.trim();
    final translation = translationController.text.trim();

    if (word.isEmpty || translation.isEmpty) return;

    setState(() => isSaving = true);

    try {
      await apiService.createWord(word: word, translation: translation);
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() => isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      title: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(Icons.translate_rounded, color: theme.colorScheme.onPrimaryContainer),
          ),
          const SizedBox(width: 12),
          Text(t(context, 'title'), style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 8),
          TextField(
            controller: wordController,
            textInputAction: TextInputAction.next,
              decoration: InputDecoration(
              labelText: t(context, 'word'),
              hintText: t(context, 'wordHint'),
              prefixIcon: const Icon(Icons.language),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: translationController,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (!isSaving) saveWord();
            },
            decoration: InputDecoration(
              labelText: t(context, 'translation'),
              hintText: t(context, 'translationHint'),
              prefixIcon: const Icon(Icons.translate),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
        ],
      ),
      actionsPadding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      actions: [
        TextButton(
          onPressed: isSaving ? null : () => Navigator.of(context).pop(false),
          child: Text(t(context, 'cancel')),
        ),
        const SizedBox(width: 8),
        FilledButton.icon(
          onPressed: isSaving ? null : saveWord,
          icon: isSaving
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.save_rounded),
          label: Text(isSaving ? t(context, 'saving') : t(context, 'save')),
        ),
      ],
    );
  }
}
