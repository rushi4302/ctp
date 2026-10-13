import '../constants/api_constants.dart';
import '../network/api_client.dart';

class TransparencyService {
  final ApiClient _client = ApiClient();

  Future<Map<String, dynamic>> getTransparencyStats({String? ward, String? locality}) async {
    try {
      final queryParams = <String, dynamic>{
        if (ward != null) 'ward': ward,
        if (locality != null) 'locality': locality,
      };
      final response = await _client.dio.get(
        '${ApiConstants.baseUrl}/transparency/stats',
        queryParameters: queryParams.isEmpty ? null : queryParams,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<Map<String, dynamic>> getCivicHealthScore({String? ward, String? locality}) async {
    try {
      final queryParams = <String, dynamic>{
        if (ward != null) 'ward': ward,
        if (locality != null) 'locality': locality,
      };
      final response = await _client.dio.get(
        '${ApiConstants.baseUrl}/transparency/health-score',
        queryParameters: queryParams.isEmpty ? null : queryParams,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<List<Map<String, dynamic>>> getPublicMapPoints({String? ward, String? category, String? status}) async {
    try {
      final queryParams = <String, dynamic>{
        if (ward != null) 'ward': ward,
        if (category != null) 'category': category,
        if (status != null) 'status_filter': status,
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
