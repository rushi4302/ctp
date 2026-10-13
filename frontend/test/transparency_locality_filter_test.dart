import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/transparency_service.dart';
import 'package:frontend/features/transparency/screens/public_transparency_dashboard_screen.dart';

class _FakeTransparencyService extends TransparencyService {
  Map<String, dynamic> _stats(
    int issues, {
    required Map<String, int> localities,
  }) => {
    'data_notice': 'Test data',
    'total_unique_civic_issues': issues,
    'total_valid_reports': issues,
    'pending_issues': issues - 1,
    'assigned_issues': 0,
    'resolved_issues': 1,
    'closed_issues': 0,
    'in_progress_issues': 0,
    'resolution_rate': (100 / issues).toDouble(),
    'average_resolution_hours': null,
    'locality_distribution': localities,
  };

  Map<String, dynamic> _score(int issues, double score) => {
    'overall_score': score,
    'rating': 'GOOD',
    'total_issues_analyzed': issues,
    'data_notice': 'Test score',
    'components': {
      'resolution_rate': {
        'score': score,
        'description': 'Test component explanation',
      },
    },
  };

  @override
  Future<Map<String, dynamic>> getTransparencyStats({
    String? ward,
    String? locality,
  }) async {
    if (locality == 'Dhanori') return _stats(7, localities: {'Dhanori': 7});
    if (locality == 'Wagholi') return _stats(8, localities: {'Wagholi': 8});
    return _stats(15, localities: {'Dhanori': 7, 'Wagholi': 8});
  }

  @override
  Future<Map<String, dynamic>> getCivicHealthScore({
    String? ward,
    String? locality,
  }) async {
    if (locality == 'Dhanori') return _score(7, 76.6);
    if (locality == 'Wagholi') return _score(8, 71.4);
    return _score(15, 73.2);
  }
}

void main() {
  testWidgets(
    'locality selection scopes the dashboard and overall restores it',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: PublicTransparencyDashboardScreen(
            transparencyService: _FakeTransparencyService(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('All Localities (Overall)'), findsOneWidget);
      expect(find.text('Overall Platform Score'), findsOneWidget);
      expect(find.text('Dhanori'), findsWidgets);
      expect(find.text('Wagholi'), findsWidgets);
      expect(find.text('15'), findsOneWidget);

      await tester.tap(find.byType(DropdownButtonFormField<String?>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Dhanori').last);
      await tester.pumpAndSettle();

      expect(find.text('Dhanori Locality Score'), findsOneWidget);
      expect(find.text('Wagholi'), findsNothing);
    expect(find.textContaining('7 unique issues'), findsOneWidget);

      await tester.tap(find.byType(DropdownButtonFormField<String?>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('All Localities (Overall)').last);
      await tester.pumpAndSettle();

      expect(find.text('Overall Platform Score'), findsOneWidget);
      expect(find.text('Wagholi'), findsWidgets);
      expect(find.text('15'), findsOneWidget);
    },
  );
}
