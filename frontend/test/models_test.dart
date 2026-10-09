import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/shared/models/report_model.dart';
import 'package:frontend/shared/models/user_model.dart';

void main() {
  group('UserModel Tests', () {
    test('parses citizen role correctly', () {
      final json = {
        'id': 1,
        'email': 'citizen@pune.gov.in',
        'full_name': 'Ramesh Kumar',
        'role': 'citizen',
        'is_active': true,
      };
      final user = UserModel.fromJson(json);
      expect(user.id, 1);
      expect(user.email, 'citizen@pune.gov.in');
      expect(user.isCitizen, isTrue);
      expect(user.isMunicipality, isFalse);
    });

    test('parses municipality role correctly', () {
      final json = {
        'id': 2,
        'email': 'officer@pune.gov.in',
        'full_name': 'PMC Officer',
        'role': 'municipality',
      };
      final user = UserModel.fromJson(json);
      expect(user.isMunicipality, isTrue);
      expect(user.isCitizen, isFalse);
    });
  });

  group('ReportModel Tests', () {
    test('parses full report model with media and status logs', () {
      final json = {
        'id': 101,
        'title': 'Dangerous Pothole',
        'description': 'Near bridge, deep crater in tarmac',
        'category': 'Pothole/Road Damage',
        'status': 'VERIFIED',
        'severity': 'HIGH',
        'latitude': 18.5204,
        'longitude': 73.8567,
        'address': 'FC Road',
        'ward': 'Ward 5',
        'reporter_id': 1,
        'ai_category': 'Pothole/Road Damage',
        'ai_confidence': 0.985,
        'location_validation_status': 'VALID',
        'created_at': '2026-09-24T10:00:00Z',
        'updated_at': '2026-09-24T10:30:00Z',
        'upvotes_count': 5,
        'has_upvoted': true,
        'media': [
          {
            'id': 1,
            'report_id': 101,
            'file_url': '/uploads/photo123.jpg',
            'file_name': 'photo123.jpg',
            'file_type': 'image/jpeg',
            'file_size': 10240,
            'created_at': '2026-09-24T10:00:00Z',
          }
        ],
        'status_logs': [
          {
            'id': 1,
            'report_id': 101,
            'previous_status': 'NONE',
            'new_status': 'SUBMITTED',
            'comment': 'Submitted by citizen',
            'created_at': '2026-09-24T10:00:00Z',
          },
          {
            'id': 2,
            'report_id': 101,
            'previous_status': 'SUBMITTED',
            'new_status': 'VERIFIED',
            'comment': 'Verified by engineer',
            'created_at': '2026-09-24T10:30:00Z',
          }
        ],
      };

      final report = ReportModel.fromJson(json);
      expect(report.id, 101);
      expect(report.title, 'Dangerous Pothole');
      expect(report.status, 'VERIFIED');
      expect(report.hasUpvoted, isTrue);
      expect(report.upvotesCount, 5);
      expect(report.media.length, 1);
      expect(report.media.first.fullUrl, contains('/uploads/photo123.jpg'));
      expect(report.statusLogs.length, 2);
      expect(report.statusLogs.last.newStatus, 'VERIFIED');
    });

    test('parses structured location and timestamp metadata fields', () {
      final json = {
        'id': 102,
        'title': 'Broken Streetlight',
        'description': 'Streetlight flickering at intersection',
        'category': 'Streetlight Issue',
        'status': 'SUBMITTED',
        'severity': 'MEDIUM',
        'latitude': 18.5793,
        'longitude': 73.9821,
        'location_accuracy': 8.5,
        'capture_timestamp': '2026-09-25T12:30:45+05:30',
        'address': 'GH Raisoni College, Wagholi, Pune, Maharashtra 412207',
        'locality': 'Wagholi',
        'city': 'Pune',
        'district': 'Pune',
        'state': 'Maharashtra',
        'postal_code': '412207',
        'ward': 'Ward 12',
        'reporter_id': 1,
        'location_validation_status': 'VALID',
        'created_at': '2026-09-25T12:30:50Z',
        'updated_at': '2026-09-25T12:30:50Z',
        'media': [
          {
            'id': 2,
            'report_id': 102,
            'file_url': '/uploads/photo456.jpg',
            'file_name': 'photo456.jpg',
            'file_type': 'image/jpeg',
            'file_size': 20480,
            'capture_timestamp': '2026-09-25T12:30:45+05:30',
            'created_at': '2026-09-25T12:30:50Z',
          }
        ],
      };

      final report = ReportModel.fromJson(json);
      expect(report.id, 102);
      expect(report.latitude, 18.5793);
      expect(report.longitude, 73.9821);
      expect(report.locationAccuracy, 8.5);
      expect(report.captureTimestamp, isNotNull);
      expect(report.locality, 'Wagholi');
      expect(report.city, 'Pune');
      expect(report.state, 'Maharashtra');
      expect(report.postalCode, '412207');
      expect(report.media.first.captureTimestamp, isNotNull);
    });

    test('parses civic_issue_id, moderation_status and rejection_reason correctly', () {
      final json = {
        'id': 103,
        'title': 'Test Report with Civic Issue',
        'description': 'Description of civic problem',
        'category': 'Garbage',
        'status': 'REJECTED',
        'severity': 'LOW',
        'latitude': 18.5204,
        'longitude': 73.8567,
        'reporter_id': 1,
        'civic_issue_id': 42,
        'moderation_status': 'REJECTED',
        'rejection_reason': 'Duplicate spam submission',
        'rejected_at': '2026-09-25T14:00:00Z',
        'location_validation_status': 'VALID',
        'created_at': '2026-09-25T13:00:00Z',
        'updated_at': '2026-09-25T14:00:00Z',
      };

      final report = ReportModel.fromJson(json);
      expect(report.id, 103);
      expect(report.civicIssueId, 42);
      expect(report.moderationStatus, 'REJECTED');
      expect(report.rejectionReason, 'Duplicate spam submission');
      expect(report.rejectedAt, isNotNull);
    });
  });
}

