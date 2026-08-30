import 'package:flutter/material.dart';

import '../controllers/words_controller.dart';
import '../l10n/app_localizations.dart';
import '../widgets/words/words_view.dart';

class WordsPage extends StatefulWidget {
  const WordsPage({super.key});

  @override
  State<WordsPage> createState() => _WordsPageState();
}

class _WordsPageState extends State<WordsPage> {
  late final WordsController controller;

  @override
  void initState() {
    super.initState();
    controller = WordsController();
    controller.loadWords();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> _toggleLearned(dynamic word) async {
    final l10n = AppLocalizations.of(context)!;
    final wordId = word['id'] as int;
    final newStatus = word['learned'] != true;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        title: Text(newStatus ? l10n.completeWord : l10n.returnToLearning),
        content: Text(
          newStatus
              ? l10n.masteredWord(word['word'].toString())
              : l10n.returnWordToLearning(word['word'].toString()),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(
              newStatus ? l10n.markCompleted : l10n.returnToLearningButton,
            ),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await controller.toggleLearned(wordId: wordId, learned: newStatus);
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            newStatus ? l10n.wordMovedToLearned : l10n.wordMovedToLearning,
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _deleteWord(dynamic word) async {
    final l10n = AppLocalizations.of(context)!;
    final wordId = word['id'] as int;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        title: Text(l10n.deleteWordTitle),
        content: Text(l10n.deleteWordConfirmation(word['word'].toString())),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(l10n.delete),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await controller.deleteWord(wordId);
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.wordDeleted),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        elevation: 0,
        title: Text(
          l10n.words,
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),
      body: AnimatedBuilder(
        animation: controller,
        builder: (context, _) => WordsView(
          controller: controller,
          onToggleLearned: _toggleLearned,
          onDelete: _deleteWord,
          onRefresh: controller.refresh,
        ),
      ),
    );
  }
}
