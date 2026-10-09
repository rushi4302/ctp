import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/location_service.dart';
import '../../../core/services/report_service.dart';
import '../../feed/providers/report_provider.dart';
import 'civic_camera_screen.dart';

class CreateReportScreen extends ConsumerStatefulWidget {
  final bool autoLaunchCamera;
  const CreateReportScreen({super.key, this.autoLaunchCamera = false});

  @override
  ConsumerState<CreateReportScreen> createState() => _CreateReportScreenState();
}

class _CreateReportScreenState extends ConsumerState<CreateReportScreen> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  final _reportService = ReportService();

  XFile? _capturedFile;
  Uint8List? _capturedImageBytes;
  DateTime? _captureTimestamp;
  CivicLocationData? _civicLocation;

  double? _latitude;
  double? _longitude;
  String? _locationError;

  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    if (widget.autoLaunchCamera) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _openCamera();
      });
    }
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    super.dispose();
  }

  /// Opens the In-App Camera screen with live preview, instant capture timestamp,
  /// GPS acquisition, reverse geocoding, and Citizen Confirmation.
  Future<void> _openCamera() async {
    try {
      final result = await Navigator.of(context).push<CivicCaptureResult>(
        MaterialPageRoute(
          builder: (context) => const CivicCameraScreen(),
        ),
      );

      if (result != null && mounted) {
        setState(() {
          _capturedFile = result.file;
          _capturedImageBytes = result.bytes;
          _captureTimestamp = result.captureTimestamp;
          _civicLocation = result.location;
          _latitude = result.location.latitude;
          _longitude = result.location.longitude;
          _locationError = null;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not launch camera: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Submits the civic report with photo, captured timestamp, and structured location metadata.
  Future<void> _submitReport() async {
    // 1. Photo validation
    if (_capturedImageBytes == null || _captureTimestamp == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please capture a photo of the civic issue before submitting.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    // 2. Location validation
    if (_latitude == null || _longitude == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_locationError ?? 'Location required. Please wait for GPS or retake photo.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    // 3. Description validation
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    try {
      final description = _descriptionController.text.trim();
      final autoTitle = description.length > 60
          ? '${description.substring(0, 57)}...'
          : description;

      final report = await _reportService.createReport(
        title: autoTitle,
        description: description,
        latitude: _latitude!,
        longitude: _longitude!,
        locationAccuracy: _civicLocation?.accuracy,
        captureTimestamp: _captureTimestamp,
        address: _civicLocation?.displayAddress,
        locality: _civicLocation?.locality ?? _civicLocation?.subLocality,
        city: _civicLocation?.city,
        district: _civicLocation?.district,
        state: _civicLocation?.state,
        postalCode: _civicLocation?.postalCode,
        imageBytes: _capturedImageBytes,
        imageName: _capturedFile?.name ?? 'captured_issue.jpg',
      );

      // Refresh global feed
      ref.read(reportListProvider.notifier).fetchReports();

      if (mounted) {
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Civic report submitted successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        context.pushReplacement('/reports/${report.id}');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Submission failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Report Civic Issue'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 1. Camera Section (Prompt or Photo Preview)
              _buildCameraSection(),
              const SizedBox(height: 16),

              // 2. Structured Verification Details Card (When photo is captured)
              if (_captureTimestamp != null && _civicLocation != null) ...[
                _buildVerificationCard(),
                const SizedBox(height: 20),
              ],

              // 3. Description Field
              _buildDescriptionField(),
              const SizedBox(height: 28),

              // 4. Submit Button
              _buildSubmitButton(),
            ],
          ),
        ),
      ),
    );
  }

  /// Builds either the photo preview or the prominent In-App Camera launch card.
  Widget _buildCameraSection() {
    if (_capturedImageBytes != null) {
      return Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Stack(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Image.memory(
                _capturedImageBytes!,
                width: double.infinity,
                height: 240,
                fit: BoxFit.cover,
              ),
            ),
            Positioned(
              top: 10,
              right: 10,
              child: ElevatedButton.icon(
                onPressed: _openCamera,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.black.withOpacity(0.75),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
                icon: const Icon(Icons.camera_alt, size: 16),
                label: const Text('Retake Photo', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      );
    }

    return InkWell(
      onTap: _openCamera,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        height: 200,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border, width: 1.5),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.camera_alt_outlined,
                  size: 44,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Capture Photo of Issue',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Camera only (Gallery disabled for verification)',
                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Displays structured metadata captured at the exact moment of photo creation.
  Widget _buildVerificationCard() {
    final formattedTime = DateFormat('d MMM yyyy, hh:mm a').format(_captureTimestamp!);
    final landmark = _civicLocation?.landmark;
    final area = _civicLocation?.displayArea;
    final city = _civicLocation?.displayCity;
    final coords = _civicLocation?.coordinatesFormatted;
    final accuracy = _civicLocation?.accuracyFormatted;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.teal.shade200),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified, color: Colors.teal, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Geotag & Timestamp Verified',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: AppColors.textPrimary,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.teal.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.teal.shade200),
                ),
                child: Text(
                  '±$accuracy',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: Colors.teal.shade800,
                  ),
                ),
              ),
            ],
          ),
          const Divider(height: 18),

          // Captured Time
          _buildInfoRow(
            icon: Icons.access_time_filled,
            iconColor: Colors.deepPurple,
            label: '🕒 Captured',
            value: formattedTime,
          ),
          const SizedBox(height: 8),

          // Landmark / Building (if available)
          if (landmark != null && landmark.isNotEmpty) ...[
            _buildInfoRow(
              icon: Icons.apartment,
              iconColor: AppColors.primary,
              label: '📍 Location',
              value: landmark,
            ),
            const SizedBox(height: 8),
          ],

          // Area
          _buildInfoRow(
            icon: Icons.holiday_village_outlined,
            iconColor: Colors.orange.shade800,
            label: '🏘️ Area',
            value: area ?? 'Unknown Area',
          ),
          const SizedBox(height: 8),

          // City
          _buildInfoRow(
            icon: Icons.location_city,
            iconColor: Colors.teal,
            label: '🏙️ City',
            value: city ?? 'Unknown City',
          ),
          const SizedBox(height: 8),

          // Coordinates
          _buildInfoRow(
            icon: Icons.my_location,
            iconColor: Colors.blueGrey,
            label: '🌐 Coordinates',
            value: coords ?? 'Unknown',
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow({
    required IconData icon,
    required Color iconColor,
    required String label,
    required String value,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 105,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade600,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDescriptionField() {
    return TextFormField(
      controller: _descriptionController,
      minLines: 4,
      maxLines: 7,
      decoration: InputDecoration(
        labelText: 'Description *',
        hintText: 'Describe the civic issue in detail...',
        alignLabelWithHint: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        filled: true,
        fillColor: Colors.white,
      ),
      validator: (val) {
        if (val == null || val.trim().length < 5) {
          return 'Please provide a description (min 5 characters)';
        }
        return null;
      },
    );
  }

  Widget _buildSubmitButton() {
    return ElevatedButton(
      onPressed: _isSubmitting ? null : _submitReport,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        elevation: 1,
      ),
      child: _isSubmitting
          ? const SizedBox(
              height: 22,
              width: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
            )
          : const Text(
              'Submit Civic Report',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
    );
  }
}
