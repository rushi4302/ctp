import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../../core/constants/app_colors.dart';

class SingleLocationMapScreen extends StatefulWidget {
  final double latitude;
  final double longitude;
  final String title;
  final String snippet;
  final String? status;

  const SingleLocationMapScreen({
    super.key,
    required this.latitude,
    required this.longitude,
    required this.title,
    required this.snippet,
    this.status,
  });

  @override
  State<SingleLocationMapScreen> createState() => _SingleLocationMapScreenState();
}

class _SingleLocationMapScreenState extends State<SingleLocationMapScreen> {
  late CameraPosition _initialCameraPosition;
  late Set<Marker> _markers;

  @override
  void initState() {
    super.initState();
    _initialCameraPosition = CameraPosition(
      target: LatLng(widget.latitude, widget.longitude),
      zoom: 16,
    );
    _markers = {
      Marker(
        markerId: const MarkerId('single_location'),
        position: LatLng(widget.latitude, widget.longitude),
        infoWindow: InfoWindow(
          title: widget.title,
          snippet: widget.snippet,
        ),
      ),
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Location Map'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: GoogleMap(
              initialCameraPosition: _initialCameraPosition,
              markers: _markers,
              myLocationButtonEnabled: false,
              myLocationEnabled: false,
              zoomControlsEnabled: true,
            ),
          ),
          Positioned(
            bottom: 20,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 8)],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.title,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    widget.snippet,
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 14),
                  ),
                  if (widget.status != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.getStatusColor(widget.status!).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        widget.status!,
                        style: TextStyle(
                          color: AppColors.getStatusColor(widget.status!),
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ]
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
