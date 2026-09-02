import 'package:flutter/material.dart';

import '../core/language/language_controller.dart';
import '../models/learning_lesson_model.dart';
import '../repositories/learning_repository.dart';

class LessonAssessmentPage extends StatefulWidget {
  final LearningLessonModel lesson;
  final LanguageController languageController;
  final LearningRepository? repository;

  const LessonAssessmentPage({
    super.key,
    required this.lesson,
    required this.languageController,
    this.repository,
  });

  @override
  State<LessonAssessmentPage> createState() => _LessonAssessmentPageState();
}

class _LessonAssessmentPageState extends State<LessonAssessmentPage> {
  late final LearningRepository _repository;

  List<Map<String, dynamic>> _questions = [];
  final Map<String, String> _answers = {};

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

  String _locale() => widget.languageController.locale.languageCode;

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
      case 'fr': return fr ?? en;
      case 'es': return es ?? en;
      case 'de': return de ?? en;
      case 'it': return it ?? en;
      case 'ja': return ja ?? en;
      case 'ko': return ko ?? en;
      case 'zh': return zh ?? en;
      case 'ar':
      default: return ar;
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
    fr: 'Chargement de l’évaluation...',
    es: 'Cargando evaluación...',
    de: 'Test wird geladen...',
    it: 'Caricamento della verifica...',
    ja: 'テストを読み込んでいます...',
    ko: '평가를 불러오는 중...',
    zh: '正在加载测试...',
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

  String _resultTitle(bool passed) => passed
      ? _text(
          ar: 'أحسنت! اجتزت الاختبار',
          en: 'Great! You passed',
          fr: 'Bravo ! Vous avez réussi',
          es: '¡Genial! Has aprobado',
          de: 'Großartig! Bestanden',
          it: 'Ottimo! Hai superato il test',
          ja: '合格しました！',
          ko: '통과했습니다!',
          zh: '太棒了！你通过了',
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

  Future<void> _loadAssessment() async {
    try {
      final data = await _repository.getLessonAssessment(
        lessonId: widget.lesson.id,
      );

      final rawQuestions = data['questions'];
      final questions = rawQuestions is List
          ? rawQuestions
              .whereType<Map>()
              .map((item) => Map<String, dynamic>.from(item))
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
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? fallback;
  }

  Future<void> _submit() async {
    if (_submitting || _questions.isEmpty) return;

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final result = await _repository.submitLessonAssessment(
        lessonId: widget.lesson.id,
        answers: _answers.entries
            .map(
              (entry) => {
                'question_id': entry.key,
                'answer': entry.value,
              },
            )
            .toList(),
      );

      if (!mounted) return;

      final passed = result['passed'] == true;
      final score = _toDouble(result['score'], 0);
      final bestScore = _toDouble(result['best_score'], score);
      final levelUpgraded = result['level_upgraded'] == true;
      final newLevel = result['new_level']?.toString() ?? '';

      await _showResult(
        passed: passed,
        score: score,
        bestScore: bestScore,
        levelUpgraded: levelUpgraded,
        newLevel: newLevel,
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
      builder: (context) => AlertDialog(
        title: Text(_resultTitle(passed)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${_scoreLabel()}: ${score.toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text('${_passingLabel()}: ${_passingScore.toStringAsFixed(0)}%'),
            const SizedBox(height: 8),
            Text('Best: ${bestScore.toStringAsFixed(0)}%'),
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
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ],
          ],
        ),
        actions: [
          if (!passed)
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
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
              Navigator.of(context).pop();
              Navigator.of(context).pop(passed);
            },
            child: Text(passed ? _continueLabel() : _retryLabel()),
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
        appBar: AppBar(title: Text(_title())),
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
        appBar: AppBar(title: Text(_title())),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              _error ?? 'No assessment questions available.',
              textAlign: TextAlign.center,
              style: TextStyle(color: theme.colorScheme.error),
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

    return Scaffold(
      appBar: AppBar(
        title: Text(_title()),
        actions: [
          Padding(
            padding: const EdgeInsetsDirectional.only(end: 16),
            child: Center(
              child: Text(
                '${_currentIndex + 1}/${_questions.length}',
                style: theme.textTheme.labelLarge,
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
                  ...options.map((option) {
                    final optionId = option['id']?.toString() ?? '';
                    final optionText = option['text']?.toString() ?? '';
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: RadioListTile<String>(
                        value: optionId,
                        groupValue: selected,
                        onChanged: _submitting
                            ? null
                            : (value) {
                                if (value == null) return;
                                setState(() {
                                  _answers[id] = value;
                                });
                              },
                        title: Text(
                          optionText,
                          textDirection: _textDirection(optionText),
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                          side: BorderSide(
                            color: selected == optionId
                                ? theme.colorScheme.primary
                                : theme.colorScheme.outlineVariant,
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: selected == null || _submitting
                      ? null
                      : () {
                          if (isLast) {
                            _submit();
                          } else {
                            setState(() => _currentIndex++);
                          }
                        },
                  icon: Icon(isLast ? Icons.check_rounded : Icons.arrow_forward_rounded),
                  label: Text(isLast ? _submitLabel() : _nextLabel()),
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
