import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/location_service.dart';

/// Container for confirmed camera capture output with photo and verified metadata.
class CivicCaptureResult {
  final XFile file;
  final Uint8List bytes;
  final DateTime captureTimestamp;
  final CivicLocationData location;

  const CivicCaptureResult({
    required this.file,
    required this.bytes,
    required this.captureTimestamp,
    required this.location,
  });
}

class CivicCameraScreen extends StatefulWidget {
  const CivicCameraScreen({super.key});

  @override
  State<CivicCameraScreen> createState() => _CivicCameraScreenState();
}

class _CivicCameraScreenState extends State<CivicCameraScreen>
    with WidgetsBindingObserver {
  final LocationService _locationService = LocationService();

  List<CameraDescription> _cameras = [];
  CameraController? _controller;
  int _selectedCameraIndex = 0;
  bool _isCameraInitialized = false;
  String? _cameraErrorMessage;

  // Flash modes: auto, off, always
  FlashMode _currentFlashMode = FlashMode.auto;

  // Capture & confirmation states
  bool _isCapturing = false;
  XFile? _capturedFile;
  Uint8List? _capturedBytes;
  DateTime? _captureTimestamp;

  CivicLocationData? _capturedLocation;
  bool _isLocating = false;
  String? _locationErrorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final cameraController = _controller;
    if (cameraController == null || !cameraController.value.isInitialized) {
      return;
    }

    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      cameraController.dispose();
      if (mounted) {
        setState(() {
          _isCameraInitialized = false;
        });
      }
    } else if (state == AppLifecycleState.resumed) {
      _initializeCamera();
    }
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isEmpty) {
        if (mounted) {
          setState(() {
            _cameraErrorMessage = 'No camera found on this device.';
            _isCameraInitialized = false;
          });
        }
        return;
      }

      // Default to back camera if available
      int backCameraIndex = _cameras.indexWhere(
        (cam) => cam.lensDirection == CameraLensDirection.back,
      );
      _selectedCameraIndex = backCameraIndex != -1 ? backCameraIndex : 0;

      await _setupController(_cameras[_selectedCameraIndex]);
    } catch (e) {
      if (mounted) {
        setState(() {
          _cameraErrorMessage = 'Camera initialization failed: $e';
          _isCameraInitialized = false;
        });
      }
    }
  }

  Future<void> _setupController(CameraDescription cameraDescription) async {
    final oldController = _controller;
    if (oldController != null) {
      await oldController.dispose();
    }

    final newController = CameraController(
      cameraDescription,
      ResolutionPreset.high,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );

    _controller = newController;

    try {
      await newController.initialize();
      try {
        await newController.setFlashMode(_currentFlashMode);
      } catch (_) {}

      if (mounted) {
        setState(() {
          _isCameraInitialized = true;
          _cameraErrorMessage = null;
        });
      }
    } on CameraException catch (e) {
      if (mounted) {
        setState(() {
          _isCameraInitialized = false;
          if (e.code == 'CameraAccessDenied' || e.code == 'CameraAccessDeniedWithoutPrompt') {
            _cameraErrorMessage = 'Camera permission denied. Please grant permission in settings.';
          } else {
            _cameraErrorMessage = 'Camera error: ${e.description ?? e.code}';
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCameraInitialized = false;
          _cameraErrorMessage = 'Unable to start camera: $e';
        });
      }
    }
  }

  Future<void> _toggleFlash() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    FlashMode nextMode;
    switch (_currentFlashMode) {
      case FlashMode.auto:
        nextMode = FlashMode.always;
        break;
      case FlashMode.always:
        nextMode = FlashMode.off;
        break;
      case FlashMode.off:
      default:
        nextMode = FlashMode.auto;
        break;
    }

    try {
      await _controller!.setFlashMode(nextMode);
      if (mounted) {
        setState(() => _currentFlashMode = nextMode);
      }
    } catch (_) {}
  }

  Future<void> _switchCamera() async {
    if (_cameras.length < 2) return;
    final nextIndex = (_selectedCameraIndex + 1) % _cameras.length;
    _selectedCameraIndex = nextIndex;
    setState(() => _isCameraInitialized = false);
    await _setupController(_cameras[nextIndex]);
  }

  /// Shutter tapped: immediately lock exact device timestamp, take picture, acquire GPS.
  Future<void> _capturePhoto() async {
    if (_controller == null || !_controller!.value.isInitialized || _isCapturing) {
      return;
    }

    setState(() => _isCapturing = true);

    // 1. Immediately record device capture timestamp as source of truth
    final captureTimestamp = DateTime.now();

    try {
      final xFile = await _controller!.takePicture();
      final bytes = await xFile.readAsBytes();

      if (mounted) {
        setState(() {
          _capturedFile = xFile;
          _capturedBytes = bytes;
          _captureTimestamp = captureTimestamp;
          _isCapturing = false;
          _isLocating = true;
          _locationErrorMessage = null;
        });
      }

      // 2. Concurrently obtain device GPS location & reverse geocode
      _fetchLocationForCapture(captureTimestamp);
    } catch (e) {
      if (mounted) {
        setState(() => _isCapturing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Photo capture failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _fetchLocationForCapture(DateTime timestamp) async {
    setState(() {
      _isLocating = true;
      _locationErrorMessage = null;
    });

    try {
      final locationData = await _locationService.getCurrentLocation(doReverseGeocode: true);
      if (mounted) {
        setState(() {
          // Preserve the capture timestamp as the anchor
          _capturedLocation = locationData.copyWith(timestamp: timestamp);
          _isLocating = false;
          _locationErrorMessage = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLocating = false;
          _locationErrorMessage = e.toString().replaceAll('Exception: ', '');
        });
      }
    }
  }

  void _retakePhoto() {
    setState(() {
      _capturedFile = null;
      _capturedBytes = null;
      _captureTimestamp = null;
      _capturedLocation = null;
      _isLocating = false;
      _locationErrorMessage = null;
    });
  }

  void _confirmAndUsePhoto() {
    if (_capturedFile == null || _capturedBytes == null || _captureTimestamp == null) {
      return;
    }

    if (_capturedLocation == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please wait for GPS location or retry before confirming.'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    final result = CivicCaptureResult(
      file: _capturedFile!,
      bytes: _capturedBytes!,
      captureTimestamp: _captureTimestamp!,
      location: _capturedLocation!,
    );

    Navigator.of(context).pop(result);
  }

  @override
  Widget build(BuildContext context) {
    // If a photo was captured, show the Confirmation Screen
    if (_capturedBytes != null && _captureTimestamp != null) {
      return _buildConfirmationScreen();
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: _cameraErrorMessage != null
            ? _buildCameraErrorView()
            : (!_isCameraInitialized || _controller == null)
                ? const Center(
                    child: CircularProgressIndicator(color: AppColors.primary),
                  )
                : _buildCameraPreviewView(),
      ),
    );
  }

  Widget _buildCameraErrorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.camera_alt_outlined, size: 64, color: Colors.white70),
            const SizedBox(height: 16),
            const Text(
              'Camera Access Needed',
              style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              _cameraErrorMessage ?? 'Unable to access camera.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Colors.white54),
                  ),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 16),
                ElevatedButton(
                  onPressed: _initializeCamera,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                  ),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraPreviewView() {
    return Stack(
      fit: StackFit.expand,
      children: [
        // Camera live preview
        Center(
          child: CameraPreview(_controller!),
        ),

        // Top bar: Close, Flash, Switch Camera
        Positioned(
          top: 12,
          left: 12,
          right: 12,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              IconButton(
                icon: const Icon(Icons.close, color: Colors.white, size: 28),
                onPressed: () => Navigator.of(context).pop(),
              ),
              Row(
                children: [
                  IconButton(
                    icon: Icon(
                      _currentFlashMode == FlashMode.always
                          ? Icons.flash_on
                          : _currentFlashMode == FlashMode.auto
                              ? Icons.flash_auto
                              : Icons.flash_off,
                      color: _currentFlashMode == FlashMode.off
                          ? Colors.white54
                          : Colors.amberAccent,
                      size: 26,
                    ),
                    onPressed: _toggleFlash,
                  ),
                  if (_cameras.length > 1)
                    IconButton(
                      icon: const Icon(Icons.flip_camera_ios, color: Colors.white, size: 26),
                      onPressed: _switchCamera,
                    ),
                ],
              ),
            ],
          ),
        ),

        // Hint text above shutter
        Positioned(
          bottom: 110,
          left: 0,
          right: 0,
          child: Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.gps_fixed, size: 14, color: Colors.white70),
                  SizedBox(width: 6),
                  Text(
                    'GPS and timestamp captured automatically',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
        ),

        // Bottom Bar: Shutter button
        Positioned(
          bottom: 24,
          left: 0,
          right: 0,
          child: Center(
            child: GestureDetector(
              onTap: _isCapturing ? null : _capturePhoto,
              child: Container(
                width: 76,
                height: 76,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 4),
                  color: _isCapturing ? Colors.white54 : Colors.transparent,
                ),
                child: Center(
                  child: Container(
                    width: 60,
                    height: 60,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _isCapturing ? AppColors.primary : Colors.white,
                    ),
                    child: _isCapturing
                        ? const CircularProgressIndicator(color: Colors.white, strokeWidth: 3)
                        : null,
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// Citizen Confirmation Screen displaying photo preview, timestamp, location, area, city, and accuracy.
  Widget _buildConfirmationScreen() {
    final formattedDate = _captureTimestamp != null
        ? DateFormat('d MMM yyyy, hh:mm a').format(_captureTimestamp!)
        : 'Unknown Time';

    final hasLocation = _capturedLocation != null;
    final landmark = _capturedLocation?.landmark;
    final area = _capturedLocation?.displayArea;
    final city = _capturedLocation?.displayCity;
    final coords = _capturedLocation?.coordinatesFormatted;
    final accuracy = _capturedLocation?.accuracyFormatted;

    return Scaffold(
      backgroundColor: Colors.grey.shade900,
      appBar: AppBar(
        title: const Text('Confirm Photo & Location'),
        backgroundColor: Colors.black87,
        foregroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _retakePhoto,
        ),
      ),
      body: Column(
        children: [
          // 1. Photo Preview
          Expanded(
            flex: 5,
            child: Container(
              width: double.infinity,
              color: Colors.black,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image.memory(
                    _capturedBytes!,
                    fit: BoxFit.contain,
                  ),
                  Positioned(
                    top: 10,
                    right: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.7),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.verified, color: Colors.greenAccent, size: 14),
                          SizedBox(width: 4),
                          Text(
                            'ORIGINAL PHOTO',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 2. Structured Metadata Card
          Expanded(
            flex: 6,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16.0),
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Section Header
                    Row(
                      children: [
                        const Icon(Icons.info_outline, color: AppColors.primary, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          'Captured Verification Details',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.grey.shade900,
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 18),

                    // Timestamp
                    _buildMetaRow(
                      icon: Icons.access_time_filled,
                      iconColor: Colors.deepPurple,
                      label: 'Captured',
                      value: formattedDate,
                    ),
                    const SizedBox(height: 10),

                    // Location / Landmark
                    if (_isLocating) ...[
                      _buildMetaRow(
                        icon: Icons.location_on,
                        iconColor: AppColors.primary,
                        label: 'Location',
                        value: 'Detecting location...',
                        isLoading: true,
                      ),
                    ] else if (_locationErrorMessage != null) ...[
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade200),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.error_outline, color: Colors.red, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _locationErrorMessage!,
                                style: TextStyle(color: Colors.red.shade900, fontSize: 12),
                              ),
                            ),
                            TextButton(
                              onPressed: () => _fetchLocationForCapture(_captureTimestamp!),
                              child: const Text('Retry', style: TextStyle(fontWeight: FontWeight.bold)),
                            ),
                          ],
                        ),
                      ),
                    ] else ...[
                      if (landmark != null && landmark.isNotEmpty) ...[
                        _buildMetaRow(
                          icon: Icons.apartment,
                          iconColor: AppColors.primary,
                          label: 'Location',
                          value: landmark,
                        ),
                        const SizedBox(height: 10),
                      ],
                      _buildMetaRow(
                        icon: Icons.holiday_village_outlined,
                        iconColor: Colors.orange.shade800,
                        label: 'Area',
                        value: area ?? 'Unknown Area',
                      ),
                      const SizedBox(height: 10),
                      _buildMetaRow(
                        icon: Icons.location_city,
                        iconColor: Colors.teal,
                        label: 'City',
                        value: city ?? 'Unknown City',
                      ),
                      const SizedBox(height: 10),
                      _buildMetaRow(
                        icon: Icons.my_location,
                        iconColor: Colors.blueGrey,
                        label: 'Coordinates',
                        value: coords ?? 'Unknown',
                      ),
                      const SizedBox(height: 10),
                      _buildMetaRow(
                        icon: Icons.gps_fixed,
                        iconColor: Colors.green.shade700,
                        label: 'Accuracy',
                        value: accuracy ?? 'Unknown',
                      ),
                    ],

                    const SizedBox(height: 20),

                    // Confirmation Action Buttons
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _retakePhoto,
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.grey.shade800,
                              side: BorderSide(color: Colors.grey.shade400),
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                            icon: const Icon(Icons.refresh, size: 18),
                            label: const Text('Retake Photo', style: TextStyle(fontWeight: FontWeight.bold)),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: (_isLocating || !hasLocation) ? null : _confirmAndUsePhoto,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primary,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                              elevation: 2,
                            ),
                            icon: const Icon(Icons.check_circle_outline, size: 18),
                            label: const Text('Use This Photo', style: TextStyle(fontWeight: FontWeight.bold)),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetaRow({
    required IconData icon,
    required Color iconColor,
    required String label,
    required String value,
    bool isLoading = false,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: iconColor, size: 18),
        const SizedBox(width: 10),
        SizedBox(
          width: 85,
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
          child: isLoading
              ? Row(
                  children: [
                    SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: iconColor),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      value,
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey.shade700,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                )
              : Text(
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
}
