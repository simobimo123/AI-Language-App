import 'package:flutter/foundation.dart';

import '../models/stats_model.dart';
import '../repositories/stats_repository.dart';

class HomeStatsController extends ChangeNotifier {
  final StatsRepository repository;

  StatsModel? _stats;

  bool _isLoading = false;
  String? _errorMessage;

  HomeStatsController({
    StatsRepository? repository,
  }) : repository = repository ?? StatsRepository();

  StatsModel? get stats => _stats;

  bool get isLoading => _isLoading;

  String? get errorMessage => _errorMessage;

  int get streakDays => _stats?.streakDays ?? 0;

  int get learnedWords => _stats?.learnedWords ?? 0;

  int get conversations => _stats?.conversations ?? 0;

  double get learningProgress =>
      _stats?.learningProgress ?? 0.0;

  int get completedLessons =>
      _stats?.completedLessons ?? 0;

  int get totalLessons =>
      _stats?.totalLessons ?? 0;

  Future<void> load() async {
    if (_isLoading) {
      return;
    }

    _isLoading = true;
    _errorMessage = null;

    notifyListeners();

    try {
      _stats = await repository.getHomeStats();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = _cleanErrorMessage(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() async {
    _isLoading = true;
    _errorMessage = null;

    notifyListeners();

    try {
      _stats = await repository.getHomeStats();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = _cleanErrorMessage(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  String _cleanErrorMessage(Object error) {
    final message = error.toString();

    if (message.startsWith('Exception: ')) {
      return message.substring(
        'Exception: '.length,
      );
    }

    return message;
  }
}