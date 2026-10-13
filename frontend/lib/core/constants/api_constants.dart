import 'package:flutter/foundation.dart';

class ApiConstants {
  static const String _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) {
      final configured = _configuredBaseUrl.replaceFirst(RegExp(r'/$'), '');
      return '$configured/api/v1';
    }
    // Android emulator host bridge; physical devices should pass their Mac's
    // Wi-Fi address with --dart-define=API_BASE_URL=http://<mac-ip>:8000.
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://127.0.0.1:8000/api/v1';
  }

  static String get uploadsBaseUrl {
    return baseUrl.replaceFirst('/api/v1', '');
  }

  // Auth
  static const String login = '/login';
  static const String register = '/register';
  static const String me = '/me';
  static const String userProfile = '/users/me';
  static const String forgotPassword = '/forgot-password';
  static const String resetPassword = '/reset-password';

  // Reports
  static const String reports = '/reports';
  static const String search = '/search';
  static const String analyzeAI = '/reports/analyze-ai';

  // Municipality
  static const String municipalityStats = '/municipality/stats';
  static const String municipalityReports = '/municipality/reports';
}
