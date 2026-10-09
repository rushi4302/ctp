import 'package:flutter/material.dart';

class AppColors {
  // Brand Primary & Accent
  static const Color primary = Color(0xFF0F766E); // Deep Teal
  static const Color primaryLight = Color(0xFF14B8A6);
  static const Color primaryDark = Color(0xFF115E59);
  static const Color secondary = Color(0xFF0369A1); // Civic Blue

  // Status Colors
  static const Color statusSubmitted = Color(0xFF64748B); // Slate Gray
  static const Color statusVerified = Color(0xFF0284C7); // Sky Blue
  static const Color statusInProgress = Color(0xFFD97706); // Amber
  static const Color statusResolved = Color(0xFF16A34A); // Emerald Green
  static const Color statusRejected = Color(0xFFDC2626); // Crimson Red
  static const Color statusFlagged = Color(0xFF9333EA); // Purple

  // Severity Colors
  static const Color severityLow = Color(0xFF10B981);
  static const Color severityMedium = Color(0xFFF59E0B);
  static const Color severityHigh = Color(0xFFF97316);
  static const Color severityCritical = Color(0xFFEF4444);

  // Backgrounds & Neutrals
  static const Color background = Color(0xFFF8FAFC);
  static const Color cardSurface = Colors.white;
  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF64748B);
  static const Color border = Color(0xFFE2E8F0);

  static Color getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'SUBMITTED':
        return statusSubmitted;
      case 'VERIFIED':
        return statusVerified;
      case 'IN_PROGRESS':
        return statusInProgress;
      case 'RESOLVED':
        return statusResolved;
      case 'REJECTED':
        return statusRejected;
      case 'FLAGGED':
        return statusFlagged;
      default:
        return textSecondary;
    }
  }

  static Color getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'LOW':
        return severityLow;
      case 'MEDIUM':
        return severityMedium;
      case 'HIGH':
        return severityHigh;
      case 'CRITICAL':
        return severityCritical;
      default:
        return severityMedium;
    }
  }
}
