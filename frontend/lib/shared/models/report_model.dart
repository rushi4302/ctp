import 'user_model.dart';
import '../../core/constants/api_constants.dart';

class MediaModel {
  final int id;
  final int reportId;
  final String fileUrl;
  final String fileName;
  final String fileType;
  final int fileSize;
  final double? exifLatitude;
  final double? exifLongitude;
  final DateTime? exifTimestamp;
  final DateTime? captureTimestamp;
  final DateTime createdAt;

  MediaModel({
    required this.id,
    required this.reportId,
    required this.fileUrl,
    required this.fileName,
    required this.fileType,
    required this.fileSize,
    this.exifLatitude,
    this.exifLongitude,
    this.exifTimestamp,
    this.captureTimestamp,
    required this.createdAt,
  });

  String get fullUrl {
    if (fileUrl.startsWith('http')) return fileUrl;
    return '${ApiConstants.uploadsBaseUrl}$fileUrl';
  }

  factory MediaModel.fromJson(Map<String, dynamic> json) {
    return MediaModel(
      id: json['id'] as int,
      reportId: json['report_id'] as int? ?? 0,
      fileUrl: json['file_url'] as String? ?? '',
      fileName: json['file_name'] as String? ?? '',
      fileType: json['file_type'] as String? ?? '',
      fileSize: json['file_size'] as int? ?? 0,
      exifLatitude: (json['exif_latitude'] as num?)?.toDouble(),
      exifLongitude: (json['exif_longitude'] as num?)?.toDouble(),
      exifTimestamp: json['exif_timestamp'] != null
          ? DateTime.tryParse(json['exif_timestamp'] as String)
          : null,
      captureTimestamp: json['capture_timestamp'] != null
          ? DateTime.tryParse(json['capture_timestamp'] as String)
          : null,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class StatusLogModel {
  final int id;
  final int reportId;
  final int? changedById;
  final String previousStatus;
  final String newStatus;
  final String? comment;
  final DateTime createdAt;
  final UserModel? changedBy;

  StatusLogModel({
    required this.id,
    required this.reportId,
    this.changedById,
    required this.previousStatus,
    required this.newStatus,
    this.comment,
    required this.createdAt,
    this.changedBy,
  });

  factory StatusLogModel.fromJson(Map<String, dynamic> json) {
    return StatusLogModel(
      id: json['id'] as int,
      reportId: json['report_id'] as int? ?? 0,
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

class CommentModel {
  final int id;
  final int reportId;
  final int userId;
  final String content;
  final DateTime createdAt;
  final UserModel? user;

  CommentModel({
    required this.id,
    required this.reportId,
    required this.userId,
    required this.content,
    required this.createdAt,
    this.user,
  });

  factory CommentModel.fromJson(Map<String, dynamic> json) {
    return CommentModel(
      id: json['id'] as int,
      reportId: json['report_id'] as int? ?? 0,
      userId: json['user_id'] as int? ?? 0,
      content: json['content'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      user: json['user'] != null
          ? UserModel.fromJson(json['user'] as Map<String, dynamic>)
          : null,
    );
  }
}

class ReportModel {
  final int id;
  final String title;
  final String description;
  final String category;
  final String status;
  final String severity;
  final double latitude;
  final double longitude;
  final double? locationAccuracy;
  final DateTime? captureTimestamp;
  final String? address;
  final String? locality;
  final String? city;
  final String? district;
  final String? state;
  final String? postalCode;
  final String? ward;
  final int reporterId;
  final String? assignedDepartmentId;
  final int? contractorId;
  final String? aiCategory;
  final double? aiConfidence;
  final String locationValidationStatus;
  final DateTime createdAt;
  final DateTime updatedAt;
  int upvotesCount;
  bool hasUpvoted;
  final int? civicIssueId;
  final String moderationStatus;
  final String? rejectionReason;
  final DateTime? rejectedAt;
  final List<MediaModel> media;

  final UserModel? reporter;
  final List<CommentModel> comments;
  final List<StatusLogModel> statusLogs;

  ReportModel({
    required this.id,
    required this.title,
    required this.description,
    required this.category,
    required this.status,
    required this.severity,
    required this.latitude,
    required this.longitude,
    this.locationAccuracy,
    this.captureTimestamp,
    this.address,
    this.locality,
    this.city,
    this.district,
    this.state,
    this.postalCode,
    this.ward,
    required this.reporterId,
    this.assignedDepartmentId,
    this.contractorId,
    this.aiCategory,
    this.aiConfidence,
    required this.locationValidationStatus,
    required this.createdAt,
    required this.updatedAt,
    this.upvotesCount = 0,
    this.hasUpvoted = false,
    this.civicIssueId,
    this.moderationStatus = 'ACTIVE',
    this.rejectionReason,
    this.rejectedAt,
    this.media = const [],
    this.reporter,
    this.comments = const [],
    this.statusLogs = const [],
  });


  factory ReportModel.fromJson(Map<String, dynamic> json) {
    return ReportModel(
      id: json['id'] as int,
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? 'Other',
      status: json['status'] as String? ?? 'SUBMITTED',
      severity: json['severity'] as String? ?? 'MEDIUM',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0.0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0.0,
      locationAccuracy: (json['location_accuracy'] as num?)?.toDouble(),
      captureTimestamp: json['capture_timestamp'] != null
          ? DateTime.tryParse(json['capture_timestamp'] as String)
          : null,
      address: json['address'] as String?,
      locality: json['locality'] as String?,
      city: json['city'] as String?,
      district: json['district'] as String?,
      state: json['state'] as String?,
      postalCode: json['postal_code'] as String?,
      ward: json['ward'] as String?,
      reporterId: json['reporter_id'] as int? ?? 0,
      assignedDepartmentId: json['assigned_department_id'] as String?,
      contractorId: json['contractor_id'] as int?,
      aiCategory: json['ai_category'] as String?,
      aiConfidence: (json['ai_confidence'] as num?)?.toDouble(),
      locationValidationStatus: json['location_validation_status'] as String? ?? 'VALID',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
      upvotesCount: json['upvotes_count'] as int? ?? 0,
      hasUpvoted: json['has_upvoted'] as bool? ?? false,
      civicIssueId: json['civic_issue_id'] as int?,
      moderationStatus: json['moderation_status'] as String? ?? 'ACTIVE',
      rejectionReason: json['rejection_reason'] as String?,
      rejectedAt: json['rejected_at'] != null
          ? DateTime.tryParse(json['rejected_at'] as String)
          : null,
      media: (json['media'] as List<dynamic>?)
              ?.map((m) => MediaModel.fromJson(m as Map<String, dynamic>))
              .toList() ??
          [],
      reporter: json['reporter'] != null
          ? UserModel.fromJson(json['reporter'] as Map<String, dynamic>)
          : null,
      comments: (json['comments'] as List<dynamic>?)
              ?.map((c) => CommentModel.fromJson(c as Map<String, dynamic>))
              .toList() ??
          [],
      statusLogs: (json['status_logs'] as List<dynamic>?)
              ?.map((s) => StatusLogModel.fromJson(s as Map<String, dynamic>))
              .toList() ??
          [],
    );

  }
}
