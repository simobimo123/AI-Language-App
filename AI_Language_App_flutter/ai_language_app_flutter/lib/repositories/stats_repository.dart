import '../models/stats_model.dart';
import '../services/api/api_service.dart';

class StatsRepository {
  final ApiService apiService;

  StatsRepository({
    ApiService? apiService,
  }) : apiService = apiService ?? ApiService();

  Future<StatsModel> getHomeStats() async {
    final data = await apiService.getHomeStats();

    return StatsModel.fromJson(data);
  }
}