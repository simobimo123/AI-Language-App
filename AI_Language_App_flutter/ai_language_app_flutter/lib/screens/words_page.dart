import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';
import '../services/learning_language_controller.dart';
import '../widgets/word_card.dart';

enum WordFilter { all, learning, learned }

class WordsPage extends StatefulWidget {
  const WordsPage({super.key});

  @override
  State<WordsPage> createState() => _WordsPageState();
}

class _WordsPageState extends State<WordsPage> {
  final ApiService apiService = ApiService();

  final LearningLanguageController learningLanguageController =
      LearningLanguageController.instance;

  List<dynamic> words = [];

  bool isLoading = true;

  String? errorMessage;

  WordFilter selectedFilter = WordFilter.all;

  @override
  void initState() {
    super.initState();

    learningLanguageController.addListener(_onLearningLanguageChanged);

    loadWords();
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);

    super.dispose();
  }

  void _onLearningLanguageChanged() {
    if (!mounted) {
      return;
    }

    loadWords();
  }

  Future<void> loadWords() async {
    if (!mounted) {
      return;
    }

    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final result = await apiService.getWords();

      if (!mounted) {
        return;
      }

      setState(() {
        words = result;
        isLoading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  List<dynamic> get filteredWords {
    final result = [...words];

    result.sort((a, b) {
      final learnedA = a['learned'] == true;
      final learnedB = b['learned'] == true;

      if (learnedA == learnedB) {
        return 0;
      }

      return learnedA ? 1 : -1;
    });

    if (selectedFilter == WordFilter.learning) {
      return result.where((word) {
        return word['learned'] != true;
      }).toList();
    }

    if (selectedFilter == WordFilter.learned) {
      return result.where((word) {
        return word['learned'] == true;
      }).toList();
    }

    return result;
  }

  int get learningCount {
    return words.where((word) {
      return word['learned'] != true;
    }).length;
  }

  int get learnedCount {
    return words.where((word) {
      return word['learned'] == true;
    }).length;
  }

  Future<void> toggleLearned(dynamic word) async {
    final l10n = AppLocalizations.of(context)!;

    final int wordId = word['id'];

    final bool currentStatus = word['learned'] == true;

    final bool newStatus = !currentStatus;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(22),
          ),
          title: Text(newStatus ? l10n.completeWord : l10n.returnToLearning),
          content: Text(
            newStatus
                ? l10n.masteredWord(word['word'].toString())
                : l10n.returnWordToLearning(word['word'].toString()),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context, false);
              },
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(context, true);
              },
              child: Text(
                newStatus ? l10n.markCompleted : l10n.returnToLearningButton,
              ),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    try {
      await apiService.updateWordStatus(wordId: wordId, learned: newStatus);

      if (!mounted) {
        return;
      }

      setState(() {
        word['learned'] = newStatus;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            newStatus ? l10n.wordMovedToLearned : l10n.wordMovedToLearning,
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> deleteWord(dynamic word) async {
    final l10n = AppLocalizations.of(context)!;

    final int wordId = word['id'];

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(22),
          ),
          title: Text(l10n.deleteWordTitle),
          content: Text(l10n.deleteWordConfirmation(word['word'].toString())),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context, false);
              },
              child: Text(l10n.cancel),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () {
                Navigator.pop(context, true);
              },
              child: Text(l10n.delete),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    try {
      await apiService.deleteWord(wordId: wordId);

      if (!mounted) {
        return;
      }

      setState(() {
        words.removeWhere((item) => item['id'] == wordId);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.wordDeleted),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: theme.scaffoldBackgroundColor,
        elevation: 0,
        title: Text(
          l10n.words,
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),
      body: _buildBody(theme, l10n),
    );
  }

  Widget _buildBody(ThemeData theme, AppLocalizations l10n) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (errorMessage != null) {
      return _buildError(l10n);
    }

    if (words.isEmpty) {
      return RefreshIndicator(
        onRefresh: loadWords,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.75,
              child: _buildEmptyState(theme, l10n),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: loadWords,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 30),
        children: [
          _buildWordsHeader(theme, l10n),
          const SizedBox(height: 18),
          _buildFilter(theme, l10n),
          const SizedBox(height: 18),
          if (filteredWords.isEmpty)
            _buildFilterEmptyState(theme, l10n)
          else
            ...filteredWords.map((word) {
              return WordCard(
                word: word,
                onToggleLearned: () {
                  toggleLearned(word);
                },
                onDelete: () {
                  deleteWord(word);
                },
              );
            }),
        ],
      ),
    );
  }

  Widget _buildWordsHeader(ThemeData theme, AppLocalizations l10n) {
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
                    Text(
                      l10n.myVocabulary,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      l10n.savedWordsCount(words.length),
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: 58,
                height: 58,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.8),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.auto_stories_rounded, size: 30),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              _buildSmallStat(
                icon: Icons.school_outlined,
                value: '$learningCount',
                label: l10n.learning,
              ),
              const SizedBox(width: 10),
              _buildSmallStat(
                icon: Icons.check_circle_outline_rounded,
                value: '$learnedCount',
                label: l10n.learned,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSmallStat({
    required IconData icon,
    required String value,
    required String label,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.65),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Icon(icon, size: 19),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    value,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilter(ThemeData theme, AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        children: [
          _buildFilterButton(label: l10n.all, filter: WordFilter.all),
          _buildFilterButton(label: l10n.learning, filter: WordFilter.learning),
          _buildFilterButton(label: l10n.learned, filter: WordFilter.learned),
        ],
      ),
    );
  }

  Widget _buildFilterButton({
    required String label,
    required WordFilter filter,
  }) {
    final theme = Theme.of(context);

    final selected = selectedFilter == filter;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            selectedFilter = filter;
          });
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 11, horizontal: 4),
          decoration: BoxDecoration(
            color: selected ? theme.colorScheme.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: selected
                  ? theme.colorScheme.onPrimary
                  : Colors.grey.shade600,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFilterEmptyState(ThemeData theme, AppLocalizations l10n) {
    final bool learnedFilter = selectedFilter == WordFilter.learned;

    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        children: [
          Icon(
            learnedFilter ? Icons.school_outlined : Icons.menu_book_outlined,
            size: 42,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: 14),
          Text(
            learnedFilter ? l10n.noLearnedWords : l10n.noLearningWords,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            learnedFilter ? l10n.keepPracticing : l10n.wordsAddedDuringLearning,
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey.shade600, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme, AppLocalizations l10n) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.menu_book_rounded,
                size: 48,
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              l10n.noSavedWords,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              l10n.saveWordsDuringConversation,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 15,
                color: Colors.grey.shade600,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 26),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.auto_awesome_rounded,
                    size: 20,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 10),
                  Flexible(
                    child: Text(
                      l10n.learnNaturally,
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError(AppLocalizations l10n) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.cloud_off_rounded,
                size: 38,
                color: Colors.red.shade400,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              l10n.errorOccurred,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              errorMessage!,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade600),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: loadWords,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(l10n.tryAgain),
            ),
          ],
        ),
      ),
    );
  }
}
