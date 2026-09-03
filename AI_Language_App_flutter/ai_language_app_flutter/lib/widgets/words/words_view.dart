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

    if (controller.isLoading) return const Center(child: CircularProgressIndicator());

    if (controller.errorMessage != null) {
      return _ErrorView(message: controller.errorMessage!, onRetry: onRefresh, l10n: l10n);
    }

    final isWords = controller.selectedTab == LearningBankTab.words;
    final items = isWords ? controller.filteredWords : controller.filteredSentences;

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 30),
        children: [
          _WordsHeader(controller: controller, l10n: l10n),
          const SizedBox(height: 16),
          _BankTabs(controller: controller),
          const SizedBox(height: 16),
          _FilterBar(controller: controller, l10n: l10n),
          const SizedBox(height: 18),
          if (items.isEmpty)
            _BankEmptyState(
              isWords: isWords,
              controller: controller,
              l10n: l10n,
            )
          else if (isWords)
            ...items.map(
              (word) => WordCard(
                word: word,
                onToggleLearned: () => onToggleLearned(word),
                onDelete: () => onDelete(word),
              ),
            )
          else
            ...items.map(
              (sentence) => _SentenceCard(
                sentence: sentence,
                onToggleLearned: () => _toggleSentence(context, sentence),
                onDelete: () => _deleteSentence(context, sentence),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _toggleSentence(BuildContext context, dynamic sentence) async {
    final learned = sentence['learned'] == true;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(learned ? 'إعادة الجملة للتعلّم؟' : 'تحديد الجملة كمكتملة؟'),
        content: Text(sentence['sentence'].toString()),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('إلغاء')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: Text(learned ? 'إعادة للتعلّم' : 'تم التعلّم')),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await controller.toggleSentenceLearned(sentenceId: sentence['id'] as int, learned: !learned);
      } catch (error) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    }
  }

  Future<void> _deleteSentence(BuildContext context, dynamic sentence) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('حذف الجملة؟'),
        content: Text(sentence['sentence'].toString()),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('إلغاء')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('حذف')),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await controller.deleteSentence(sentence['id'] as int);
      } catch (error) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    }
  }
}

class _BankTabs extends StatelessWidget {
  final WordsController controller;

  const _BankTabs({required this.controller});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final wordsSelected = controller.selectedTab == LearningBankTab.words;

    return Container(
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        children: [
          _BankTab(
            label: 'الكلمات',
            icon: Icons.translate_rounded,
            selected: wordsSelected,
            onTap: () => controller.setTab(LearningBankTab.words),
          ),
          _BankTab(
            label: 'الجمل',
            icon: Icons.chat_bubble_outline_rounded,
            selected: !wordsSelected,
            onTap: () => controller.setTab(LearningBankTab.sentences),
          ),
        ],
      ),
    );
  }
}

class _BankTab extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  const _BankTab({required this.label, required this.icon, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 11),
          decoration: BoxDecoration(
            color: selected ? theme.colorScheme.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 18, color: selected ? theme.colorScheme.onPrimary : Colors.grey.shade600),
              const SizedBox(width: 7),
              Text(label, style: TextStyle(fontWeight: FontWeight.w600, color: selected ? theme.colorScheme.onPrimary : Colors.grey.shade600)),
            ],
          ),
        ),
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
    final total = controller.words.length + controller.sentences.length;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [theme.colorScheme.primaryContainer, theme.colorScheme.secondaryContainer]),
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
                    Text('$total محفوظ', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
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
              _SmallStat(icon: Icons.translate_rounded, value: '${controller.words.length}', label: 'كلمات'),
              const SizedBox(width: 10),
              _SmallStat(icon: Icons.chat_bubble_outline_rounded, value: '${controller.sentences.length}', label: 'جمل'),
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
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)), Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: Colors.grey.shade700))])),
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
          child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: selected ? theme.colorScheme.onPrimary : Colors.grey.shade600)),
        ),
      ),
    );
  }
}

class _SentenceCard extends StatelessWidget {
  final dynamic sentence;
  final VoidCallback onToggleLearned;
  final VoidCallback onDelete;

  const _SentenceCard({required this.sentence, required this.onToggleLearned, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final learned = sentence['learned'] == true;
    final text = sentence['sentence']?.toString() ?? '';
    final translation = sentence['translation']?.toString() ?? '';

    return Dismissible(
      key: ValueKey('sentence-${sentence['id']}'),
      direction: DismissDirection.horizontal,
      confirmDismiss: (direction) async {
        if (direction == DismissDirection.startToEnd) {
          onDelete();
        } else {
          onToggleLearned();
        }
        return false;
      },
      background: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 22),
        decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(20)),
        alignment: Alignment.centerLeft,
        child: Icon(Icons.delete_outline_rounded, color: Colors.red.shade600),
      ),
      secondaryBackground: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 22),
        decoration: BoxDecoration(color: theme.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(20)),
        alignment: Alignment.centerRight,
        child: Icon(learned ? Icons.school_outlined : Icons.check_circle_outline_rounded, color: theme.colorScheme.primary),
      ),
      child: Card(
        elevation: 0,
        margin: const EdgeInsets.only(bottom: 14),
        color: theme.colorScheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: learned ? Colors.green.withValues(alpha: .25) : Colors.grey.shade200)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(color: learned ? Colors.green.withValues(alpha: .12) : theme.colorScheme.secondaryContainer, borderRadius: BorderRadius.circular(16)),
                child: Icon(learned ? Icons.check_rounded : Icons.chat_bubble_outline_rounded, color: learned ? Colors.green.shade600 : theme.colorScheme.primary),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(text, style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, decoration: learned ? TextDecoration.lineThrough : null)),
                    const SizedBox(height: 8),
                    Row(children: [Icon(Icons.arrow_forward_rounded, size: 15, color: Colors.grey.shade500), const SizedBox(width: 5), Expanded(child: Text(translation, style: TextStyle(fontSize: 14, color: Colors.grey.shade600)))]),
                    const SizedBox(height: 10),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5), decoration: BoxDecoration(color: learned ? Colors.green.withValues(alpha: .10) : theme.colorScheme.primary.withValues(alpha: .08), borderRadius: BorderRadius.circular(10)), child: Text(learned ? 'تم التعلّم' : 'جاري التعلّم', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: learned ? Colors.green.shade700 : theme.colorScheme.primary))),
                  ],
                ),
              ),
              IconButton(onPressed: onToggleLearned, icon: Icon(learned ? Icons.school_outlined : Icons.check_circle_outline_rounded, color: learned ? Colors.green.shade600 : Colors.grey.shade500)),
              IconButton(onPressed: onDelete, icon: Icon(Icons.delete_outline_rounded, color: Colors.grey.shade500)),
            ],
          ),
        ),
      ),
    );
  }
}

class _BankEmptyState extends StatelessWidget {
  final bool isWords;
  final WordsController controller;
  final AppLocalizations l10n;

  const _BankEmptyState({required this.isWords, required this.controller, required this.l10n});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final learned = controller.selectedFilter == WordFilter.learned;
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.grey.shade200)),
      child: Column(
        children: [
          Icon(isWords ? Icons.menu_book_outlined : Icons.chat_bubble_outline_rounded, size: 42, color: theme.colorScheme.primary),
          const SizedBox(height: 14),
          Text(
            isWords
                ? (learned ? l10n.noLearnedWords : l10n.noLearningWords)
                : (learned ? 'لا توجد جمل متعلّمة بعد' : 'لا توجد جمل محفوظة بعد'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            isWords
                ? (learned ? l10n.keepPracticing : l10n.wordsAddedDuringLearning)
                : 'احفظ الجمل التي تريد تذكّرها والتدرّب عليها لاحقًا.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey.shade600, height: 1.4),
          ),
        ],
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
            Container(width: 80, height: 80, decoration: BoxDecoration(color: Colors.red.shade50, shape: BoxShape.circle), child: Icon(Icons.cloud_off_rounded, size: 38, color: Colors.red.shade400)),
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
