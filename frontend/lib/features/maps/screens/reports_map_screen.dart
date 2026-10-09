import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/transparency_service.dart';

class ReportsMapScreen extends ConsumerStatefulWidget {
  const ReportsMapScreen({super.key});

  @override
  ConsumerState<ReportsMapScreen> createState() => _ReportsMapScreenState();
}

class _ReportsMapScreenState extends ConsumerState<ReportsMapScreen> {
  bool _useListView = false;

  static const CameraPosition _initialCameraPosition = CameraPosition(
    target: LatLng(18.5204, 73.8567), // Pune City Center
    zoom: 12,
  );

  final _transparencyService = TransparencyService();
  List<Map<String, dynamic>> _mapPoints = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchMapPoints();
  }

  Future<void> _fetchMapPoints() async {
    try {
      final points = await _transparencyService.getPublicMapPoints();
      setState(() {
        _mapPoints = points;
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }


  @override
  Widget build(BuildContext context) {
    final markers = _mapPoints.map((p) {
      return Marker(
        markerId: MarkerId('issue_${p['id']}'),
        position: LatLng(p['latitude'] as double, p['longitude'] as double),
        infoWindow: InfoWindow(
          title: '${p['category']}',
          snippet: '${p['status']} • ${p['report_count']} reports',
        ),
      );
    }).toSet();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Public Civic Map'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(_useListView ? Icons.map : Icons.format_list_bulleted),
            tooltip: _useListView ? 'Show Map' : 'Show List',
            onPressed: () => setState(() => _useListView = !_useListView),
          ),
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator()) 
        : _useListView
          ? ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: _mapPoints.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final p = _mapPoints[index];
                final statusColor = AppColors.getStatusColor(p['status'] as String);

                return Card(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: statusColor.withOpacity(0.2),
                      child: Icon(Icons.location_city, color: statusColor, size: 20),
                    ),
                    title: Text('${p['category']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text(
                      '${p['status']} • ${(p['latitude'] as double).toStringAsFixed(4)}, ${(p['longitude'] as double).toStringAsFixed(4)}',
                      style: const TextStyle(fontSize: 12),
                    ),
                    trailing: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(color: AppColors.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
                      child: Text('${p['report_count']} Reports', style: const TextStyle(fontSize: 10, color: AppColors.primary)),
                    ),
                  ),
                );
              },
            )
          : Stack(
              children: [
                Positioned.fill(
                  child: GoogleMap(
                    initialCameraPosition: _initialCameraPosition,
                    markers: markers,
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
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 8)],
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${_mapPoints.length} Public Issues in Pune',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                        TextButton(
                          onPressed: () => setState(() => _useListView = true),
                          child: const Text('View List'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
