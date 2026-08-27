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

  @override
  void dispose() {
    wordController.dispose();
    translationController.dispose();
    super.dispose();
  }

  Future<void> saveWord() async {
    final word = wordController.text.trim();
    final translation = translationController.text.trim();

    if (word.isEmpty || translation.isEmpty) {
      return;
    }

    setState(() {
      isSaving = true;
    });

    try {
      await apiService.createWord(word: word, translation: translation);

      if (!mounted) return;

      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isSaving = false;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
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
            child: Icon(
              Icons.translate_rounded,
              color: theme.colorScheme.onPrimaryContainer,
            ),
          ),

          const SizedBox(width: 12),

          const Text('Add Word', style: TextStyle(fontWeight: FontWeight.bold)),
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
              labelText: 'Word',
              hintText: 'Enter a word',
              prefixIcon: const Icon(Icons.language),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),

          const SizedBox(height: 16),

          TextField(
            controller: translationController,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (!isSaving) {
                saveWord();
              }
            },
            decoration: InputDecoration(
              labelText: 'Translation',
              hintText: 'Enter the translation',
              prefixIcon: const Icon(Icons.translate),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),
        ],
      ),

      actionsPadding: const EdgeInsets.fromLTRB(20, 0, 20, 20),

      actions: [
        TextButton(
          onPressed: isSaving
              ? null
              : () {
                  Navigator.of(context).pop(false);
                },
          child: const Text('Cancel'),
        ),

        const SizedBox(width: 8),

        FilledButton.icon(
          onPressed: isSaving ? null : saveWord,
          icon: isSaving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.save_rounded),
          label: Text(isSaving ? 'Saving...' : 'Save'),
        ),
      ],
    );
  }
}
