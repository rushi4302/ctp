import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/app_colors.dart';

class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 760;
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.location_city_rounded, color: AppColors.primary),
            SizedBox(width: 10),
            Text('Civic Intelligence', style: TextStyle(fontWeight: FontWeight.w800)),
          ],
        ),
        actions: wide
            ? [
                TextButton(onPressed: () => context.push('/transparency'), child: const Text('Transparency')),
                TextButton(onPressed: () => context.push('/login'), child: const Text('Sign in')),
                TextButton(onPressed: () => context.push('/admin-login'), child: const Text('Admin')),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: FilledButton(onPressed: () => context.push('/register'), child: const Text('Create account')),
                ),
              ]
            : [
                IconButton(tooltip: 'Transparency', onPressed: () => context.push('/transparency'), icon: const Icon(Icons.insights_outlined)),
                IconButton(tooltip: 'Sign in', onPressed: () => context.push('/login'), icon: const Icon(Icons.login)),
                IconButton(tooltip: 'Administrator sign in', onPressed: () => context.push('/admin-login'), icon: const Icon(Icons.admin_panel_settings_outlined)),
                IconButton(tooltip: 'Create account', onPressed: () => context.push('/register'), icon: const Icon(Icons.person_add_alt_1)),
              ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            Container(
              width: double.infinity,
              color: const Color(0xFFF1F6F5),
              padding: EdgeInsets.symmetric(horizontal: wide ? 72 : 24, vertical: wide ? 84 : 52),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1120),
                  child: Flex(
                    direction: wide ? Axis.horizontal : Axis.vertical,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        flex: wide ? 6 : 0,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('A clearer view of local issues', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
                            const SizedBox(height: 16),
                            Text(
                              'Report it.\nTrack what happens.',
                              style: TextStyle(fontSize: wide ? 54 : 40, height: 1.08, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
                            ),
                            const SizedBox(height: 18),
                            const Text(
                              'Help make civic problems visible with location-aware reports, public status updates, and transparent community data.',
                              style: TextStyle(fontSize: 17, height: 1.55, color: AppColors.textSecondary),
                            ),
                            const SizedBox(height: 28),
                            Wrap(spacing: 12, runSpacing: 12, children: [
                              FilledButton.icon(
                                onPressed: () => context.push('/register'),
                                icon: const Icon(Icons.add_a_photo_outlined),
                                label: const Text('Report an issue'),
                              ),
                              OutlinedButton.icon(
                                onPressed: () => context.push('/transparency'),
                                icon: const Icon(Icons.insights_outlined),
                                label: const Text('Explore public data'),
                              ),
                            ]),
                          ],
                        ),
                      ),
                      if (wide) const SizedBox(width: 56),
                      if (wide)
                        Expanded(
                          flex: 5,
                          child: Container(
                            height: 320,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(28),
                              border: Border.all(color: const Color(0xFFE1EAE8)),
                            ),
                            child: const Center(
                              child: Column(mainAxisSize: MainAxisSize.min, children: [
                                Icon(Icons.map_outlined, size: 92, color: AppColors.primary),
                                SizedBox(height: 16),
                                Text('Community reports and progress', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
                                SizedBox(height: 6),
                                Text('Explore current data in the public dashboard', style: TextStyle(color: AppColors.textSecondary)),
                              ]),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: wide ? 72 : 24, vertical: 48),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1120),
                child: Wrap(
                  spacing: 20,
                  runSpacing: 20,
                  children: const [
                    _FeatureCard(icon: Icons.camera_alt_outlined, title: 'Report with context', body: 'Attach evidence and a location so neighbors and authorities can understand the issue.'),
                    _FeatureCard(icon: Icons.timeline_outlined, title: 'Follow the timeline', body: 'See recorded status changes and available resolution evidence.'),
                    _FeatureCard(icon: Icons.query_stats_outlined, title: 'Inspect public data', body: 'Review counts and performance metrics calculated from available reports.'),
                  ],
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.all(20),
              child: Text('Civic Intelligence • Public reporting and transparency', style: TextStyle(color: AppColors.textSecondary)),
            ),
          ],
        ),
      ),
    );
  }
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard({required this.icon, required this.title, required this.body});
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: MediaQuery.sizeOf(context).width < 380 ? MediaQuery.sizeOf(context).width - 48 : 340,
        child: Card(
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18), side: const BorderSide(color: Color(0xFFE6ECEB))),
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(icon, color: AppColors.primary, size: 28),
              const SizedBox(height: 14),
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
              const SizedBox(height: 8),
              Text(body, style: const TextStyle(height: 1.45, color: AppColors.textSecondary)),
            ]),
          ),
        ),
      );
}
