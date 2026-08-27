import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';

class LearningStats extends StatelessWidget {
  final int streakDays;
  final int learnedWords;
  final int conversations;

  const LearningStats({
    super.key,
    required this.streakDays,
    required this.learnedWords,
    required this.conversations,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Row(
      children: [
        Expanded(
          child: StatCard(
            icon: Icons.local_fire_department_rounded,
            value: streakDays.toString(),
            label: l10n.streakDays,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatCard(
            icon: Icons.menu_book_rounded,
            value: learnedWords.toString(),
            label: l10n.learnedWords,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: StatCard(
            icon: Icons.chat_bubble_rounded,
            value: conversations.toString(),
            label: l10n.conversations,
          ),
        ),
      ],
    );
  }
}

class StatCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;

  const StatCard({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      constraints: const BoxConstraints(minHeight: 122),
      padding: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 16,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: theme.colorScheme.outlineVariant,
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.shadow.withValues(
              alpha: 0.04,
            ),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              icon,
              color: theme.colorScheme.primary,
              size: 22,
            ),
          ),
          const SizedBox(height: 9),
          Text(
            value,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 11,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}