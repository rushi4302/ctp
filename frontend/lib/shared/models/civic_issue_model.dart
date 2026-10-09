import 'user_model.dart';
import 'report_model.dart';
import '../../core/constants/api_constants.dart';

class CivicIssueStatusLogModel {
  final int id;
  final int civicIssueId;
  final int? changedById;
  final String previousStatus;
  final String newStatus;
  final String? comment;
  final DateTime createdAt;
  final UserModel? changedBy;

  CivicIssueStatusLogModel({
    required this.id,
    required this.civicIssueId,
    this.changedById,
    required this.previousStatus,
    required this.newStatus,
    this.comment,
    required this.createdAt,
    this.changedBy,
  });

  factory CivicIssueStatusLogModel.fromJson(Map<String, dynamic> json) {
    return CivicIssueStatusLogModel(
      id: json['id'] as int,
      civicIssueId: json['civic_issue_id'] as int? ?? 0,
      changedById: json['changed_by_id'] as int?,
      previousStatus: json['previous_status'] as String? ?? '',
      newStatus: json['new_status'] as String? ?? '',
      comment: json['comment'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      changedBy: json['changed_by'] != null
          ? UserModel.fromJson(json['changed_by'] as Map<String, dynamic>)
          : null,
    );
  }
}

class CivicIssueModel {
  final int id;
  final String title;
  final String description;
  final String category;
  final String status;
  final String severity;
  final double latitude;
  final double longitude;
  final String? address;
  final String? locality;
  final String? city;
  final String? district;
  final String? state;
  final String? postalCode;
  final String? ward;
  final int reportCount;
  final String? assignedDepartmentId;
  final int? assignedWorkerId;
  final UserModel? assignedWorker;
  final String? aiCategory;
  final double? aiConfidence;
  final String? resolutionNotes;
  final String? resolutionEvidenceUrl;
  final double? resolutionLatitude;
  final double? resolutionLongitude;
  final DateTime? resolutionTimestamp;
  final String? resolutionLocationStatus;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? resolvedAt;
  final DateTime? closedAt;

  // Details
  final List<ReportModel> reports;
  final List<CivicIssueStatusLogModel> statusLogs;

  CivicIssueModel({
    required this.id,
    required this.title,
    required this.description,
    required this.category,
    required this.status,
    required this.severity,
    required this.latitude,
    required this.longitude,
    this.address,
    this.locality,
    this.city,
    this.district,
    this.state,
    this.postalCode,
    this.ward,
    required this.reportCount,
    this.assignedDepartmentId,
    this.assignedWorkerId,
    this.assignedWorker,
    this.aiCategory,
    this.aiConfidence,
    this.resolutionNotes,
    this.resolutionEvidenceUrl,
    this.resolutionLatitude,
    this.resolutionLongitude,
    this.resolutionTimestamp,
    this.resolutionLocationStatus,
    required this.createdAt,
    required this.updatedAt,
    this.resolvedAt,
    this.closedAt,
    this.reports = const [],
    this.statusLogs = const [],
  });

  String? get fullResolutionEvidenceUrl {
    if (resolutionEvidenceUrl == null || resolutionEvidenceUrl!.isEmpty) return null;
    if (resolutionEvidenceUrl!.startsWith('http')) return resolutionEvidenceUrl;
    return '${ApiConstants.uploadsBaseUrl}$resolutionEvidenceUrl';
  }

  factory CivicIssueModel.fromJson(Map<String, dynamic> json) {
    return CivicIssueModel(
      id: json['id'] as int,
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? 'Other',
      status: json['status'] as String? ?? 'PENDING',
      severity: json['severity'] as String? ?? 'MEDIUM',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0.0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0.0,
      address: json['address'] as String?,
      locality: json['locality'] as String?,
      city: json['city'] as String?,
      district: json['district'] as String?,
      state: json['state'] as String?,
      postalCode: json['postal_code'] as String?,
      ward: json['ward'] as String?,
      reportCount: json['report_count'] as int? ?? 1,
      assignedDepartmentId: json['assigned_department_id'] as String?,
      assignedWorkerId: json['assigned_worker_id'] as int?,
      assignedWorker: json['assigned_worker'] != null
          ? UserModel.fromJson(json['assigned_worker'] as Map<String, dynamic>)
          : null,
      aiCategory: json['ai_category'] as String?,
      aiConfidence: (json['ai_confidence'] as num?)?.toDouble(),
      resolutionNotes: json['resolution_notes'] as String?,
      resolutionEvidenceUrl: json['resolution_evidence_url'] as String?,
      resolutionLatitude: (json['resolution_latitude'] as num?)?.toDouble(),
      resolutionLongitude: (json['resolution_longitude'] as num?)?.toDouble(),
      resolutionTimestamp: json['resolution_timestamp'] != null 
          ? DateTime.tryParse(json['resolution_timestamp'] as String) 
          : null,
      resolutionLocationStatus: json['resolution_location_status'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
      resolvedAt: json['resolved_at'] != null ? DateTime.tryParse(json['resolved_at'] as String) : null,
      closedAt: json['closed_at'] != null ? DateTime.tryParse(json['closed_at'] as String) : null,
      reports: (json['reports'] as List<dynamic>?)
              ?.map((r) => ReportModel.fromJson(r as Map<String, dynamic>))
              .toList() ??
          [],
      statusLogs: (json['status_logs'] as List<dynamic>?)
              ?.map((s) => CivicIssueStatusLogModel.fromJson(s as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
