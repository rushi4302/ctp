import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app/router/app_router.dart';
import 'core/constants/app_colors.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: CivicIntelligenceApp()));
}

class CivicIntelligenceApp extends StatelessWidget {
  const CivicIntelligenceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Civic Intelligence Platform',
      debugShowCheckedModeBanner: false,
      routerConfig: appRouter,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          primary: AppColors.primary,
          secondary: AppColors.secondary,
          surface: Colors.white,
        ),
        scaffoldBackgroundColor: AppColors.background,
        appBarTheme: const AppBarTheme(
          centerTitle: false,
          elevation: 0,
        ),
        cardTheme: const CardThemeData(
          color: Colors.white,
          surfaceTintColor: Colors.transparent,
          elevation: 1,
        ),

      ),
    );
  }
}
