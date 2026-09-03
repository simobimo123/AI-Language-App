import 'package:flutter/material.dart';

import '../../services/api/api_service.dart';
import '../../services/api/learning_bank_api.dart';

class SaveSentenceDialog extends StatefulWidget {
  final String initialSentence;
  final String initialTranslation;

  const SaveSentenceDialog({
    super.key,
    required this.initialSentence,
    this.initialTranslation = '',
  });

  @override
  State<SaveSentenceDialog> createState() => _SaveSentenceDialogState();
}

class _SaveSentenceDialogState extends State<SaveSentenceDialog> {
  late final TextEditingController _sentenceController;
  late final TextEditingController _translationController;
  final ApiService _apiService = ApiService();

  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _sentenceController = TextEditingController(text: widget.initialSentence);
    _translationController =
        TextEditingController(text: widget.initialTranslation);
  }

  @override
  void dispose() {
    _sentenceController.dispose();
    _translationController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final sentence = _sentenceController.text.trim();
    final translation = _translationController.text.trim();

    if (sentence.isEmpty || translation.isEmpty || _saving) {
      return;
    }

    setState(() => _saving = true);

    try {
      await _apiService.saveSentence(
        sentence: sentence,
        translation: translation,
      );

      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تعذر حفظ الجملة. حاول مرة أخرى.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('حفظ الجملة'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _sentenceController,
              maxLines: 4,
              maxLength: 255,
              enabled: !_saving,
              decoration: const InputDecoration(
                labelText: 'الجملة',
                hintText: 'اختر الجملة التي تريد تذكرها',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _translationController,
              maxLines: 3,
              maxLength: 255,
              enabled: !_saving,
              decoration: const InputDecoration(
                labelText: 'الترجمة',
                hintText: 'أدخل معناها بلغتك',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(false),
          child: const Text('إلغاء'),
        ),
        FilledButton.icon(
          onPressed: _saving ? null : _save,
          icon: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.bookmark_add_outlined),
          label: const Text('حفظ'),
        ),
      ],
    );
  }
}

Future<bool?> showSaveSentenceDialog(
  BuildContext context, {
  required String sentence,
  String translation = '',
}) {
  return showDialog<bool>(
    context: context,
    builder: (_) => SaveSentenceDialog(
      initialSentence: sentence,
      initialTranslation: translation,
    ),
  );
}
