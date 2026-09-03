import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';

class LessonAssessmentPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;
  final LearningRepository? repository;
  final String? conversationId;

  const LessonAssessmentPage({
    super.key,
    required this.lesson,
    required this.languageController,
    this.conversationId,
    this.repository,
  });

  @override
  State<LessonAssessmentPage> createState() => _LessonAssessmentPageState();
}

class _LessonAssessmentPageState extends State<LessonAssessmentPage> {
  late final LearningRepository _repository;

  final Map<String, String> _answers = {};

  List<Map<String, dynamic>> _questions = [];

  bool _loading = true;
  bool _submitting = false;

  String? _error;

  double _passingScore = 80;

  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();

    _repository = widget.repository ?? LearningRepository();

    _loadAssessment();
  }

  String _locale() {
    return widget.languageController.locale.languageCode;
  }

  String _text({
    required String ar,
    required String en,
    String? fr,
    String? es,
    String? de,
    String? it,
    String? ja,
    String? ko,
    String? zh,
  }) {
    switch (_locale()) {
      case 'fr':
        return fr ?? en;
      case 'es':
        return es ?? en;
      case 'de':
        return de ?? en;
      case 'it':
        return it ?? en;
      case 'ja':
        return ja ?? en;
      case 'ko':
        return ko ?? en;
      case 'zh':
        return zh ?? en;
      case 'ar':
      default:
        return ar;
    }
  }

  String _title() => _text(
        ar: 'اختبار الدرس',
        en: 'Lesson assessment',
        fr: 'Évaluation de la leçon',
        es: 'Evaluación de la lección',
        de: 'Lektionstest',
        it: 'Verifica della lezione',
        ja: 'レッスンテスト',
        ko: '레슨 평가',
        zh: '课程测试',
      );

  String _loadingText() => _text(
        ar: 'جاري تحميل الاختبار...',
        en: 'Loading assessment...',
        fr: 'Chargement...',
        es: 'Cargando...',
        de: 'Test wird geladen...',
        it: 'Caricamento...',
        ja: '読み込み中...',
        ko: '불러오는 중...',
        zh: '正在加载...',
      );

  String _nextLabel() => _text(
        ar: 'التالي',
        en: 'Next',
        fr: 'Suivant',
        es: 'Siguiente',
        de: 'Weiter',
        it: 'Avanti',
        ja: '次へ',
        ko: '다음',
        zh: '下一题',
      );

  String _submitLabel() => _text(
        ar: 'إرسال الإجابات',
        en: 'Submit answers',
        fr: 'Envoyer les réponses',
        es: 'Enviar respuestas',
        de: 'Antworten abgeben',
        it: 'Invia risposte',
        ja: '回答を送信',
        ko: '답변 제출',
        zh: '提交答案',
      );

  String _retryLabel() => _text(
        ar: 'إعادة المحاولة',
        en: 'Try again',
        fr: 'Réessayer',
        es: 'Intentar de nuevo',
        de: 'Erneut versuchen',
        it: 'Riprova',
        ja: 'もう一度',
        ko: '다시 시도',
        zh: '重新尝试',
      );

  String _continueLabel() => _text(
        ar: 'متابعة',
        en: 'Continue',
        fr: 'Continuer',
        es: 'Continuar',
        de: 'Weiter',
        it: 'Continua',
        ja: '続ける',
        ko: '계속',
        zh: '继续',
      );

  String _scoreLabel() => _text(
        ar: 'النتيجة',
        en: 'Score',
        fr: 'Score',
        es: 'Puntuación',
        de: 'Ergebnis',
        it: 'Punteggio',
        ja: 'スコア',
        ko: '점수',
        zh: '得分',
      );

  String _passingLabel() => _text(
        ar: 'درجة النجاح',
        en: 'Passing score',
        fr: 'Score requis',
        es: 'Puntuación mínima',
        de: 'Bestehensgrenze',
        it: 'Punteggio minimo',
        ja: '合格点',
        ko: '통과 점수',
        zh: '及格分数',
      );

  String _bestLabel() => _text(
        ar: 'أفضل نتيجة',
        en: 'Best score',
        fr: 'Meilleur score',
        es: 'Mejor puntuación',
        de: 'Beste Punktzahl',
        it: 'Miglior punteggio',
        ja: 'ベストスコア',
        ko: '최고 점수',
        zh: '最佳得分',
      );

  Future<void> _loadAssessment() async {
    try {
      final data = await _repository.getLessonAssessment(
        lessonId: widget.lesson.id,
        conversationId: widget.conversationId,
      );

      final raw = data['questions'];

      final questions = raw is List
          ? raw
              .whereType<Map>()
              .map((e) => Map<String, dynamic>.from(e))
              .toList()
          : <Map<String, dynamic>>[];

      if (!mounted) return;

      setState(() {
        _questions = questions;
        _passingScore = _toDouble(data['passing_score'], 80);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  double _toDouble(dynamic value, double fallback) {
    return value is num
        ? value.toDouble()
        : double.tryParse(value?.toString() ?? '') ?? fallback;
  }

  Future<void> _submit() async {
    if (_submitting ||
        _questions.isEmpty ||
        _answers.length != _questions.length) {
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final result = await _repository.submitLessonAssessment(
        lessonId: widget.lesson.id,
        conversationId: widget.conversationId,
        answers: _answers.entries
            .map(
              (e) => {
                'question_id': e.key,
                'answer': e.value,
              },
            )
            .toList(),
      );

      if (!mounted) return;

      await _showResult(
        passed: result['passed'] == true,
        score: _toDouble(result['score'], 0),
        bestScore: _toDouble(result['best_score'], 0),
        levelUpgraded: result['level_upgraded'] == true,
        newLevel: result['new_level']?.toString() ?? '',
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _submitting = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _showResult({
    required bool passed,
    required double score,
    required double bestScore,
    required bool levelUpgraded,
    required String newLevel,
  }) async {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        title: Text(
          passed
              ? _text(
                  ar: 'أحسنت! اجتزت الاختبار',
                  en: 'Great! You passed',
                  fr: 'Bravo ! Vous avez réussi',
                  es: '¡Has aprobado!',
                  de: 'Bestanden!',
                  it: 'Test superato!',
                  ja: '合格しました！',
                  ko: '통과했습니다!',
                  zh: '通过了！',
                )
              : _text(
                  ar: 'لم تجتز الاختبار بعد',
                  en: 'Not passed yet',
                  fr: 'Pas encore réussi',
                  es: 'Aún no aprobado',
                  de: 'Noch nicht bestanden',
                  it: 'Non ancora superato',
                  ja: 'まだ合格していません',
                  ko: '아직 통과하지 못했습니다',
                  zh: '还未通过测试',
                ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${_scoreLabel()}: ${score.toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              '${_passingLabel()}: '
              '${_passingScore.toStringAsFixed(0)}%',
            ),
            const SizedBox(height: 8),
            Text(
              '${_bestLabel()}: ${bestScore.toStringAsFixed(0)}%',
            ),
            if (levelUpgraded && newLevel.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                _text(
                  ar: 'تم فتح المستوى $newLevel 🎉',
                  en: 'Level $newLevel unlocked 🎉',
                  fr: 'Niveau $newLevel débloqué 🎉',
                  es: 'Nivel $newLevel desbloqueado 🎉',
                  de: 'Level $newLevel freigeschaltet 🎉',
                  it: 'Livello $newLevel sbloccato 🎉',
                  ja: 'レベル $newLevel が解放されました 🎉',
                  ko: '레벨 $newLevel 잠금 해제 🎉',
                  zh: '已解锁 $newLevel 级 🎉',
                ),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ],
        ),
        actions: [
          if (!passed)
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();

                setState(() {
                  _answers.clear();
                  _currentIndex = 0;
                  _submitting = false;
                });
              },
              child: Text(_retryLabel()),
            ),
          FilledButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();

              if (passed) {
                Navigator.of(context).pop(true);
              }
            },
            child: Text(
              passed ? _continueLabel() : _retryLabel(),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) {
      return Scaffold(
        appBar: AppBar(
          title: Text(_title()),
        ),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(_loadingText()),
            ],
          ),
        ),
      );
    }

    if (_error != null || _questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          title: Text(_title()),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              _error ?? 'No assessment questions available.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: theme.colorScheme.error,
              ),
            ),
          ),
        ),
      );
    }

    final question = _questions[_currentIndex];

    final id = question['id']?.toString() ?? '';

    final text = question['question']?.toString() ?? '';

    final options = question['options'] is List
        ? (question['options'] as List).whereType<Map>().toList()
        : <Map>[];

    final selected = _answers[id];

    final isLast = _currentIndex == _questions.length - 1;

    final canContinue = selected != null &&
        !_submitting &&
        (!isLast || _answers.length == _questions.length);

    return Scaffold(
      appBar: AppBar(
        title: Text(_title()),
        actions: [
          Padding(
            padding: const EdgeInsetsDirectional.only(end: 16),
            child: Center(
              child: Text(
                '${_currentIndex + 1}/${_questions.length}',
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            LinearProgressIndicator(
              value: (_currentIndex + 1) / _questions.length,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  Text(
                    text,
                    textDirection: _textDirection(text),
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // RadioGroup replaces the deprecated
                  // Radio.groupValue / Radio.onChanged API.
                  RadioGroup<String>(
                    groupValue: selected,
                   onChanged: (value) {
  if (_submitting || value == null) {
    return;
  }

  setState(() {
    _answers[id] = value;
  });
},
                    child: Column(
                      children: options.map((option) {
                        final optionId =
                            option['id']?.toString() ?? '';

                        final optionText =
                            option['text']?.toString() ?? '';

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: RadioListTile<String>(
                            value: optionId,
                            title: Text(
                              optionText,
                              textDirection:
                                  _textDirection(optionText),
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius:
                                  BorderRadius.circular(16),
                              side: BorderSide(
                                color: selected == optionId
                                    ? theme.colorScheme.primary
                                    : theme
                                        .colorScheme
                                        .outlineVariant,
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                16,
                8,
                16,
                16,
              ),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: canContinue
                      ? () {
                          if (isLast) {
                            _submit();
                          } else {
                            setState(() {
                              _currentIndex++;
                            });
                          }
                        }
                      : null,
                  icon: Icon(
                    isLast
                        ? Icons.check_rounded
                        : Icons.arrow_forward_rounded,
                  ),
                  label: Text(
                    isLast ? _submitLabel() : _nextLabel(),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  TextDirection _textDirection(String text) {
    return RegExp(r'[\u0600-\u06FF]').hasMatch(text)
        ? TextDirection.rtl
        : TextDirection.ltr;
  }
}