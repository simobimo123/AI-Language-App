import 'package:flutter/foundation.dart';

import '../core/errors/error_message.dart';
import '../repositories/word_repository.dart';
import '../services/learning_language_controller.dart';

enum WordFilter { all, learning, learned }
enum LearningBankTab { words, sentences }

class WordsController extends ChangeNotifier {
  final WordRepository repository;
  final LearningLanguageController learningLanguageController;

  List<dynamic> _words = [];
  List<dynamic> _sentences = [];
  bool _isLoading = true;
  String? _errorMessage;
  WordFilter _selectedFilter = WordFilter.all;
  LearningBankTab _selectedTab = LearningBankTab.words;

  WordsController({
    WordRepository? repository,
    LearningLanguageController? learningLanguageController,
  })  : repository = repository ?? WordRepository(),
        learningLanguageController = learningLanguageController ?? LearningLanguageController.instance {
    this.learningLanguageController.addListener(_onLearningLanguageChanged);
  }

  List<dynamic> get words => List.unmodifiable(_words);
  List<dynamic> get sentences => List.unmodifiable(_sentences);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  WordFilter get selectedFilter => _selectedFilter;
  LearningBankTab get selectedTab => _selectedTab;

  int get learningCount => _words.where((word) => word['learned'] != true).length;
  int get learnedCount => _words.where((word) => word['learned'] == true).length;
  int get learningSentenceCount => _sentences.where((sentence) => sentence['learned'] != true).length;
  int get learnedSentenceCount => _sentences.where((sentence) => sentence['learned'] == true).length;

  List<dynamic> get filteredWords {
    final result = [..._words];
    result.sort((a, b) {
      final learnedA = a['learned'] == true;
      final learnedB = b['learned'] == true;
      if (learnedA == learnedB) return 0;
      return learnedA ? 1 : -1;
    });

    switch (_selectedFilter) {
      case WordFilter.all:
        return result;
      case WordFilter.learning:
        return result.where((word) => word['learned'] != true).toList();
      case WordFilter.learned:
        return result.where((word) => word['learned'] == true).toList();
    }
  }

  List<dynamic> get filteredSentences {
    final result = [..._sentences];
    result.sort((a, b) {
      final learnedA = a['learned'] == true;
      final learnedB = b['learned'] == true;
      if (learnedA == learnedB) return 0;
      return learnedA ? 1 : -1;
    });

    switch (_selectedFilter) {
      case WordFilter.all:
        return result;
      case WordFilter.learning:
        return result.where((sentence) => sentence['learned'] != true).toList();
      case WordFilter.learned:
        return result.where((sentence) => sentence['learned'] == true).toList();
    }
  }

    Future<void> loadWords() async {
    if (_isLoading) {
      return;
    }

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final words = await repository.getWords();
      final sentences = await repository.getSentences();
      _words = words;
      _sentences = sentences;
    } catch (error) {
      _errorMessage = ErrorMessage.from(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() => loadWords();

  void setFilter(WordFilter filter) {
    if (_selectedFilter == filter) return;
    _selectedFilter = filter;
    notifyListeners();
  }

  void setTab(LearningBankTab tab) {
    if (_selectedTab == tab) return;
    _selectedTab = tab;
    notifyListeners();
  }

  Future<void> toggleLearned({required int wordId, required bool learned}) async {
    try {
      await repository.updateWordStatus(wordId: wordId, learned: learned);
      final index = _words.indexWhere((word) => word['id'] == wordId);
      if (index == -1) return;
      _words[index]['learned'] = learned;
      notifyListeners();
    } catch (error) {
      _errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> deleteWord(int wordId) async {
    try {
      await repository.deleteWord(wordId: wordId);
      _words.removeWhere((word) => word['id'] == wordId);
      notifyListeners();
    } catch (error) {
      _errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> toggleSentenceLearned({required int sentenceId, required bool learned}) async {
    try {
      await repository.updateSentenceStatus(sentenceId: sentenceId, learned: learned);
      final index = _sentences.indexWhere((sentence) => sentence['id'] == sentenceId);
      if (index == -1) return;
      _sentences[index]['learned'] = learned;
      notifyListeners();
    } catch (error) {
      _errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  Future<void> deleteSentence(int sentenceId) async {
    try {
      await repository.deleteSentence(sentenceId: sentenceId);
      _sentences.removeWhere((sentence) => sentence['id'] == sentenceId);
      notifyListeners();
    } catch (error) {
      _errorMessage = ErrorMessage.from(error);
      notifyListeners();
    }
  }

  void _onLearningLanguageChanged() => loadWords();

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);
    super.dispose();
  }
}
