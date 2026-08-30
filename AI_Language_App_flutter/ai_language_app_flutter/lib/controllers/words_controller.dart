import 'package:flutter/foundation.dart';

import '../core/errors/error_message.dart';
import '../repositories/word_repository.dart';
import '../services/learning_language_controller.dart';

enum WordFilter { all, learning, learned }

class WordsController extends ChangeNotifier {
  final WordRepository repository;
  final LearningLanguageController learningLanguageController;

  List<dynamic> _words = [];
  bool _isLoading = true;
  String? _errorMessage;
  WordFilter _selectedFilter = WordFilter.all;

  WordsController({
    WordRepository? repository,
    LearningLanguageController? learningLanguageController,
  })  : repository = repository ?? WordRepository(),
        learningLanguageController =
            learningLanguageController ?? LearningLanguageController.instance {
    this.learningLanguageController.addListener(_onLearningLanguageChanged);
  }

  List<dynamic> get words => List.unmodifiable(_words);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  WordFilter get selectedFilter => _selectedFilter;

  int get learningCount =>
      _words.where((word) => word['learned'] != true).length;

  int get learnedCount =>
      _words.where((word) => word['learned'] == true).length;

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

  Future<void> loadWords() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _words = await repository.getWords();
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

  Future<void> toggleLearned({
    required int wordId,
    required bool learned,
  }) async {
    await repository.updateWordStatus(
      wordId: wordId,
      learned: learned,
    );

    final index = _words.indexWhere((word) => word['id'] == wordId);
    if (index == -1) return;

    _words[index]['learned'] = learned;
    notifyListeners();
  }

  Future<void> deleteWord(int wordId) async {
    await repository.deleteWord(wordId: wordId);
    _words.removeWhere((word) => word['id'] == wordId);
    notifyListeners();
  }

  void _onLearningLanguageChanged() {
    loadWords();
  }

  @override
  void dispose() {
    learningLanguageController.removeListener(_onLearningLanguageChanged);
    super.dispose();
  }
}
