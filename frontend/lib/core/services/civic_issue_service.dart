import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../constants/api_constants.dart';
import '../network/api_client.dart';
import '../../shared/models/civic_issue_model.dart';

class CivicIssueService {
  final ApiClient _client = ApiClient();

  Future<List<CivicIssueModel>> getCivicIssues({
    int skip = 0,
    int limit = 50,
    String? statusFilter,
    String? category,
    String? ward,
    int? assignedWorkerId,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'skip': skip,
        'limit': limit,
        if (statusFilter != null && statusFilter.isNotEmpty) 'status_filter': statusFilter,
        if (category != null && category.isNotEmpty) 'category': category,
        if (ward != null && ward.isNotEmpty) 'ward': ward,
        if (assignedWorkerId != null) 'assigned_worker_id': assignedWorkerId,
      };

      final response = await _client.dio.get(
        '${ApiConstants.baseUrl}/civic-issues',
        queryParameters: queryParams,
      );

      final list = response.data as List<dynamic>;
      return list.map((item) => CivicIssueModel.fromJson(item as Map<String, dynamic>)).toList();
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<CivicIssueModel> getCivicIssueById(int id) async {
    try {
      final response = await _client.dio.get('${ApiConstants.baseUrl}/civic-issues/$id');
      return CivicIssueModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<CivicIssueModel> resolveCivicIssue(
    int issueId,
    String resolutionNotes, {
    String? imagePath,
    Uint8List? imageBytes,
    String? imageName,
    double? latitude,
    double? longitude,
    DateTime? timestamp,
  }) async {
    try {
      final formMap = <String, dynamic>{
        'resolution_notes': resolutionNotes.trim(),
        if (latitude != null) 'resolution_latitude': latitude,
        if (longitude != null) 'resolution_longitude': longitude,
        if (timestamp != null) 'resolution_timestamp': timestamp.toIso8601String(),
      };

      if (imageBytes != null) {
        formMap['evidence_image'] = MultipartFile.fromBytes(
          imageBytes,
          filename: imageName ?? 'evidence.jpg',
        );
      } else if (imagePath != null && imagePath.isNotEmpty) {
        formMap['evidence_image'] = await MultipartFile.fromFile(
          imagePath,
          filename: imagePath.split('/').last,
        );
      }

      final formData = FormData.fromMap(formMap);

      final response = await _client.dio.post(
        '${ApiConstants.baseUrl}/civic-issues/$issueId/resolve',
        data: formData,
      );

      return CivicIssueModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<CivicIssueModel> updateStatus(
    int issueId, {
    required String status,
    String? comment,
  }) async {
    try {
      final response = await _client.dio.patch(
        '${ApiConstants.baseUrl}/civic-issues/$issueId/status',
        data: {
          'status': status,
          if (comment != null) 'comment': comment,
        },
      );
      return CivicIssueModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<CivicIssueModel> requestReopen(int issueId) async {
    try {
      final response = await _client.dio.post('${ApiConstants.baseUrl}/civic-issues/$issueId/reopen');
      return CivicIssueModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }
}
