import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:go_router/go_router.dart';

import '../../core/storage/token_storage.dart';
import '../../features/auth/screens/forgot_password_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/auth/screens/profile_screen.dart';
import '../../features/feed/screens/home_dashboard_screen.dart';
import '../../features/feed/screens/my_reports_screen.dart';
import '../../features/feed/screens/report_detail_screen.dart';
import '../../features/maps/screens/reports_map_screen.dart';
import '../../features/municipality/screens/municipality_dashboard_screen.dart';
import '../../features/post/screens/create_report_screen.dart';
import '../../features/transparency/screens/public_transparency_dashboard_screen.dart';
import '../../features/public/screens/landing_screen.dart';

final appRouter = GoRouter(
  initialLocation: kIsWeb ? '/' : '/home',
  redirect: (context, state) async {
    final token = await TokenStorage.getToken();
    final isAuth = token != null && token.isNotEmpty;
    final isLoggingIn = state.matchedLocation == '/login' ||
        state.matchedLocation == '/admin-login' ||
        state.matchedLocation == '/register' ||
        state.matchedLocation == '/forgot-password';
    final isPublicPage = state.matchedLocation == '/' ||
        state.matchedLocation == '/transparency' ||
        state.matchedLocation == '/map';

    if (!isAuth && !isLoggingIn && !isPublicPage) {
      return '/login';
    }

    final role = isAuth ? await TokenStorage.getUserRole() : null;
    if (isAuth && state.matchedLocation == '/') {
      return role == 'municipality' || role == 'admin' ? '/municipality' : '/home';
    }

    if (isAuth && state.matchedLocation == '/municipality' && role != 'municipality' && role != 'admin') {
      return '/home';
    }

    if (isAuth && isLoggingIn) {
      final role = await TokenStorage.getUserRole();
      if (role == 'municipality' || role == 'admin') {
        return '/municipality';
      }
      return '/home';
    }

    return null;
  },
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const LandingScreen(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/admin-login',
      builder: (context, state) => const LoginScreen(adminEntry: true),
    ),
    GoRoute(
      path: '/register',
      builder: (context, state) => const RegisterScreen(),
    ),
    GoRoute(
      path: '/forgot-password',
      builder: (context, state) => const ForgotPasswordScreen(),
    ),
    GoRoute(
      path: '/profile',
      builder: (context, state) => const ProfileScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) => const HomeDashboardScreen(),
    ),
    GoRoute(
      path: '/create-report',
      builder: (context, state) => const CreateReportScreen(),
    ),
    GoRoute(
      path: '/reports/:id',
      builder: (context, state) {
        final id = int.tryParse(state.pathParameters['id'] ?? '0') ?? 0;
        return ReportDetailScreen(reportId: id);
      },
    ),
    GoRoute(
      path: '/my-reports',
      builder: (context, state) => const MyReportsScreen(),
    ),
    GoRoute(
      path: '/map',
      builder: (context, state) => const ReportsMapScreen(),
    ),
    GoRoute(
      path: '/municipality',
      builder: (context, state) => const MunicipalityDashboardScreen(),
    ),
    GoRoute(
      path: '/transparency',
      builder: (context, state) => const PublicTransparencyDashboardScreen(),
    ),
  ],
);
