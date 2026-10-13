import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../providers/report_provider.dart';
import '../../../shared/utils/complaint_presentation.dart';

class MyReportsScreen extends ConsumerStatefulWidget {
  const MyReportsScreen({super.key});

  @override
  ConsumerState<MyReportsScreen> createState() => _MyReportsScreenState();
}

class _MyReportsScreenState extends ConsumerState<MyReportsScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(reportListProvider.notifier).fetchMyReports());
  }

  @override
  Widget build(BuildContext context) {
    final reportState = ref.watch(reportListProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('My Reports'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(reportListProvider.notifier).fetchMyReports(),
        child: reportState.isLoading && reportState.myReports.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : reportState.myReports.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.assignment_late_outlined, size: 64, color: Colors.grey.shade400),
                        const SizedBox(height: 12),
                        Text(
                          "You haven't submitted any reports yet.",
                          style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () => context.push('/create-report'),
                          icon: const Icon(Icons.add),
                          label: const Text('Submit a Report'),
                        ),
                      ],
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: reportState.myReports.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final report = reportState.myReports[index];
                      final statusColor = AppColors.getStatusColor(report.status);

                      return Card(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          title: Text(
                            presentComplaintTitle(report.title, isSynthetic: report.isSynthetic),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: 4),
                              Text(report.category, style: const TextStyle(color: AppColors.primary, fontSize: 12)),
                              if (report.isSynthetic)
                                const Text(
                                  'Demonstration record',
                                  style: TextStyle(color: Colors.deepOrange, fontSize: 11),
                                ),
                              const SizedBox(height: 4),
                              Text(
                                '${report.createdAt.day}/${report.createdAt.month}/${report.createdAt.year}',
                                style: TextStyle(color: Colors.grey.shade500, fontSize: 11),
                              ),
                            ],
                          ),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: statusColor.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                                humanizeStatus(report.status),
                              style: TextStyle(
                                color: statusColor,
                                fontWeight: FontWeight.bold,
                                fontSize: 11,
                              ),
                            ),
                          ),
                          onTap: () => context.push('/reports/${report.id}'),
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}
