import 'package:flutter/material.dart';

import '../services/api/api_service.dart';
import '../core/language/language_controller.dart';
import '../core/theme/theme_controller.dart';


class PlacementTestPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;
  final String language;

  const PlacementTestPage({
    super.key,
    required this.themeController,
    required this.languageController,
    required this.language,
  });

  @override
  State<PlacementTestPage> createState() =>
      _PlacementTestPageState();
}

class _PlacementTestPageState
    extends State<PlacementTestPage> {
  final ApiService apiService = ApiService();

  String currentLevel = 'A1';

  List<dynamic> words = [];
  final Set<int> selectedWordIds = {};

  List<dynamic> quizQuestions = [];
  final Map<int, int> quizAnswers = {};

  bool isLoading = true;
  bool isEvaluating = false;
  bool isQuizMode = false;
  bool isFinished = false;

  String? errorMessage;

  int get quizAnsweredCount =>
      quizAnswers.length;

  @override
  void initState() {
    super.initState();

    loadWords();
  }

  // =========================================================
  // Helpers
  // =========================================================

  bool get isArabic =>
      widget.languageController.locale.languageCode == 'ar';

  String text({
    required String ar,
    required String en,
  }) {
    return isArabic ? ar : en;
  }

  // =========================================================
  // Load vocabulary level
  // =========================================================

  Future<void> loadWords() async {
    if (!mounted) return;

    setState(() {
      isLoading = true;
      isQuizMode = false;
      errorMessage = null;
      words = [];
      selectedWordIds.clear();
    });

    try {
      final result =
          await apiService.getPlacementWords(
        language: widget.language,
        level: currentLevel,
      );

      final receivedWords =
          result['words'] as List<dynamic>?;

      if (receivedWords == null ||
          receivedWords.length != 20) {
        throw Exception(
          text(
            ar: 'تعذر تحميل كلمات الاختبار بشكل صحيح.',
            en: 'The placement words could not be loaded correctly.',
          ),
        );
      }

      if (!mounted) return;

      setState(() {
        words = receivedWords;
        isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        errorMessage = e.toString();
      });
    }
  }

  // =========================================================
  // Toggle known word
  // =========================================================

  void toggleWord(int wordId) {
    if (isEvaluating || isLoading) {
      return;
    }

    setState(() {
      if (selectedWordIds.contains(wordId)) {
        selectedWordIds.remove(wordId);
      } else {
        selectedWordIds.add(wordId);
      }
    });
  }

  // =========================================================
  // Evaluate vocabulary
  // =========================================================

  Future<void> evaluateWords() async {
    if (isEvaluating || words.length != 20) {
      return;
    }

    setState(() {
      isEvaluating = true;
      errorMessage = null;
    });

    try {
      final presentedWordIds = words
          .map(
            (word) => int.parse(
              word['id'].toString(),
            ),
          )
          .toList();

      final selectedIds =
          selectedWordIds.toList();

      final result =
          await apiService.evaluatePlacementWords(
        language: widget.language,
        level: currentLevel,
        presentedWordIds: presentedWordIds,
        selectedWordIds: selectedIds,
      );

      final passed =
          result['passed'] == true;

      final preliminaryLevel =
          result['preliminary_level']
              ?.toString();

      final nextLevel =
          result['next_level']?.toString();

      // -----------------------------------------------------
      // Failed A1 -> PRE_A1
      //
      // There is no confirmation quiz below A1.
      // -----------------------------------------------------

      if (!passed &&
          preliminaryLevel == 'PRE_A1') {
        await finalizeLevel('PRE_A1');
        return;
      }

      // -----------------------------------------------------
      // Failed A2..C2
      //
      // Run confirmation quiz at the preliminary level.
      // -----------------------------------------------------

      if (!passed &&
          preliminaryLevel != null) {
        await loadQuiz(preliminaryLevel);
        return;
      }

      // -----------------------------------------------------
      // Passed current level and there is another level.
      //
      // Continue climbing.
      // -----------------------------------------------------

      if (passed && nextLevel != null) {
        currentLevel = nextLevel;

        if (!mounted) return;

        setState(() {
          isEvaluating = false;
        });

        await loadWords();
        return;
      }

      // -----------------------------------------------------
      // Passed C2.
      //
      // Confirmation quiz is taken at C2.
      // -----------------------------------------------------

      if (passed && nextLevel == null) {
        await loadQuiz(currentLevel);
        return;
      }

      throw Exception(
        text(
          ar: 'تعذر تحديد المرحلة التالية في الاختبار.',
          en: 'Could not determine the next placement stage.',
        ),
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isEvaluating = false;
        errorMessage = e.toString();
      });
    }
  }

  // =========================================================
  // Load confirmation quiz
  // =========================================================

  Future<void> loadQuiz(
    String level,
  ) async {
    if (!mounted) return;

    setState(() {
      isLoading = true;
      isEvaluating = false;
      isQuizMode = false;
      quizQuestions = [];
      quizAnswers.clear();
      errorMessage = null;
    });

    try {
      final result =
          await apiService.getPlacementQuiz(
        language: widget.language,
        level: level,
      );

      final questions =
          result['questions'] as List<dynamic>?;

      if (questions == null ||
          questions.isEmpty) {
        throw Exception(
          text(
            ar: 'تعذر تحميل أسئلة اختبار التأكيد.',
            en: 'The confirmation quiz could not be loaded.',
          ),
        );
      }

      currentLevel = level;

      if (!mounted) return;

      setState(() {
        quizQuestions = questions;
        isLoading = false;
        isQuizMode = true;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        errorMessage = e.toString();
      });
    }
  }

  // =========================================================
  // Select quiz answer
  // =========================================================

  void selectQuizAnswer(
    int questionId,
    int answerIndex,
  ) {
    if (isEvaluating) {
      return;
    }

    setState(() {
      quizAnswers[questionId] =
          answerIndex;
    });
  }

  // =========================================================
  // Evaluate confirmation quiz
  // =========================================================

  Future<void> evaluateQuiz() async {
    if (isEvaluating ||
        quizQuestions.isEmpty ||
        quizAnswers.isEmpty) {
      return;
    }

    if (quizAnswers.length !=
        quizQuestions.length) {
      return;
    }

    setState(() {
      isEvaluating = true;
      errorMessage = null;
    });

    try {
      final answers = quizAnswers.entries
          .map(
            (entry) => {
              'question_id': entry.key,
              'selected_index': entry.value,
            },
          )
          .toList();

      final result =
          await apiService.evaluatePlacementQuiz(
        language: widget.language,
        level: currentLevel,
        answers: answers,
      );

      final finalLevel =
          result['final_level']?.toString();

      if (finalLevel == null ||
          finalLevel.isEmpty) {
        throw Exception(
          text(
            ar: 'لم يتم إرجاع المستوى النهائي.',
            en: 'The final placement level was not returned.',
          ),
        );
      }

      await finalizeLevel(finalLevel);
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isEvaluating = false;
        errorMessage = e.toString();
      });
    }
  }

  // =========================================================
  // Finalize placement
  // =========================================================

  Future<void> finalizeLevel(
    String level,
  ) async {
    try {
      final result =
          await apiService.finalizePlacement(
        language: widget.language,
        level: level,
      );

      final finalLevel =
          result['level']?.toString() ?? level;

      if (!mounted) return;

      setState(() {
        isEvaluating = false;
        isFinished = true;
      });

      await Future<void>.delayed(
        const Duration(milliseconds: 350),
      );

      if (!mounted) return;

      Navigator.pop(
        context,
        finalLevel,
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isEvaluating = false;
        errorMessage = e.toString();
      });
    }
  }

  // =========================================================
  // Restart current level
  // =========================================================

  Future<void> retryCurrentStage() async {
    if (isEvaluating) {
      return;
    }

    await loadWords();
  }

  // =========================================================
  // Level display name
  // =========================================================

  String levelName(String level) {
    if (level == 'PRE_A1') {
      return 'Pre-A1';
    }

    return level;
  }

  // =========================================================
  // Build word test
  // =========================================================

  Widget buildWordTest(
    ThemeData theme,
  ) {
    return Column(
      crossAxisAlignment:
          CrossAxisAlignment.stretch,
      children: [
        Text(
          text(
            ar: 'اختبار المفردات',
            en: 'Vocabulary test',
          ),
          style: theme.textTheme.headlineSmall
              ?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),

        const SizedBox(height: 8),

        Text(
          text(
            ar: 'اختر الكلمات التي تعرف معناها. لا بأس في ترك الكلمات التي لا تعرفها.',
            en: 'Select the words you know. Leave unknown words unselected.',
          ),
          style: TextStyle(
            color:
                theme.colorScheme.onSurfaceVariant,
            height: 1.5,
          ),
        ),

        const SizedBox(height: 18),

        Container(
          padding:
              const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: theme
                .colorScheme
                .primaryContainer,
            borderRadius:
                BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              Icon(
                Icons.school_rounded,
                color: theme
                    .colorScheme
                    .onPrimaryContainer,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  text(
                    ar:
                        'المستوى الحالي: ${levelName(currentLevel)}',
                    en:
                        'Current level: ${levelName(currentLevel)}',
                  ),
                  style: TextStyle(
                    fontWeight:
                        FontWeight.bold,
                    color: theme
                        .colorScheme
                        .onPrimaryContainer,
                  ),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 18),

        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: words.map((word) {
            final id =
                int.parse(
              word['id'].toString(),
            );

            final selected =
                selectedWordIds.contains(id);

            return FilterChip(
              label: Text(
                word['word']
                    ?.toString() ??
                    '',
              ),
              selected: selected,
              onSelected: (_) {
                toggleWord(id);
              },
              avatar: selected
                  ? const Icon(
                      Icons.check_rounded,
                    )
                  : const Icon(
                      Icons.text_fields_rounded,
                    ),
            );
          }).toList(),
        ),

        const SizedBox(height: 22),

        if (errorMessage != null)
          _ErrorCard(
            message: errorMessage!,
            onRetry: retryCurrentStage,
          ),

        const SizedBox(height: 16),

        SizedBox(
          height: 54,
          child: FilledButton(
            onPressed:
                isEvaluating
                    ? null
                    : evaluateWords,
            child: isEvaluating
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child:
                        CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color:
                          Colors.white,
                    ),
                  )
                : Text(
                    text(
                      ar: 'متابعة',
                      en: 'Continue',
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  // =========================================================
  // Build quiz
  // =========================================================

  Widget buildQuiz(
    ThemeData theme,
  ) {
    return Column(
      crossAxisAlignment:
          CrossAxisAlignment.stretch,
      children: [
        Text(
          text(
            ar: 'اختبار التأكيد',
            en: 'Confirmation test',
          ),
          style: theme.textTheme.headlineSmall
              ?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),

        const SizedBox(height: 8),

        Text(
          text(
            ar:
                'أجب عن الأسئلة التالية للتأكد من مستواك.',
            en:
                'Answer the following questions to confirm your level.',
          ),
          style: TextStyle(
            color:
                theme.colorScheme.onSurfaceVariant,
            height: 1.5,
          ),
        ),

        const SizedBox(height: 18),

        Container(
          padding:
              const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color:
                theme.colorScheme.primaryContainer,
            borderRadius:
                BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              Icon(
                Icons.quiz_rounded,
                color: theme
                    .colorScheme
                    .onPrimaryContainer,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  text(
                    ar:
                        'مستوى الاختبار: ${levelName(currentLevel)}',
                    en:
                        'Test level: ${levelName(currentLevel)}',
                  ),
                  style: TextStyle(
                    fontWeight:
                        FontWeight.bold,
                    color: theme
                        .colorScheme
                        .onPrimaryContainer,
                  ),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 20),

        ...List.generate(
          quizQuestions.length,
          (questionIndex) {
            final question =
                quizQuestions[
                    questionIndex];

            final questionId =
                int.parse(
              question['id'].toString(),
            );

            final questionText =
                question['question']
                    ?.toString() ??
                    '';

            final choices =
                List<dynamic>.from(
              question['choices'] ?? [],
            );

            final selectedIndex =
                quizAnswers[questionId];

            return Container(
              margin:
                  const EdgeInsets.only(
                bottom: 18,
              ),
              padding:
                  const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color:
                    theme.colorScheme.surface,
                borderRadius:
                    BorderRadius.circular(
                  18,
                ),
                border: Border.all(
                  color: theme
                      .colorScheme
                      .outlineVariant,
                ),
              ),
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment
                        .stretch,
                children: [
                  Text(
                    '${questionIndex + 1}. $questionText',
                    style: const TextStyle(
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...List.generate(
                    choices.length,
                    (choiceIndex) {
                      final selected =
                          selectedIndex ==
                              choiceIndex;

                      return Padding(
                        padding:
                            const EdgeInsets
                                .only(
                          bottom: 8,
                        ),
                        child: InkWell(
                          onTap: () {
                            selectQuizAnswer(
                              questionId,
                              choiceIndex,
                            );
                          },
                          borderRadius:
                              BorderRadius
                                  .circular(
                            14,
                          ),
                          child:
                              AnimatedContainer(
                            duration:
                                const Duration(
                              milliseconds:
                                  160,
                            ),
                            padding:
                                const EdgeInsets
                                    .all(
                              13,
                            ),
                            decoration:
                                BoxDecoration(
                              color: selected
                                  ? theme
                                      .colorScheme
                                      .primaryContainer
                                  : theme
                                      .colorScheme
                                      .surfaceContainerHighest,
                              borderRadius:
                                  BorderRadius
                                      .circular(
                                14,
                              ),
                              border:
                                  Border.all(
                                color: selected
                                    ? theme
                                        .colorScheme
                                        .primary
                                    : theme
                                        .colorScheme
                                        .outlineVariant,
                              ),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  selected
                                      ? Icons
                                          .radio_button_checked_rounded
                                      : Icons
                                          .radio_button_unchecked_rounded,
                                  color: selected
                                      ? theme
                                          .colorScheme
                                          .primary
                                      : theme
                                          .colorScheme
                                          .onSurfaceVariant,
                                ),
                                const SizedBox(
                                  width: 10,
                                ),
                                Expanded(
                                  child: Text(
                                    choices[
                                            choiceIndex]
                                        .toString(),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            );
          },
        ),

        if (errorMessage != null)
          _ErrorCard(
            message: errorMessage!,
            onRetry: evaluateQuiz,
          ),

        const SizedBox(height: 4),

        SizedBox(
          height: 54,
          child: FilledButton(
            onPressed:
                isEvaluating ||
                        quizAnswers.length !=
                            quizQuestions.length
                    ? null
                    : evaluateQuiz,
            child: isEvaluating
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child:
                        CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color:
                          Colors.white,
                    ),
                  )
                : Text(
                    text(
                      ar: 'إنهاء الاختبار',
                      en: 'Finish test',
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  // =========================================================
  // Build
  // =========================================================

  @override
  Widget build(
    BuildContext context,
  ) {
    final theme =
        Theme.of(context);

    return Scaffold(
      backgroundColor:
          theme.scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor:
            theme.scaffoldBackgroundColor,
        elevation: 0,
        title: Text(
          text(
            ar: 'اختبار تحديد المستوى',
            en: 'Placement Test',
          ),
          style: const TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SafeArea(
        child: isLoading
            ? Center(
                child:
                    CircularProgressIndicator(
                  color:
                      theme.colorScheme.primary,
                ),
              )
            : SingleChildScrollView(
                padding:
                    const EdgeInsets.fromLTRB(
                  20,
                  12,
                  20,
                  30,
                ),
                child: Center(
                  child: ConstrainedBox(
                    constraints:
                        const BoxConstraints(
                      maxWidth: 650,
                    ),
                    child: isFinished
                        ? _FinishedCard(
                            level:
                                currentLevel,
                            isArabic:
                                isArabic,
                          )
                        : isQuizMode
                            ? buildQuiz(
                                theme,
                              )
                            : buildWordTest(
                                theme,
                              ),
                  ),
                ),
              ),
      ),
    );
  }
}

// =========================================================
// Error Card
// =========================================================

class _ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorCard({
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(
    BuildContext context,
  ) {
    final theme =
        Theme.of(context);

    return Container(
      width: double.infinity,
      padding:
          const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color:
            theme.colorScheme.errorContainer,
        borderRadius:
            BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment:
            CrossAxisAlignment.stretch,
        children: [
          Text(
            message,
            style: TextStyle(
              color: theme
                  .colorScheme
                  .onErrorContainer,
            ),
          ),
          const SizedBox(height: 10),
          TextButton.icon(
            onPressed: onRetry,
            icon: const Icon(
              Icons.refresh_rounded,
            ),
            label: Text(
              theme.brightness ==
                      Brightness.dark
                  ? 'Retry'
                  : 'إعادة المحاولة',
            ),
          ),
        ],
      ),
    );
  }
}

// =========================================================
// Finished Card
// =========================================================

class _FinishedCard
    extends StatelessWidget {
  final String level;
  final bool isArabic;

  const _FinishedCard({
    required this.level,
    required this.isArabic,
  });

  @override
  Widget build(
    BuildContext context,
  ) {
    final theme =
        Theme.of(context);

    return Container(
      padding:
          const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color:
            theme.colorScheme.surface,
        borderRadius:
            BorderRadius.circular(24),
        border: Border.all(
          color: theme
              .colorScheme
              .outlineVariant,
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 76,
            height: 76,
            decoration: BoxDecoration(
              color: theme
                  .colorScheme
                  .primaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.check_rounded,
              size: 42,
              color: theme
                  .colorScheme
                  .onPrimaryContainer,
            ),
          ),
          const SizedBox(height: 20),
          Text(
            isArabic
                ? 'تم تحديد مستواك'
                : 'Your level has been determined',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            isArabic
                ? 'مستواك: ${level == 'PRE_A1' ? 'Pre-A1' : level}'
                : 'Your level: ${level == 'PRE_A1' ? 'Pre-A1' : level}',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 17,
              color: theme
                  .colorScheme
                  .primary,
              fontWeight:
                  FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
