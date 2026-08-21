import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

class WordCard extends StatelessWidget {
  final dynamic word;
  final VoidCallback onToggleLearned;
  final VoidCallback onDelete;

  const WordCard({
    super.key,
    required this.word,
    required this.onToggleLearned,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    final bool learned = word['learned'] == true;

    final String wordText = word['word'] ?? '';
    final String translation = word['translation'] ?? '';

    final String statusText = learned ? l10n.learned : l10n.learning;

    final String toggleText = learned
        ? l10n.returnToLearningButton
        : l10n.markCompleted;

    return Dismissible(
      key: ValueKey(word['id']),

      direction: DismissDirection.horizontal,

      confirmDismiss: (direction) async {
        if (direction == DismissDirection.startToEnd) {
          onDelete();
          return false;
        }

        onToggleLearned();
        return false;
      },

      // Swipe right → Delete
      background: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 22),
        decoration: BoxDecoration(
          color: Colors.red.shade50,
          borderRadius: BorderRadius.circular(20),
        ),
        alignment: Alignment.centerLeft,
        child: Row(
          children: [
            Icon(Icons.delete_outline_rounded, color: Colors.red.shade600),
            const SizedBox(width: 8),
            Text(
              l10n.delete,
              style: TextStyle(
                color: Colors.red.shade600,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),

      // Swipe left → Change status
      secondaryBackground: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 22),
        decoration: BoxDecoration(
          color: learned
              ? theme.colorScheme.primaryContainer
              : Colors.green.withOpacity(0.12),
          borderRadius: BorderRadius.circular(20),
        ),
        alignment: Alignment.centerRight,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Flexible(
              child: Text(
                toggleText,
                textAlign: TextAlign.end,
                style: TextStyle(
                  color: learned
                      ? theme.colorScheme.onPrimaryContainer
                      : Colors.green.shade700,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Icon(
              learned
                  ? Icons.school_outlined
                  : Icons.check_circle_outline_rounded,
              color: learned
                  ? theme.colorScheme.onPrimaryContainer
                  : Colors.green.shade600,
            ),
          ],
        ),
      ),

      // Word Card
      child: Card(
        elevation: 0,
        margin: const EdgeInsets.only(bottom: 14),
        color: theme.colorScheme.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(
            color: learned
                ? Colors.green.withOpacity(0.25)
                : Colors.grey.shade200,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Main word icon
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: learned
                      ? Colors.green.withOpacity(0.12)
                      : theme.colorScheme.secondaryContainer,
                  borderRadius: BorderRadius.circular(17),
                ),
                child: Icon(
                  learned ? Icons.check_rounded : Icons.translate_rounded,
                  size: 27,
                  color: learned
                      ? Colors.green.shade600
                      : theme.colorScheme.onSecondaryContainer,
                ),
              ),

              const SizedBox(width: 14),

              // Word information
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      wordText,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        decoration: learned ? TextDecoration.lineThrough : null,
                      ),
                    ),

                    const SizedBox(height: 6),

                    Row(
                      children: [
                        Icon(
                          Icons.arrow_forward_rounded,
                          size: 15,
                          color: Colors.grey.shade500,
                        ),
                        const SizedBox(width: 5),
                        Expanded(
                          child: Text(
                            translation,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 10),

                    // Status
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 9,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: learned
                            ? Colors.green.withOpacity(0.10)
                            : theme.colorScheme.primary.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        statusText,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: learned
                              ? Colors.green.shade700
                              : theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 8),

              // Change status button
              IconButton(
                tooltip: toggleText,
                onPressed: onToggleLearned,
                icon: Icon(
                  learned
                      ? Icons.school_outlined
                      : Icons.check_circle_outline_rounded,
                  color: learned ? Colors.green.shade600 : Colors.grey.shade500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
