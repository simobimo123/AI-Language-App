import 'package:flutter/material.dart';

import '../../services/api/api_service.dart';
import '../../services/api/learning_bank_api.dart';

class WordDetailDialog extends StatefulWidget {
  final String word;
  final String languageCode;

  const WordDetailDialog({
    super.key,
    required this.word,
    required this.languageCode,
  });

  @override
  State<WordDetailDialog> createState() => _WordDetailDialogState();
}

class _WordDetailDialogState extends State<WordDetailDialog> {
  final ApiService _apiService = ApiService();

  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = true;
  bool _savingWord = false;
  bool _savingSentence = false;
  bool _wordSaved = false;
  bool _sentenceSaved = false;

  @override
  void initState() {
    super.initState();
    _load();
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
    switch (widget.languageCode) {
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

  Future<void> _load() async {
    try {
      final data = await _apiService.lookupWord(word: widget.word);
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = _text(
          ar: 'تعذر الحصول على معلومات الكلمة.',
          en: 'Unable to load the word information.',
          fr: 'Impossible de charger les informations du mot.',
          es: 'No se pudo cargar la información de la palabra.',
          de: 'Die Wortinformationen konnten nicht geladen werden.',
          it: 'Impossibile caricare le informazioni della parola.',
          ja: '単語の情報を読み込めませんでした。',
          ko: '단어 정보를 불러오지 못했습니다.',
          zh: '无法加载单词信息。',
        );
      });
    }
  }

  Future<void> _saveWord() async {
    final translation = (_data?['translation'] ?? '').toString().trim();
    if (translation.isEmpty || _savingWord || _wordSaved) return;

    setState(() => _savingWord = true);
    try {
      await _apiService.createWord(
        word: (_data?['word'] ?? widget.word).toString(),
        translation: translation,
      );
      if (!mounted) return;
      setState(() {
        _savingWord = false;
        _wordSaved = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _savingWord = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_text(
            ar: 'تعذر حفظ الكلمة.',
            en: 'Unable to save the word.',
            fr: 'Impossible d’enregistrer le mot.',
            es: 'No se pudo guardar la palabra.',
            de: 'Das Wort konnte nicht gespeichert werden.',
            it: 'Impossibile salvare la parola.',
            ja: '単語を保存できませんでした。',
            ko: '단어를 저장하지 못했습니다.',
            zh: '无法保存单词。',
          )),
        ),
      );
    }
  }

  Future<void> _saveSentence() async {
    final sentence = (_data?['example_sentence'] ?? '').toString().trim();
    final translation =
        (_data?['example_translation'] ?? '').toString().trim();
    if (sentence.isEmpty || translation.isEmpty || _savingSentence || _sentenceSaved) {
      return;
    }

    setState(() => _savingSentence = true);
    try {
      await _apiService.saveSentence(
        sentence: sentence,
        translation: translation,
      );
      if (!mounted) return;
      setState(() {
        _savingSentence = false;
        _sentenceSaved = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _savingSentence = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_text(
            ar: 'تعذر حفظ الجملة.',
            en: 'Unable to save the sentence.',
            fr: 'Impossible d’enregistrer la phrase.',
            es: 'No se pudo guardar la frase.',
            de: 'Der Satz konnte nicht gespeichert werden.',
            it: 'Impossibile salvare la frase.',
            ja: '文を保存できませんでした。',
            ko: '문장을 저장하지 못했습니다.',
            zh: '无法保存句子。',
          )),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final translation = (_data?['translation'] ?? '').toString().trim();
    final example = (_data?['example_sentence'] ?? '').toString().trim();
    final exampleTranslation =
        (_data?['example_translation'] ?? '').toString().trim();
    final partOfSpeech =
        (_data?['part_of_speech'] ?? '').toString().trim();
    final pronunciation =
        (_data?['pronunciation'] ?? '').toString().trim();

    return AlertDialog(
      title: Row(
        children: [
          Expanded(
            child: Text(
              (_data?['word'] ?? widget.word).toString(),
              textDirection: TextDirection.ltr,
            ),
          ),
          IconButton(
            tooltip: _text(
              ar: 'إغلاق', en: 'Close', fr: 'Fermer', es: 'Cerrar',
              de: 'Schließen', it: 'Chiudi', ja: '閉じる', ko: '닫기', zh: '关闭',
            ),
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.close),
          ),
        ],
      ),
      content: SizedBox(
        width: 520,
        child: _loading
            ? const Padding(
                padding: EdgeInsets.all(28),
                child: Center(child: CircularProgressIndicator()),
              )
            : _error != null
                ? Text(_error!)
                : SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          translation.isEmpty
                              ? _text(
                                  ar: 'لا توجد ترجمة محفوظة بعد.',
                                  en: 'No translation is available yet.',
                                  fr: 'Aucune traduction disponible pour le moment.',
                                  es: 'Aún no hay traducción disponible.',
                                  de: 'Noch keine Übersetzung verfügbar.',
                                  it: 'Nessuna traduzione disponibile.',
                                  ja: 'まだ翻訳がありません。',
                                  ko: '아직 번역이 없습니다.',
                                  zh: '暂时没有可用的翻译。',
                                )
                              : translation,
                          style: theme.textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        if (partOfSpeech.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            partOfSpeech,
                            style: theme.textTheme.bodyMedium,
                          ),
                        ],
                        if (pronunciation.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            pronunciation,
                            style: theme.textTheme.bodyMedium,
                          ),
                        ],
                        const SizedBox(height: 20),
                        if (example.isNotEmpty) ...[
                          Text(
                            _text(
                              ar: 'مثال',
                              en: 'Example',
                              fr: 'Exemple',
                              es: 'Ejemplo',
                              de: 'Beispiel',
                              it: 'Esempio',
                              ja: '例文',
                              ko: '예문',
                              zh: '例句',
                            ),
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            example,
                            textDirection: TextDirection.ltr,
                            style: theme.textTheme.bodyLarge?.copyWith(
                              height: 1.45,
                            ),
                          ),
                          if (exampleTranslation.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text(
                              exampleTranslation,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                height: 1.4,
                              ),
                            ),
                          ],
                        ],
                      ],
                    ),
                  ),
      ),
      actions: _loading || _error != null
          ? null
          : [
              TextButton.icon(
                onPressed: translation.isEmpty || _savingWord || _wordSaved
                    ? null
                    : _saveWord,
                icon: _savingWord
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(
                        _wordSaved
                            ? Icons.check_circle_outline
                            : Icons.bookmark_add_outlined,
                      ),
                label: Text(
                  _wordSaved
                      ? _text(
                          ar: 'تم حفظ الكلمة',
                          en: 'Word saved',
                          fr: 'Mot enregistré',
                          es: 'Palabra guardada',
                          de: 'Wort gespeichert',
                          it: 'Parola salvata',
                          ja: '単語を保存しました',
                          ko: '단어 저장됨',
                          zh: '单词已保存',
                        )
                      : _text(
                          ar: 'حفظ الكلمة',
                          en: 'Save word',
                          fr: 'Enregistrer le mot',
                          es: 'Guardar palabra',
                          de: 'Wort speichern',
                          it: 'Salva parola',
                          ja: '単語を保存',
                          ko: '단어 저장',
                          zh: '保存单词',
                        ),
                ),
              ),
              if (example.isNotEmpty)
                FilledButton.icon(
                  onPressed: exampleTranslation.isEmpty ||
                          _savingSentence ||
                          _sentenceSaved
                      ? null
                      : _saveSentence,
                  icon: _savingSentence
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          _sentenceSaved
                              ? Icons.check_circle_outline
                              : Icons.bookmark_add_outlined,
                        ),
                  label: Text(
                    _sentenceSaved
                        ? _text(
                            ar: 'تم حفظ المثال',
                            en: 'Example saved',
                            fr: 'Exemple enregistré',
                            es: 'Ejemplo guardado',
                            de: 'Beispiel gespeichert',
                            it: 'Esempio salvato',
                            ja: '例文を保存しました',
                            ko: '예문 저장됨',
                            zh: '例句已保存',
                          )
                        : _text(
                            ar: 'حفظ المثال',
                            en: 'Save example',
                            fr: 'Enregistrer l’exemple',
                            es: 'Guardar ejemplo',
                            de: 'Beispiel speichern',
                            it: 'Salva esempio',
                            ja: '例文を保存',
                            ko: '예문 저장',
                            zh: '保存例句',
                          ),
                  ),
                ),
            ],
    );
  }
}

Future<void> showWordDetailDialog(
  BuildContext context, {
  required String word,
  required String languageCode,
}) {
  return showDialog<void>(
    context: context,
    builder: (_) => WordDetailDialog(
      word: word,
      languageCode: languageCode,
    ),
  );
}
