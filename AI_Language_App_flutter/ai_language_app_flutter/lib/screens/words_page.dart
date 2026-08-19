import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/word_card.dart';

enum WordFilter { all, learning, learned }

class WordsPage extends StatefulWidget {
  const WordsPage({super.key});

  @override
  State<WordsPage> createState() => _WordsPageState();
}

class _WordsPageState extends State<WordsPage> {
  final ApiService apiService = ApiService();

  List<dynamic> words = [];

  bool isLoading = true;
  String? errorMessage;

  WordFilter selectedFilter = WordFilter.all;

  @override
  void initState() {
    super.initState();

    loadWords();
  }

  Future<void> loadWords() async {
    if (!mounted) return;

    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final result = await apiService.getWords();

      if (!mounted) return;

      setState(() {
        words = result;
        isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

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
          title: Text(
            newStatus ? 'تحديد كمكتملة؟' : 'إعادتها إلى جاري التعلم ...؟',
          ),
          content: Text(
            newStatus
                ? 'هل أتقنت كلمة "${word['word']}"؟'
                : 'ستعود كلمة "${word['word']}" إلى قائمة جاري التعلم ...',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context, false);
              },
              child: const Text('إلغاء'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(context, true);
              },
              child: Text(newStatus ? 'تحديد كمكتملة' : 'إعادة إلى التعلّم'),
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

      if (!mounted) return;

      setState(() {
        word['learned'] = newStatus;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            newStatus
                ? 'تم نقل الكلمة إلى تم التعلم.'
                : 'تم نقل الكلمة إلى جاري التعلم ...',
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> deleteWord(dynamic word) async {
    final int wordId = word['id'];

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(22),
          ),
          title: const Text('حذف الكلمة؟'),
          content: Text(
            'هل تريد حذف كلمة "${word['word']}"؟ لا يمكن التراجع عن هذا الإجراء.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context, false);
              },
              child: const Text('إلغاء'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () {
                Navigator.pop(context, true);
              },
              child: const Text('حذف'),
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

      if (!mounted) return;

      setState(() {
        words.removeWhere((item) => item['id'] == wordId);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('تم حذف الكلمة.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;

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

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,

      appBar: AppBar(
        backgroundColor: const Color(0xFFF7F7FB),
        elevation: 0,

        title: const Text(
          'كلماتي',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),

        actions: [
          IconButton(
            onPressed: loadWords,
            tooltip: 'تحديث',
            icon: const Icon(Icons.refresh_rounded),
          ),

          const SizedBox(width: 8),
        ],
      ),

      body: _buildBody(theme),
    );
  }

  Widget _buildBody(ThemeData theme) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (errorMessage != null) {
      return _buildError();
    }

    if (words.isEmpty) {
      return _buildEmptyState(theme);
    }

    return RefreshIndicator(
      onRefresh: loadWords,

      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),

        padding: const EdgeInsets.fromLTRB(16, 8, 16, 30),

        children: [
          _buildWordsHeader(theme),

          const SizedBox(height: 18),

          _buildFilter(theme),

          const SizedBox(height: 18),

          if (filteredWords.isEmpty)
            _buildFilterEmptyState(theme)
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

  Widget _buildWordsHeader(ThemeData theme) {
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
                    const Text(
                      'مفرداتك',

                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                      ),
                    ),

                    const SizedBox(height: 6),

                    Text(
                    '${words.length} كلمة محفوظة',

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
                  color: Colors.white.withOpacity(0.8),
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
                label: 'جاري التعلم ...',
              ),

              const SizedBox(width: 10),

              _buildSmallStat(
                icon: Icons.check_circle_outline_rounded,
                value: '$learnedCount',
                label: 'تم التعلم',
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
          color: Colors.white.withOpacity(0.65),
          borderRadius: BorderRadius.circular(14),
        ),

        child: Row(
          children: [
            Icon(icon, size: 19),

            const SizedBox(width: 8),

            Column(
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
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilter(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(5),

      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
      ),

      child: Row(
        children: [
          _buildFilterButton(label: 'الكل', filter: WordFilter.all),

          _buildFilterButton(label: 'جاري التعلم ...', filter: WordFilter.learning),

          _buildFilterButton(label: 'تم التعلم', filter: WordFilter.learned),
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

          padding: const EdgeInsets.symmetric(vertical: 11),

          decoration: BoxDecoration(
            color: selected ? theme.colorScheme.primary : Colors.transparent,

            borderRadius: BorderRadius.circular(12),
          ),

          child: Text(
            label,
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

  Widget _buildFilterEmptyState(ThemeData theme) {
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
            learnedFilter
                ? 'لا توجد كلمات تم التعلم بعد'
                : 'لا توجد كلمات في جاري التعلم ...',
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 6),

          Text(
            learnedFilter
                ? 'واصل التدريب، وستظهر الكلمات التي تتعلمها هنا.'
                : 'ستظهر هنا الكلمات التي تضيفها أثناء التعلّم.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey.shade600, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
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

            const Text(
              'لا توجد كلمات محفوظة بعد',

              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),

            const SizedBox(height: 10),

            Text(
              'عند اكتشاف كلمة جديدة أثناء محادثة الذكاء الاصطناعي، أضفها إلى مفرداتك.',

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

                  const Flexible(
                    child: Text(
                      'تعلّم بصورة طبيعية من خلال المحادثة',
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

  Widget _buildError() {
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

            const Text(
              'حدث خطأ ما',

              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
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

              label: const Text('حاول مجددًا'),
            ),
          ],
        ),
      ),
    );
  }
}
