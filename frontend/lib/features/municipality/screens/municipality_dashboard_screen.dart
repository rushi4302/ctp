import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/civic_issue_service.dart';
import '../../../core/services/location_service.dart';
import '../../auth/providers/auth_provider.dart';
import '../../../shared/models/civic_issue_model.dart';
import '../../../shared/utils/complaint_presentation.dart';
import 'civic_issue_detail_screen.dart';

class MunicipalityDashboardScreen extends ConsumerStatefulWidget {
  const MunicipalityDashboardScreen({super.key});

  @override
  ConsumerState<MunicipalityDashboardScreen> createState() => _MunicipalityDashboardScreenState();
}

class _MunicipalityDashboardScreenState extends ConsumerState<MunicipalityDashboardScreen> {
  final _civicIssueService = CivicIssueService();

  bool _isLoading = true;
  List<CivicIssueModel> _issues = [];
  String? _statusFilter;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() => _isLoading = true);
    try {
      final issues = await _civicIssueService.getCivicIssues(statusFilter: _statusFilter);
      
      setState(() {
        _issues = issues;
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _assignDepartment(CivicIssueModel issue) async {
    final departmentController = TextEditingController(
      text: issue.assignedDepartmentId == null
          ? ''
          : presentDepartment(issue.assignedDepartmentId!, isSynthetic: issue.isSynthetic),
    );
    final notesController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Assign issue #${issue.id}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: departmentController, decoration: const InputDecoration(labelText: 'Department')),
            TextField(controller: notesController, decoration: const InputDecoration(labelText: 'Assignment note (optional)')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Save assignment')),
        ],
      ),
    );
    if (confirmed != true || departmentController.text.trim().isEmpty) {
      departmentController.dispose();
      notesController.dispose();
      return;
    }
    try {
      await _civicIssueService.assignDepartment(
        issue.id,
        department: departmentController.text,
        notes: notesController.text,
      );
      await _loadDashboard();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Department assignment saved.')));
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Assignment failed: $error')));
    } finally {
      departmentController.dispose();
      notesController.dispose();
    }
  }

  void _showStatusDialog(CivicIssueModel issue) {
    String selectedStatus = issue.status;
    final commentCtrl = TextEditingController();
    XFile? evidenceImage;
    Uint8List? evidenceImageBytes;
    CivicLocationData? resolutionLocation;
    DateTime? resolutionTimestamp;
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          Future<void> pickImage() async {
            final picker = ImagePicker();
            final picked = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
            if (picked != null) {
              final bytes = await picked.readAsBytes();
              setDialogState(() {
                evidenceImage = picked;
                evidenceImageBytes = bytes;
              });
              // Immediately fetch GPS
              try {
                final locData = await LocationService().getCurrentLocation(doReverseGeocode: false);
                setDialogState(() {
                  resolutionLocation = locData;
                  resolutionTimestamp = locData.timestamp;
                });
              } catch (_) {
                // If location fails, we just don't have it.
              }
            }
          }

          return AlertDialog(
            title: Text('Change Status: #${issue.id}'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    value: selectedStatus,
                    decoration: const InputDecoration(labelText: 'Status'),
                    items: const [
                      DropdownMenuItem(value: 'PENDING', child: Text('Pending')),
                      DropdownMenuItem(value: 'ASSIGNED', child: Text('Assigned')),
                      DropdownMenuItem(value: 'IN_PROGRESS', child: Text('In Progress')),
                      DropdownMenuItem(value: 'RESOLVED', child: Text('Resolved')),
                      DropdownMenuItem(value: 'CLOSED', child: Text('Closed')),
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
                      labelText: 'Official Remark / Notes',
                      hintText: 'Action taken or reason...',
                    ),
                  ),
                  if (selectedStatus == 'RESOLVED') ...[
                    const SizedBox(height: 16),
                    const Text('Resolution Proof', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    if (evidenceImage != null)
                      Stack(
                        alignment: Alignment.topRight,
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.memory(evidenceImageBytes!, height: 120, width: double.infinity, fit: BoxFit.cover),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close, color: Colors.white),
                            onPressed: () => setDialogState(() {
                              evidenceImage = null;
                              evidenceImageBytes = null;
                            }),
                          ),
                        ],
                      )
                    else
                      OutlinedButton.icon(
                        onPressed: pickImage,
                        icon: const Icon(Icons.camera_alt),
                        label: const Text('Capture Proof of Work'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                  ]
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white),
                onPressed: isSubmitting
                    ? null
                    : () async {
                        final comment = commentCtrl.text.trim();
                        if (selectedStatus == 'RESOLVED' && comment.length < 5) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Please provide detailed resolution notes (min 5 chars).')),
                          );
                          return;
                        }

                        setDialogState(() => isSubmitting = true);
                        try {
                          if (selectedStatus == 'RESOLVED') {
                            await _civicIssueService.resolveCivicIssue(
                              issue.id,
                              comment,
                              imageBytes: evidenceImageBytes,
                              imageName: evidenceImage?.name,
                              latitude: resolutionLocation?.latitude,
                              longitude: resolutionLocation?.longitude,
                              timestamp: resolutionTimestamp,
                            );
                          } else {
                            await _civicIssueService.updateStatus(
                              issue.id,
                              status: selectedStatus,
                              comment: comment.isNotEmpty ? comment : null,
                            );
                          }
                          if (mounted) {
                            Navigator.pop(ctx);
                            await _loadDashboard();
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(selectedStatus == 'RESOLVED' ? 'Issue resolved and saved.' : 'Issue status updated.')),
                              );
                            }
                          }
                        } catch (e) {
                          setDialogState(() => isSubmitting = false);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
                            );
                          }
                        }
                      },
                child: isSubmitting
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Update'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(

      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Municipal Governance Portal'),
        backgroundColor: AppColors.primaryDark,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDashboard,
          ),
          IconButton(
            icon: const Icon(Icons.home_outlined),
            tooltip: 'Citizen View',
            onPressed: () => context.push('/home'),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadDashboard,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Stats Grid Removed for Civic Issues
                    // Filter Chips
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          _buildFilterChip('All', null),
                          _buildFilterChip('Pending', 'PENDING'),
                          _buildFilterChip('Assigned', 'ASSIGNED'),
                          _buildFilterChip('In Progress', 'IN_PROGRESS'),
                          _buildFilterChip('Resolved', 'RESOLVED'),
                          _buildFilterChip('Closed', 'CLOSED'),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Reports List
                    const Text(
                      'Jurisdiction Issues',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                    ),
                    const SizedBox(height: 12),

                    if (_issues.isEmpty)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 40),
                        child: Center(child: Text('No issues match the current filter.')),
                      )
                    else
                      ListView.separated(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: _issues.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final i = _issues[index];
                          final statusColor = AppColors.getStatusColor(i.status);

                          return Card(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            child: Padding(
                              padding: const EdgeInsets.all(14.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        '#${i.id} • ${i.category}',
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.primary),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: statusColor.withOpacity(0.15),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          humanizeStatus(i.status),
                                          style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 11),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    presentComplaintTitle(i.title, isSynthetic: i.isSynthetic),
                                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    presentComplaintDescription(i.description, isSynthetic: i.isSynthetic),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
                                  ),
                                  if (i.assignedDepartmentId != null && i.assignedDepartmentId!.isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 5),
                                      child: Text(
                                        'Department: ${presentDepartment(i.assignedDepartmentId!, isSynthetic: i.isSynthetic)}${i.isSynthetic ? ' · Demonstration assignment' : ''}',
                                        style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                                      ),
                                    ),
                                  if (i.isSynthetic)
                                    const Padding(
                                      padding: EdgeInsets.only(top: 5),
                                      child: Text(
                                        'Demonstration record · not an official municipal complaint',
                                        style: TextStyle(fontSize: 11, color: Colors.deepOrange),
                                      ),
                                    ),
                                  const SizedBox(height: 8),

                                  // AI & Location chips
                                  Wrap(
                                    spacing: 6,
                                    runSpacing: 4,
                                    children: [
                                      if (i.aiCategory != null)
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: Colors.blue.shade50,
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            'AI: ${i.aiCategory} (${((i.aiConfidence ?? 0) * 100).toStringAsFixed(0)}%)',
                                            style: TextStyle(fontSize: 10, color: Colors.blue.shade800, fontWeight: FontWeight.bold),
                                          ),
                                        ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: Colors.purple.shade50,
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(
                                          'Reports: ${i.reportCount}',
                                          style: TextStyle(
                                            fontSize: 10,
                                            color: Colors.purple.shade900,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 10),

                                  // Action Buttons
                                  Wrap(
                                    alignment: WrapAlignment.end,
                                    spacing: 8,
                                    runSpacing: 4,
                                    children: [
                                      OutlinedButton.icon(
                                        onPressed: () => _assignDepartment(i),
                                        icon: const Icon(Icons.account_tree_outlined, size: 18),
                                        label: const Text('Assign Department'),
                                      ),
                                      OutlinedButton(
                                        onPressed: () {
                                          Navigator.push(
                                            context,
                                            MaterialPageRoute(
                                              builder: (context) => CivicIssueDetailScreen(issueId: i.id),
                                            ),
                                          ).then((_) => _loadDashboard());
                                        },
                                        child: const Text('View Detail'),
                                      ),
                                      ElevatedButton(
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: AppColors.primary,
                                          foregroundColor: Colors.white,
                                        ),
                                        onPressed: () => _showStatusDialog(i),
                                        child: const Text('Update Status'),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildFilterChip(String label, String? statusVal) {
    final isSelected = _statusFilter == statusVal;
    return Padding(
      padding: const EdgeInsets.only(right: 6.0),
      child: FilterChip(
        label: Text(label, style: TextStyle(fontSize: 11, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
        selected: isSelected,
        onSelected: (_) {
          setState(() => _statusFilter = statusVal);
          _loadDashboard();
        },
      ),
    );
  }
}
