import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/auth/screens/login_screen.dart';
import 'package:frontend/features/auth/screens/register_screen.dart';
import 'package:frontend/features/post/screens/create_report_screen.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('CivicIntelligenceApp renders MaterialApp', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: CivicIntelligenceApp()));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(MaterialApp), findsOneWidget);
  });

  testWidgets('LoginScreen renders email, password fields and action buttons', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: LoginScreen(),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Civic Intelligence'), findsOneWidget);
    expect(find.text('Email Address'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.byType(ElevatedButton), findsOneWidget);
    expect(find.text('Forgot Password?'), findsOneWidget);
    expect(find.text('Administrator / municipal staff sign in'), findsOneWidget);
  });

  testWidgets('Registration provides an explicit admin sign-in entry', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: RegisterScreen())),
    );
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Create Account'), findsOneWidget);
    expect(find.text('Administrator / municipal staff sign in'), findsOneWidget);
  });

  testWidgets('CreateReportScreen renders simplified field-reporting interface', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: CreateReportScreen(),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 200));

    // Verified present:
    expect(find.text('Report Civic Issue'), findsOneWidget);
    expect(find.text('Capture Photo of Issue'), findsOneWidget);
    expect(find.text('Choose from gallery'), findsOneWidget);
    expect(find.text('Description *'), findsOneWidget);
    expect(find.text('Issue category'), findsOneWidget);
    expect(find.text('Analyze photo with AI'), findsOneWidget);
    expect(find.text('Submit Civic Report'), findsOneWidget);

    // Title and severity remain server-derived/defaulted for this compact flow.
    expect(find.text('Title *'), findsNothing);
    expect(find.text('Severity'), findsNothing);
    expect(find.text('Get Current GPS'), findsNothing);
    expect(find.text('Address / Landmark'), findsNothing);
    expect(find.text('Ward #'), findsNothing);
  });
}
