import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../constants/api_constants.dart';
import '../network/api_client.dart';
import '../../shared/models/report_model.dart';

class ReportService {
  final ApiClient _client = ApiClient();

  Future<List<ReportModel>> searchReports({
    required String query,
    String? category,
    String? status,
    int skip = 0,
    int limit = 25,
  }) async {
    try {
      final response = await _client.dio.get(
        ApiConstants.search,
        queryParameters: {
          'q': query.trim(),
          'skip': skip,
          'limit': limit,
          if (category != null && category.isNotEmpty) 'category': category,
          if (status != null && status.isNotEmpty) 'status_filter': status,
        },
      );
      final list = response.data as List<dynamic>;
      return list
          .map((item) => ReportModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<List<ReportModel>> getReports({
    int skip = 0,
    int limit = 50,
    String? category,
    String? status,
    bool myReports = false,
    double? lat,
    double? lon,
    double? radiusKm,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'skip': skip,
        'limit': limit,
        if (category != null && category.isNotEmpty) 'category': category,
        if (status != null && status.isNotEmpty) 'status_filter': status,
        if (myReports) 'my_reports': true,
        if (lat != null) 'lat': lat,
        if (lon != null) 'lon': lon,
        if (radiusKm != null) 'radius_km': radiusKm,
      };

      final response = await _client.dio.get(
        ApiConstants.reports,
        queryParameters: queryParams,
      );

      final list = response.data as List<dynamic>;
      return list
          .map((item) => ReportModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<ReportModel> getReportById(int id) async {
    try {
      final response = await _client.dio.get('${ApiConstants.reports}/$id');
      return ReportModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<void> deleteReport(int id) async {
    try {
      await _client.dio.delete('${ApiConstants.reports}/$id');
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<ReportModel> createReport({
    String? title,
    required String description,
    String? category,
    String severity = 'MEDIUM',
    required double latitude,
    required double longitude,
    double? locationAccuracy,
    DateTime? captureTimestamp,
    String? address,
    String? locality,
    String? city,
    String? district,
    String? state,
    String? postalCode,
    String? ward,
    String? imagePath,
    Uint8List? imageBytes,
    String? imageName,
  }) async {
    try {
      final finalTitle = (title != null && title.trim().isNotEmpty)
          ? title.trim()
          : (description.trim().length > 60
                ? '${description.trim().substring(0, 57)}...'
                : description.trim());

      final Map<String, dynamic> formMap = {
        'title': finalTitle,
        'description': description.trim(),
        'severity': severity,
        'latitude': latitude.toString(),
        'longitude': longitude.toString(),
      };

      if (locationAccuracy != null) {
        formMap['location_accuracy'] = locationAccuracy.toString();
      }
      if (captureTimestamp != null) {
        formMap['capture_timestamp'] = captureTimestamp.toIso8601String();
      }
      if (category != null && category.isNotEmpty) {
        formMap['category'] = category;
      }
      if (address != null && address.isNotEmpty) {
        formMap['address'] = address;
      }
      if (locality != null && locality.isNotEmpty) {
        formMap['locality'] = locality;
      }
      if (city != null && city.isNotEmpty) {
        formMap['city'] = city;
      }
      if (district != null && district.isNotEmpty) {
        formMap['district'] = district;
      }
      if (state != null && state.isNotEmpty) {
        formMap['state'] = state;
      }
      if (postalCode != null && postalCode.isNotEmpty) {
        formMap['postal_code'] = postalCode;
      }
      if (ward != null && ward.isNotEmpty) {
        formMap['ward'] = ward;
      }

      if (imageBytes != null) {
        formMap['image'] = MultipartFile.fromBytes(
          imageBytes,
          filename: imageName ?? 'report_photo.jpg',
        );
      } else if (imagePath != null && imagePath.isNotEmpty) {
        formMap['image'] = await MultipartFile.fromFile(
          imagePath,
          filename: imagePath.split('/').last,
        );
      }

      final formData = FormData.fromMap(formMap);

      final response = await _client.dio.post(
        ApiConstants.reports,
        data: formData,
      );

      return ReportModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<ReportModel> updateStatus(
    int reportId, {
    required String status,
    String? comment,
    String? assignedDepartmentId,
    int? contractorId,
  }) async {
    try {
      final response = await _client.dio.patch(
        '${ApiConstants.reports}/$reportId/status',
        data: {
          'status': status,
          if (comment != null) 'comment': comment,
          if (assignedDepartmentId != null)
            'assigned_department_id': assignedDepartmentId,
          if (contractorId != null) 'contractor_id': contractorId,
        },
      );
      return ReportModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<CommentModel> addComment(int reportId, String content) async {
    try {
      final response = await _client.dio.post(
        '${ApiConstants.reports}/$reportId/comments',
        data: {'content': content.trim()},
      );
      return CommentModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<Map<String, dynamic>> toggleUpvote(int reportId) async {
    try {
      final response = await _client.dio.post(
        '${ApiConstants.reports}/$reportId/upvote',
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<Map<String, dynamic>> analyzeAI({
    String? text,
    String? imagePath,
    Uint8List? imageBytes,
    String? imageName,
  }) async {
    try {
      final formMap = <String, dynamic>{};
      if (text != null && text.isNotEmpty) {
        formMap['text'] = text;
      }
      if (imageBytes != null) {
        formMap['image'] = MultipartFile.fromBytes(
          imageBytes,
          filename: imageName ?? 'photo.jpg',
        );
      } else if (imagePath != null && imagePath.isNotEmpty) {
        formMap['image'] = await MultipartFile.fromFile(
          imagePath,
          filename: imagePath.split('/').last,
        );
      }

      final formData = FormData.fromMap(formMap);
      final response = await _client.dio.post(
        ApiConstants.analyzeAI,
        data: formData,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<Map<String, dynamic>> getMunicipalityStats() async {
    try {
      final response = await _client.dio.get(ApiConstants.municipalityStats);
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }
}
