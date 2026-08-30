import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../controllers/words_controller.dart';
import '../word_card.dart';

class WordsView extends StatelessWidget {
  final WordsController controller;
  final Future<void> Function(dynamic word) onToggleLearned;
  final Future<void> Function(dynamic word) onDelete;
  final Future<void> Function() onRefresh;

  const WordsView({
    super.key,
    required this.controller,
    required this.onToggleLearned,
    required this.onDelete,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    if (controller.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (controller.errorMessage != null) {
      return _ErrorView(
        message: controller.errorMessage!,
        onRetry: onRefresh,
        l10n: l10n,
      );
    }

    if (controller.words.isEmpty) {
      return RefreshIndicator(
        onRefresh: onRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * .75,
              child: _EmptyState(theme: theme, l10n: l10n),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 30),
        children: [
          _WordsHeader(controller: controller, l10n: l10n),
          const SizedBox(height: 18),
          _FilterBar(controller: controller, l10n: l10n),
          const SizedBox(height: 18),
          if (controller.filteredWords.isEmpty)
            _FilterEmptyState(controller: controller, l10n: l10n)
          else
            ...controller.filteredWords.map(
              (word) => WordCard(
                word: word,
                onToggleLearned: () => onToggleLearned(word),
                onDelete: () => onDelete(word),
              ),
            ),
        ],
      ),
    );
  }
}

class _WordsHeader extends StatelessWidget {
  final WordsController controller;
  final AppLocalizations l10n;

  const _WordsHeader({required this.controller, required this.l10n});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primaryContainer,
            theme.colorScheme.secondaryContainer,
          ],
        ),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l10n.myVocabulary, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
                    const SizedBox(height: 6),
                    Text(l10n.savedWordsCount(controller.words.length), style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              Container(
                width: 58,
                height: 58,
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: .8), shape: BoxShape.circle),
                child: const Icon(Icons.auto_stories_rounded, size: 30),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              _SmallStat(icon: Icons.school_outlined, value: '${controller.learningCount}', label: l10n.learning),
              const SizedBox(width: 10),
              _SmallStat(icon: Icons.check_circle_outline_rounded, value: '${controller.learnedCount}', label: l10n.learned),
            ],
          ),
        ],
      ),
    );
  }
}

class _SmallStat extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;

  const _SmallStat({required this.icon, required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: .65), borderRadius: BorderRadius.circular(14)),
        child: Row(
          children: [
            Icon(icon, size: 19),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: Colors.grey.shade700)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  final WordsController controller;
  final AppLocalizations l10n;

  const _FilterBar({required this.controller, required this.l10n});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.grey.shade200)),
      child: Row(
        children: [
          _FilterButton(controller: controller, label: l10n.all, filter: WordFilter.all),
          _FilterButton(controller: controller, label: l10n.learning, filter: WordFilter.learning),
          _FilterButton(controller: controller, label: l10n.learned, filter: WordFilter.learned),
        ],
      ),
    );
  }
}

class _FilterButton extends StatelessWidget {
  final WordsController controller;
  final String label;
  final WordFilter filter;

  const _FilterButton({required this.controller, required this.label, required this.filter});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final selected = controller.selectedFilter == filter;

    return Expanded(
      child: GestureDetector(
        onTap: () => controller.setFilter(filter),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 11, horizontal: 4),
          decoration: BoxDecoration(color: selected ? theme.colorScheme.primary : Colors.transparent, borderRadius: BorderRadius.circular(12)),
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: selected ? theme.colorScheme.onPrimary : Colors.grey.shade600),
          ),
        ),
      ),
    );
  }
}

class _FilterEmptyState extends StatelessWidget {
  final WordsController controller;
  final AppLocalizations l10n;

  const _FilterEmptyState({required this.controller, required this.l10n});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final learned = controller.selectedFilter == WordFilter.learned;

    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.grey.shade200)),
      child: Column(
        children: [
          Icon(learned ? Icons.school_outlined : Icons.menu_book_outlined, size: 42, color: theme.colorScheme.primary),
          const SizedBox(height: 14),
          Text(learned ? l10n.noLearnedWords : l10n.noLearningWords, textAlign: TextAlign.center, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Text(learned ? l10n.keepPracticing : l10n.wordsAddedDuringLearning, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade600, height: 1.4)),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final ThemeData theme;
  final AppLocalizations l10n;

  const _EmptyState({required this.theme, required this.l10n});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(color: theme.colorScheme.primaryContainer, shape: BoxShape.circle),
              child: Icon(Icons.menu_book_rounded, size: 48, color: theme.colorScheme.onPrimaryContainer),
            ),
            const SizedBox(height: 24),
            Text(l10n.noSavedWords, textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text(l10n.saveWordsDuringConversation, textAlign: TextAlign.center, style: TextStyle(fontSize: 15, color: Colors.grey.shade600, height: 1.5)),
            const SizedBox(height: 26),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.grey.shade200)),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.auto_awesome_rounded, size: 20, color: theme.colorScheme.primary),
                  const SizedBox(width: 10),
                  Flexible(child: Text(l10n.learnNaturally, textAlign: TextAlign.center)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final Future<void> Function() onRetry;
  final AppLocalizations l10n;

  const _ErrorView({required this.message, required this.onRetry, required this.l10n});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(color: Colors.red.shade50, shape: BoxShape.circle),
              child: Icon(Icons.cloud_off_rounded, size: 38, color: Colors.red.shade400),
            ),
            const SizedBox(height: 20),
            Text(l10n.errorOccurred, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade600)),
            const SizedBox(height: 20),
            ElevatedButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh_rounded), label: Text(l10n.tryAgain)),
          ],
        ),
      ),
    );
  }
}
