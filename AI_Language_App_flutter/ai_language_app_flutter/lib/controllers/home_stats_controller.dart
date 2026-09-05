import 'package:flutter/foundation.dart';

import '../core/errors/error_message.dart';
import '../models/stats_model.dart';
import '../repositories/stats_repository.dart';

class HomeStatsController extends ChangeNotifier {
  final StatsRepository repository;

  StatsModel? _stats;
  bool _isLoading = false;
  String? _errorMessage;

  HomeStatsController({StatsRepository? repository})
      : repository = repository ?? StatsRepository();

  StatsModel? get stats => _stats;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  int get streakDays => _stats?.streakDays ?? 0;
  int get learnedWords => _stats?.learnedWords ?? 0;
  int get conversations => _stats?.conversations ?? 0;
  double get learningProgress => _stats?.learningProgress ?? 0.0;
  int get completedLessons => _stats?.completedLessons ?? 0;
  int get totalLessons => _stats?.totalLessons ?? 0;

  Future<void> load() => _fetch();

  Future<void> refresh() => _fetch(force: true);

  Future<void> _fetch({bool force = false}) async {
    if (_isLoading && !force) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _stats = await repository.getHomeStats();
    } catch (error) {
      _errorMessage = ErrorMessage.from(error);
      _stats = null; // Clear stale data on error
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
