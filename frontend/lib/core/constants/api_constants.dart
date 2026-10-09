import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';

class ApiConstants {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://10.147.150.33:8000/api/v1';
    }

    try {
      if (Platform.isAndroid) {
        return 'http://10.147.150.33:8000/api/v1';
      }
    } catch (_) {}

    return 'http://10.147.150.33:8000/api/v1';
  }

  static String get uploadsBaseUrl {
    if (kIsWeb) {
      return 'http://10.147.150.33:8000';
    }

    try {
      if (Platform.isAndroid) {
        return 'http://10.147.150.33:8000';
      }
    } catch (_) {}

    return 'http://10.147.150.33:8000';
  }

  // Auth
  static const String login = '/login';
  static const String register = '/register';
  static const String me = '/me';
  static const String forgotPassword = '/forgot-password';
  static const String resetPassword = '/reset-password';

  // Reports
  static const String reports = '/reports';
  static const String analyzeAI = '/reports/analyze-ai';

  // Municipality
  static const String municipalityStats = '/municipality/stats';
  static const String municipalityReports = '/municipality/reports';
}