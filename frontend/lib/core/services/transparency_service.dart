import '../../shared/models/report_model.dart';
import '../constants/api_constants.dart';
import '../network/api_client.dart';

class TransparencyService {
  final ApiClient _client = ApiClient();

  Future<Map<String, dynamic>> getTransparencyStats({String? ward}) async {
    try {
      final queryParams = ward != null ? {'ward': ward} : null;
      final response = await _client.dio.get(
        '${ApiConstants.baseUrl}/transparency/stats',
        queryParameters: queryParams,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<Map<String, dynamic>> getCivicHealthScore({String? ward}) async {
    try {
      final queryParams = ward != null ? {'ward': ward} : null;
      final response = await _client.dio.get(
        '${ApiConstants.baseUrl}/transparency/health-score',
        queryParameters: queryParams,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<List<Map<String, dynamic>>> getPublicMapPoints({String? ward, String? category}) async {
    try {
      final queryParams = <String, dynamic>{
        if (ward != null) 'ward': ward,
        if (category != null) 'category': category,
      };
      final response = await _client.dio.get(
        '${ApiConstants.baseUrl}/transparency/map',
        queryParameters: queryParams,
      );
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }
}
