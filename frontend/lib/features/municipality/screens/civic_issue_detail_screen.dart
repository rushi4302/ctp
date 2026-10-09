import 'dart:io';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/services/civic_issue_service.dart';
import '../../../core/services/location_service.dart';
import 'package:geolocator/geolocator.dart';
import '../../../shared/models/civic_issue_model.dart';
import '../../auth/providers/auth_provider.dart';
import '../../maps/screens/single_location_map_screen.dart';

class CivicIssueDetailScreen extends ConsumerStatefulWidget {
  final int issueId;
  const CivicIssueDetailScreen({super.key, required this.issueId});

  @override
  ConsumerState<CivicIssueDetailScreen> createState() => _CivicIssueDetailScreenState();
}

class _CivicIssueDetailScreenState extends ConsumerState<CivicIssueDetailScreen> {
  final _civicIssueService = CivicIssueService();
  CivicIssueModel? _issue;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchDetail();
  }

  Future<void> _fetchDetail() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final data = await _civicIssueService.getCivicIssueById(widget.issueId);
      setState(() {
        _issue = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = e.toString();
      });
    }
  }

  void _showResolveDialog() {
    final notesCtrl = TextEditingController();
    File? evidenceImage;
    CivicLocationData? resolutionLocation;
    DateTime? resolutionTimestamp;
    bool isResolving = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          Future<void> pickImage() async {
            final picker = ImagePicker();
            final picked = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
            if (picked != null) {
              setDialogState(() => evidenceImage = File(picked.path));
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
            title: const Text('Resolve Issue'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: notesCtrl,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Resolution Notes',
                      hintText: 'Describe the work done to resolve this issue...',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (evidenceImage != null)
                    Stack(
                      alignment: Alignment.topRight,
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.file(evidenceImage!, height: 150, width: double.infinity, fit: BoxFit.cover),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, color: Colors.white),
                          onPressed: () => setDialogState(() => evidenceImage = null),
                        ),
                      ],
                    )
                  else
                    OutlinedButton.icon(
                      onPressed: pickImage,
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Capture Proof of Work'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                    ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isResolving ? null : () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white),
                onPressed: isResolving
                    ? null
                    : () async {
                        final notes = notesCtrl.text.trim();
                        if (notes.isEmpty || notes.length < 5) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Please provide detailed resolution notes (min 5 chars).')),
                          );
                          return;
                        }
                        setDialogState(() => isResolving = true);
                        try {
                          await _civicIssueService.resolveCivicIssue(
                            _issue!.id,
                            notes,
                            imagePath: evidenceImage?.path,
                            latitude: resolutionLocation?.latitude,
                            longitude: resolutionLocation?.longitude,
                            timestamp: resolutionTimestamp,
                          );
                          if (mounted) {
                            Navigator.pop(ctx);
                            _fetchDetail();
                          }
                        } catch (e) {
                          setDialogState(() => isResolving = false);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
                            );
                          }
                        }
                      },
                child: isResolving
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Resolve'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState.user;
    final isAuthority = user != null && (user.isMunicipality || user.role == 'FIELD_WORKER');

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Civic Issue')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _issue == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Civic Issue')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error ?? 'Issue not found.'),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: _fetchDetail, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    final issue = _issue!;
    final statusColor = AppColors.getStatusColor(issue.status);

    // Get the first report photo for the "Before" picture
    String? beforePhotoUrl;
    if (issue.reports.isNotEmpty && issue.reports.first.media.isNotEmpty) {
      beforePhotoUrl = issue.reports.first.media.first.fullUrl;
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text('Issue #${issue.id}', maxLines: 1),
        backgroundColor: AppColors.primaryDark,
        foregroundColor: Colors.white,
        actions: [
          if (isAuthority && issue.status != 'RESOLVED' && issue.status != 'CLOSED')
            IconButton(
              icon: const Icon(Icons.check_circle_outline),
              tooltip: 'Resolve Issue',
              onPressed: _showResolveDialog,
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Info
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    issue.title,
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: statusColor.withOpacity(0.5)),
                  ),
                  child: Text(
                    issue.status,
                    style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              issue.description,
              style: const TextStyle(fontSize: 15, height: 1.4, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 24),

            // Before / After Comparison
            if (beforePhotoUrl != null || issue.fullResolutionEvidenceUrl != null) ...[
              const Text(
                'Resolution Progress',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Before
                  Expanded(
                    child: Column(
                      children: [
                        const Text('Before (Reported)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.orange)),
                        const SizedBox(height: 8),
                        if (beforePhotoUrl != null)
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: CachedNetworkImage(
                              imageUrl: beforePhotoUrl,
                              height: 160,
                              fit: BoxFit.cover,
                              placeholder: (_, __) => Container(height: 160, color: Colors.grey.shade200),
                              errorWidget: (_, __, ___) => Container(height: 160, color: Colors.grey.shade100, child: const Icon(Icons.broken_image)),
                            ),
                          )
                        else
                          Container(
                            height: 160,
                            decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(8)),
                            child: const Center(child: Text('No original photo')),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  // After
                  Expanded(
                    child: Column(
                      children: [
                        const Text('After (Resolved)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green)),
                        const SizedBox(height: 8),
                        if (issue.fullResolutionEvidenceUrl != null)
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: CachedNetworkImage(
                              imageUrl: issue.fullResolutionEvidenceUrl!,
                              height: 160,
                              fit: BoxFit.cover,
                              placeholder: (_, __) => Container(height: 160, color: Colors.grey.shade200),
                              errorWidget: (_, __, ___) => Container(height: 160, color: Colors.grey.shade100, child: const Icon(Icons.broken_image)),
                            ),
                          )
                        else
                          Container(
                            height: 160,
                            decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(8)),
                            child: const Center(child: Text('Pending resolution')),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
            ],

            // Resolution Notes
            if (issue.resolutionNotes != null && issue.resolutionNotes!.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.verified, color: Colors.green, size: 20),
                        const SizedBox(width: 8),
                        const Text('Resolution Notes', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      issue.resolutionNotes!,
                      style: TextStyle(color: Colors.green.shade900),
                    ),
                    if (issue.resolvedAt != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        'Resolved on ${DateFormat('MMM d, yyyy - hh:mm a').format(issue.resolvedAt!)}',
                        style: TextStyle(fontSize: 12, color: Colors.green.shade700),
                      ),
                    ]
                  ],
                ),
              ),
              if (issue.resolutionLatitude != null && issue.resolutionLongitude != null) ...[
                const SizedBox(height: 8),
                Card(
                  color: issue.resolutionLocationStatus == 'MISMATCH' ? Colors.orange.shade50 : Colors.blue.shade50,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: BorderSide(
                      color: issue.resolutionLocationStatus == 'MISMATCH' ? Colors.orange.shade200 : Colors.blue.shade200,
                    ),
                  ),
                  child: ListTile(
                    leading: Icon(
                      issue.resolutionLocationStatus == 'MISMATCH' ? Icons.warning_amber : Icons.my_location,
                      color: issue.resolutionLocationStatus == 'MISMATCH' ? Colors.orange : Colors.blue,
                    ),
                    title: Text(
                      issue.resolutionLocationStatus == 'MISMATCH' ? 'Location Mismatch Flagged' : 'Verified Resolution Location',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: issue.resolutionLocationStatus == 'MISMATCH' ? Colors.orange.shade900 : Colors.blue.shade900,
                        fontSize: 13,
                      ),
                    ),
                    subtitle: Text(
                      '${issue.resolutionLatitude!.toStringAsFixed(4)}, ${issue.resolutionLongitude!.toStringAsFixed(4)}',
                      style: const TextStyle(fontSize: 12),
                    ),
                    trailing: OutlinedButton(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => SingleLocationMapScreen(
                              latitude: issue.resolutionLatitude!,
                              longitude: issue.resolutionLongitude!,
                              title: 'Resolution Proof',
                              snippet: 'Proof of work submitted here',
                              status: 'RESOLVED',
                            ),
                          ),
                        );
                      },
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
                        foregroundColor: Colors.blue,
                        side: const BorderSide(color: Colors.blue),
                      ),
                      child: const Text('Map', style: TextStyle(fontSize: 11)),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 24),
            ],

            // Details section
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              elevation: 0.5,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Issue Details', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const Divider(height: 24),
                    _buildDetailRow(Icons.category, 'Category', issue.category),
                    const SizedBox(height: 12),
                    _buildDetailRow(Icons.warning, 'Severity', issue.severity),
                    const SizedBox(height: 12),
                    _buildDetailRow(Icons.map, 'Ward', issue.ward ?? 'Unknown'),
                    const SizedBox(height: 12),
                    _buildDetailRow(Icons.people, 'Citizen Reports', '${issue.reportCount} linked report(s)'),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => SingleLocationMapScreen(
                                latitude: issue.latitude,
                                longitude: issue.longitude,
                                title: issue.title,
                                snippet: issue.address ?? '${issue.latitude.toStringAsFixed(4)}, ${issue.longitude.toStringAsFixed(4)}',
                                status: issue.status,
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
            if (issue.statusLogs.isEmpty)
              const Text('No status transitions recorded yet.', style: TextStyle(color: AppColors.textSecondary, fontSize: 13))
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: issue.statusLogs.length,
                itemBuilder: (context, index) {
                  final log = issue.statusLogs[index];
                  final logColor = AppColors.getStatusColor(log.newStatus);

                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Column(
                        children: [
                          CircleAvatar(radius: 6, backgroundColor: logColor),
                          if (index < issue.statusLogs.length - 1)
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
                                    log.newStatus,
                                    style: TextStyle(fontWeight: FontWeight.bold, color: logColor, fontSize: 13),
                                  ),
                                  Text(
                                    '${DateFormat('MMM d, hh:mm a').format(log.createdAt)}',
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
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColors.textSecondary),
        const SizedBox(width: 8),
        Text('$label:', style: const TextStyle(color: AppColors.textSecondary)),
        const SizedBox(width: 8),
        Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.bold))),
      ],
    );
  }
}
