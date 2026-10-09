import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/report_provider.dart';
import '../../../shared/models/report_model.dart';

class HomeDashboardScreen extends ConsumerStatefulWidget {
  const HomeDashboardScreen({super.key});

  @override
  ConsumerState<HomeDashboardScreen> createState() => _HomeDashboardScreenState();
}

class _HomeDashboardScreenState extends ConsumerState<HomeDashboardScreen> {
  final List<String> _categories = [
    'All',
    'Pothole/Road Damage',
    'Garbage',
    'Drainage Problem',
    'Water Leakage',
    'Streetlight Issue',
    'Traffic Issue',
    'Other',
  ];

  @override
  Widget build(BuildContext context) {
    final reportState = ref.watch(reportListProvider);
    final authState = ref.watch(authProvider);
    final user = authState.user;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Civic Intelligence',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.analytics_outlined),
            tooltip: 'Public Transparency',
            onPressed: () => context.push('/transparency'),
          ),
          IconButton(
            icon: const Icon(Icons.map_outlined),
            tooltip: 'Map View',
            onPressed: () => context.push('/map'),
          ),
          IconButton(
            icon: const Icon(Icons.bookmark_outline),
            tooltip: 'My Reports',
            onPressed: () => context.push('/my-reports'),
          ),
          if (user != null && user.isMunicipality)
            IconButton(
              icon: const Icon(Icons.admin_panel_settings_outlined),
              tooltip: 'Municipal Dashboard',
              onPressed: () => context.push('/municipality'),
            ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign Out',
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(reportListProvider.notifier).fetchReports(),
        child: Column(
          children: [
            // Welcome Header
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              color: AppColors.primary,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Welcome, ${user?.fullName ?? "Citizen"}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Report neighborhood issues for fast municipal resolution.',
                    style: TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ],
              ),
            ),

            // Category Filter Chips
            Container(
              height: 52,
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                scrollDirection: Axis.horizontal,
                itemCount: _categories.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, index) {
                  final cat = _categories[index];
                  final isSelected = cat == 'All'
                      ? reportState.selectedCategory == null
                      : reportState.selectedCategory == cat;

                  return FilterChip(
                    label: Text(cat),
                    selected: isSelected,
                    selectedColor: AppColors.primary.withOpacity(0.15),
                    checkmarkColor: AppColors.primary,
                    labelStyle: TextStyle(
                      color: isSelected ? AppColors.primary : AppColors.textPrimary,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      fontSize: 12,
                    ),
                    onSelected: (_) {
                      ref
                          .read(reportListProvider.notifier)
                          .filterCategory(cat == 'All' ? null : cat);
                    },
                  );
                },
              ),
            ),

            // Reports List
            Expanded(
              child: reportState.isLoading && reportState.reports.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : reportState.reports.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.inbox_outlined, size: 64, color: Colors.grey.shade400),
                              const SizedBox(height: 12),
                              Text(
                                'No civic reports found.',
                                style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: reportState.reports.length,
                          itemBuilder: (context, index) {
                            final report = reportState.reports[index];
                            return _ReportCard(report: report);
                          },
                        ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/create-report'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_a_photo),
        label: const Text('Report Issue', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
    );
  }
}

class _ReportCard extends ConsumerWidget {
  final ReportModel report;
  const _ReportCard({required this.report});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = AppColors.getStatusColor(report.status);

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      elevation: 1.5,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.push('/reports/${report.id}'),
        child: Padding(
          padding: const EdgeInsets.all(14.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header: Category and Status Badge
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      report.category,
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      report.status,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Title
              Text(
                report.title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 6),

              // Description preview
              Text(
                report.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: 10),

              // Image Thumbnail if available
              if (report.media.isNotEmpty) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: CachedNetworkImage(
                    imageUrl: report.media.first.fullUrl,
                    height: 140,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (_, __) => Container(
                      height: 140,
                      color: Colors.grey.shade200,
                      child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
                    ),
                    errorWidget: (_, __, ___) => Container(
                      height: 80,
                      color: Colors.grey.shade100,
                      child: const Icon(Icons.broken_image, color: Colors.grey),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
              ],

              // Footer: Location & Upvote button
              Row(
                children: [
                  const Icon(Icons.location_on_outlined, size: 14, color: AppColors.textSecondary),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      report.address ?? '${report.latitude.toStringAsFixed(4)}, ${report.longitude.toStringAsFixed(4)}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ),
                  InkWell(
                    borderRadius: BorderRadius.circular(20),
                    onTap: () {
                      ref.read(reportListProvider.notifier).toggleUpvote(report.id);
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      child: Row(
                        children: [
                          Icon(
                            report.hasUpvoted ? Icons.thumb_up : Icons.thumb_up_outlined,
                            size: 16,
                            color: report.hasUpvoted ? AppColors.primary : AppColors.textSecondary,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            report.upvotesCount.toString(),
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: report.hasUpvoted ? AppColors.primary : AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
