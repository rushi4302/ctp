import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../core/constants/app_colors.dart';

import '../../../core/services/report_service.dart';
import '../../../core/services/civic_issue_service.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/report_provider.dart';
import '../../../shared/models/report_model.dart';
import '../../../shared/utils/complaint_presentation.dart';
import '../../maps/screens/single_location_map_screen.dart';
import '../../municipality/screens/civic_issue_detail_screen.dart';

class ReportDetailScreen extends ConsumerStatefulWidget {
  final int reportId;
  const ReportDetailScreen({super.key, required this.reportId});

  @override
  ConsumerState<ReportDetailScreen> createState() => _ReportDetailScreenState();
}

class _ReportDetailScreenState extends ConsumerState<ReportDetailScreen> {
  final _reportService = ReportService();
  final _commentController = TextEditingController();

  ReportModel? _report;
  bool _isLoading = true;
  String? _error;
  bool _isPostingComment = false;
  bool _isDeleting = false;

  @override
  void initState() {
    super.initState();
    _fetchDetail();
  }

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _fetchDetail() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final data = await _reportService.getReportById(widget.reportId);
      setState(() {
        _report = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _toggleUpvote() async {
    if (_report == null) return;
    try {
      final res = await _reportService.toggleUpvote(_report!.id);
      setState(() {
        _report!.hasUpvoted = res['has_upvoted'] as bool? ?? false;
        _report!.upvotesCount = res['total_upvotes'] as int? ?? 0;
      });
      ref.read(reportListProvider.notifier).fetchReports();
    } catch (_) {}
  }

  Future<void> _addComment() async {
    final text = _commentController.text.trim();
    if (text.isEmpty || _report == null) return;

    setState(() => _isPostingComment = true);
    try {
      await _reportService.addComment(_report!.id, text);
      _commentController.clear();
      _fetchDetail();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to post comment: $e')),
      );
    } finally {
      setState(() => _isPostingComment = false);
    }
  }

  Future<void> _deleteReport() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete complaint?'),
        content: const Text('This permanently removes the complaint and its comments, votes, status history, and attached images.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true || _report == null) return;

    setState(() => _isDeleting = true);
    try {
      await _reportService.deleteReport(_report!.id);
      ref.read(reportListProvider.notifier).fetchReports();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Complaint deleted.')),
      );
      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;
      setState(() => _isDeleting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not delete complaint: $error')),
      );
    }
  }

  void _showStatusDialog() {
    String selectedStatus = _report!.status;
    final commentCtrl = TextEditingController();
    final deptCtrl = TextEditingController(text: _report!.assignedDepartmentId ?? '');

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Update Report Status'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                DropdownButtonFormField<String>(
                  value: selectedStatus,
                  decoration: const InputDecoration(labelText: 'Status'),
                  items: const [
                    DropdownMenuItem(value: 'SUBMITTED', child: Text('Submitted')),
                    DropdownMenuItem(value: 'VERIFIED', child: Text('Verified')),
                    DropdownMenuItem(value: 'IN_PROGRESS', child: Text('In Progress')),
                    DropdownMenuItem(value: 'RESOLVED', child: Text('Resolved')),
                    DropdownMenuItem(value: 'REJECTED', child: Text('Rejected')),
                    DropdownMenuItem(value: 'FLAGGED', child: Text('Flagged')),
                  ],
                  onChanged: (val) {
                    if (val != null) setDialogState(() => selectedStatus = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: commentCtrl,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Official Remark / Comment',
                    hintText: 'Reason or work update...',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: deptCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Assigned Department',
                    hintText: 'e.g. Roads & Bridges, Sanitation',
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white),
              onPressed: () async {
                Navigator.pop(ctx);
                try {
                  await _reportService.updateStatus(
                    _report!.id,
                    status: selectedStatus,
                    comment: commentCtrl.text.trim().isNotEmpty ? commentCtrl.text.trim() : null,
                    assignedDepartmentId: deptCtrl.text.trim().isNotEmpty ? deptCtrl.text.trim() : null,
                  );
                  _fetchDetail();
                  ref.read(reportListProvider.notifier).fetchReports();
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
                    );
                  }
                }
              },
              child: const Text('Update'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState.user;
    final isAuthority = user != null && user.isMunicipality;
    final canDelete = user != null &&
        (user.isAdmin ||
            (user.isCitizen &&
                user.id == _report?.reporterId &&
                _report?.status.toUpperCase() == 'SUBMITTED'));

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Report Detail')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _report == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Report Detail')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error ?? 'Report not found.'),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: _fetchDetail, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    final report = _report!;
    final statusColor = AppColors.getStatusColor(report.status);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(presentComplaintTitle(report.title, isSynthetic: report.isSynthetic), maxLines: 1, overflow: TextOverflow.ellipsis),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          if (canDelete)
            IconButton(
              icon: _isDeleting
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.delete_outline),
              tooltip: 'Delete complaint',
              onPressed: _isDeleting ? null : _deleteReport,
            ),
          if (isAuthority)
            IconButton(
              icon: const Icon(Icons.edit_note),
              tooltip: 'Update Status',
              onPressed: _showStatusDialog,
            ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Image Preview
            if (report.media.isNotEmpty)
              CachedNetworkImage(
                imageUrl: report.media.first.fullUrl,
                height: 250,
                width: double.infinity,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(
                  height: 250,
                  color: Colors.grey.shade200,
                  child: const Center(child: CircularProgressIndicator()),
                ),
                errorWidget: (_, __, ___) => Container(
                  height: 150,
                  color: Colors.grey.shade100,
                  child: const Icon(Icons.broken_image, size: 48, color: Colors.grey),
                ),
              ),

            Padding(
              padding: const EdgeInsets.all(18.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Badges: Status, Category, Severity
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: statusColor.withOpacity(0.5)),
                        ),
                        child: Text(
                          humanizeStatus(report.status),
                          style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          report.category,
                          style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold, fontSize: 12),
                        ),
                      ),
                      const Spacer(),
                      InkWell(
                        onTap: _toggleUpvote,
                        borderRadius: BorderRadius.circular(20),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: report.hasUpvoted ? AppColors.primary : Colors.grey.shade100,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                report.hasUpvoted ? Icons.thumb_up : Icons.thumb_up_outlined,
                                size: 16,
                                color: report.hasUpvoted ? Colors.white : AppColors.textSecondary,
                              ),
                              const SizedBox(width: 5),
                              Text(
                                '${report.upvotesCount}',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: report.hasUpvoted ? Colors.white : AppColors.textPrimary,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Title & Description
                  Text(
                    presentComplaintTitle(report.title, isSynthetic: report.isSynthetic),
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    presentComplaintDescription(report.description, isSynthetic: report.isSynthetic),
                    style: const TextStyle(fontSize: 15, height: 1.4, color: AppColors.textSecondary),
                  ),
                  if (report.isSynthetic || report.relatedReportCount > 1) ...[
                    const SizedBox(height: 12),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: report.isSynthetic ? Colors.orange.shade50 : Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        report.isSynthetic
                            ? 'Synthetic demonstration record — not an official or citizen submission.'
                            : 'This report is linked to a related civic issue with ${report.relatedReportCount} reports. Reports remain individually tracked.',
                        style: TextStyle(color: report.isSynthetic ? Colors.deepOrange.shade900 : Colors.indigo.shade900),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),

                  // AI Analysis Card
                  if (report.aiCategory != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: Colors.blue.shade200),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.auto_awesome, color: Colors.blueAccent, size: 24),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'AI Classification',
                                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.blueGrey),
                                ),
                                Text(
                                  'Predicted Category: ${report.aiCategory} (${((report.aiConfidence ?? 0.0) * 100).toStringAsFixed(1)}% confidence)',
                                  style: const TextStyle(fontSize: 12, color: Colors.blueAccent, fontWeight: FontWeight.w600),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Associated Civic Issue & Moderation Notice Card
                  if (report.civicIssueId != null || report.moderationStatus == 'REJECTED') ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: report.moderationStatus == 'REJECTED'
                            ? Colors.red.shade50
                            : Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: report.moderationStatus == 'REJECTED'
                              ? Colors.red.shade200
                              : Colors.indigo.shade200,
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            report.moderationStatus == 'REJECTED'
                                ? Icons.warning_amber_rounded
                                : Icons.hub_outlined,
                            color: report.moderationStatus == 'REJECTED'
                                ? Colors.red.shade700
                                : Colors.indigo.shade700,
                            size: 24,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  report.moderationStatus == 'REJECTED'
                                      ? 'Report Moderated / Rejected'
                                      : 'Associated Civic Issue #${report.civicIssueId}',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 13,
                                    color: report.moderationStatus == 'REJECTED'
                                        ? Colors.red.shade900
                                        : Colors.indigo.shade900,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  report.moderationStatus == 'REJECTED'
                                      ? (report.rejectionReason ?? 'Hidden from public feed by platform moderators.')
                                      : 'Linked to the municipal operational problem workflow.',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: report.moderationStatus == 'REJECTED'
                                        ? Colors.red.shade800
                                        : Colors.indigo.shade700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],


                  // Location & EXIF Metadata
                  Card(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    elevation: 0.5,
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.location_on, size: 20, color: AppColors.primary),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  report.address ?? '${report.latitude.toStringAsFixed(5)}, ${report.longitude.toStringAsFixed(5)}',
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                ),
                              ),
                            ],
                          ),
                          if (locationMetadataNotice(
                                report.locationValidationStatus,
                                isSynthetic: report.isSynthetic,
                              )
                              case final notice?) ...[
                            const SizedBox(height: 8),
                            Text(
                              notice,
                              style: TextStyle(
                                fontSize: 12,
                                color: report.isSynthetic
                                    ? Colors.deepOrange.shade800
                                    : Colors.amber.shade900,
                              ),
                            ),
                          ],
                          const Divider(height: 18),
                          if (report.captureTimestamp != null) ...[
                            Row(
                              children: [
                                const Icon(Icons.access_time, size: 14, color: AppColors.textSecondary),
                                const SizedBox(width: 6),
                                Text(
                                  'Captured: ${DateFormat('d MMM yyyy, hh:mm a').format(report.captureTimestamp!)}',
                                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                          ],
                          if (report.locality != null || report.city != null) ...[
                            Row(
                              children: [
                                const Icon(Icons.location_city, size: 14, color: AppColors.textSecondary),
                                const SizedBox(width: 6),
                                Text(
                                  [
                                    if (report.locality != null) report.locality,
                                    if (report.city != null) report.city,
                                  ].join(', '),
                                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                          ],
                          Row(
                            children: [
                              const Icon(Icons.my_location, size: 14, color: AppColors.textSecondary),
                              const SizedBox(width: 6),
                              Text(
                                '${report.latitude.toStringAsFixed(6)}, ${report.longitude.toStringAsFixed(6)}',
                                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                              ),
                              if (report.locationAccuracy != null) ...[
                                const SizedBox(width: 8),
                                Text(
                                  '(±${report.locationAccuracy!.toStringAsFixed(1)} m)',
                                  style: TextStyle(fontSize: 11, color: Colors.teal.shade700, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ],
                          ),
                          if (report.ward != null) ...[
                            const SizedBox(height: 6),
                            Text('Ward: ${report.ward}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                          ],
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => SingleLocationMapScreen(
                                      latitude: report.latitude,
                                      longitude: report.longitude,
                                      title: presentComplaintTitle(report.title, isSynthetic: report.isSynthetic),
                                      snippet: report.address ?? '${report.latitude.toStringAsFixed(4)}, ${report.longitude.toStringAsFixed(4)}',
                                      status: report.status,
                                    ),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.map, size: 18),
                              label: const Text('View on Map'),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: AppColors.primary,
                                side: const BorderSide(color: AppColors.primary),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                              ),
                            ),
                          ),
                          if (report.civicIssueId != null) ...[
                            const SizedBox(height: 12),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => CivicIssueDetailScreen(issueId: report.civicIssueId!),
                                    ),
                                  );
                                },
                                icon: const Icon(Icons.verified),
                                label: const Text('View Official Resolution Details'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.green.shade700,
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                              ),
                            ),
                          ],
                          if (report.civicIssueId != null && (report.status == 'RESOLVED' || report.status == 'CLOSED')) ...[
                            const SizedBox(height: 12),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                onPressed: () async {
                                  final confirm = await showDialog<bool>(
                                    context: context,
                                    builder: (ctx) => AlertDialog(
                                      title: const Text('Still Not Resolved?'),
                                      content: const Text('If the issue still exists, you can request it to be reopened.'),
                                      actions: [
                                        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                                        ElevatedButton(
                                          onPressed: () => Navigator.pop(ctx, true), 
                                          style: ElevatedButton.styleFrom(backgroundColor: Colors.orange, foregroundColor: Colors.white),
                                          child: const Text('Request Reopen')
                                        ),
                                      ],
                                    ),
                                  );
                                  if (confirm == true) {
                                    try {
                                      await CivicIssueService().requestReopen(report.civicIssueId!);
                                      await _fetchDetail();
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Issue reopened successfully.')));
                                      }
                                    } catch (e) {
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                                      }
                                    }
                                  }
                                },
                                icon: const Icon(Icons.refresh),
                                label: const Text('Still Not Resolved?'),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: Colors.orange.shade800,
                                  side: BorderSide(color: Colors.orange.shade800),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Chronological Status Timeline
                  const Text(
                    'Status Timeline',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: 12),
                  if (report.statusLogs.isEmpty)
                    const Text('No status transitions recorded yet.', style: TextStyle(color: AppColors.textSecondary, fontSize: 13))
                  else
                    ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: report.statusLogs.length,
                      itemBuilder: (context, index) {
                        final log = report.statusLogs[index];
                        final logColor = AppColors.getStatusColor(log.newStatus);

                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Column(
                              children: [
                                CircleAvatar(radius: 6, backgroundColor: logColor),
                                if (index < report.statusLogs.length - 1)
                                  Container(width: 2, height: 40, color: Colors.grey.shade300),
                              ],
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Padding(
                                padding: const EdgeInsets.only(bottom: 12.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text(
                                          humanizeStatus(log.newStatus),
                                          style: TextStyle(fontWeight: FontWeight.bold, color: logColor, fontSize: 13),
                                        ),
                                        Text(
                                          '${log.createdAt.hour}:${log.createdAt.minute.toString().padLeft(2, '0')}',
                                          style: TextStyle(color: Colors.grey.shade500, fontSize: 11),
                                        ),
                                      ],
                                    ),
                                    if (log.comment != null && log.comment!.isNotEmpty)
                                      Text(log.comment!, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  const SizedBox(height: 24),

                  // Comments Section
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Discussion (${report.comments.length})',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (report.comments.isEmpty)
                    const Text('No comments yet. Join the conversation.', style: TextStyle(color: AppColors.textSecondary, fontSize: 13))
                  else
                    ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: report.comments.length,
                      separatorBuilder: (_, __) => const Divider(height: 16),
                      itemBuilder: (context, index) {
                        final comment = report.comments[index];
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  comment.user?.fullName ?? 'User #${comment.userId}',
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                                Text(
                                  '${comment.createdAt.hour}:${comment.createdAt.minute.toString().padLeft(2, '0')}',
                                  style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(comment.content, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
                          ],
                        );
                      },
                    ),
                  const SizedBox(height: 20),

                  // Add Comment Box
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _commentController,
                          decoration: InputDecoration(
                            hintText: 'Add a comment...',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            filled: true,
                            fillColor: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        onPressed: _isPostingComment ? null : _addComment,
                        icon: _isPostingComment
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.send, color: AppColors.primary),
                      ),
                    ],
                  ),
                  const SizedBox(height: 30),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
