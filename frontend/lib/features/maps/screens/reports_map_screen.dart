import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/transparency_service.dart';
import '../../../shared/utils/complaint_presentation.dart';

class ReportsMapScreen extends ConsumerStatefulWidget {
  const ReportsMapScreen({super.key});

  @override
  ConsumerState<ReportsMapScreen> createState() => _ReportsMapScreenState();
}

class _ReportsMapScreenState extends ConsumerState<ReportsMapScreen> {
  bool _useListView = false;
  String? _selectedCategory;
  String? _selectedStatus;

  static const LatLng _initialCenter = LatLng(18.5793, 73.9828);
  static const double _initialZoom = 12;

  final _transparencyService = TransparencyService();
  final MapController _mapController = MapController();
  List<Map<String, dynamic>> _mapPoints = [];
  bool _isLoading = true;
  bool _locationPermissionGranted = false;
  LatLng? _currentLocation;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _loadMapPoints();
  }

  Future<void> _loadMapPoints() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final points = await _transparencyService.getPublicMapPoints(
        category: _selectedCategory,
        status: _selectedStatus,
      );
      if (!mounted) return;
      setState(() {
        _mapPoints = points;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loadError = error.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _requestMapLocationPermission() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return;
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (!mounted) return;
      setState(() {
        _locationPermissionGranted =
            permission == LocationPermission.whileInUse ||
            permission == LocationPermission.always;
      });
    } catch (_) {
      // Location is optional. The map and report list remain usable without it.
    }
  }

  Future<void> _centerOnCurrentLocation() async {
    if (!_locationPermissionGranted) {
      await _requestMapLocationPermission();
    }
    if (!_locationPermissionGranted || !mounted) return;

    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
        ),
      );
      if (!mounted) return;
      final location = LatLng(position.latitude, position.longitude);
      setState(() => _currentLocation = location);
      _mapController.move(location, 15);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Current location is unavailable.')),
      );
    }
  }

  IconData _categoryIcon(dynamic category) => switch (category) {
    'Pothole/Road Damage' => Icons.add_road,
    'Garbage' => Icons.delete_outline,
    'Water Leakage' => Icons.water_drop_outlined,
    'Streetlight Issue' => Icons.lightbulb_outline,
    'Drainage Problem' => Icons.water_outlined,
    'Traffic Issue' => Icons.traffic,
    _ => Icons.location_on,
  };

  List<Marker> _buildMarkers() {
    final markers = _mapPoints
        .where((point) => point['latitude'] is num && point['longitude'] is num)
        .map((point) {
          final statusColor = AppColors.getStatusColor(
            point['status'] as String,
          );
          return Marker(
            point: LatLng(
              (point['latitude'] as num).toDouble(),
              (point['longitude'] as num).toDouble(),
            ),
            width: 48,
            height: 48,
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => _showMarkerDetails(point),
              child: Center(
                child: Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: statusColor,
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 2),
                    boxShadow: const [
                      BoxShadow(color: Colors.black26, blurRadius: 4),
                    ],
                  ),
                  child: Icon(
                    _categoryIcon(point['category']),
                    color: Colors.white,
                    size: 21,
                  ),
                ),
              ),
            ),
          );
        })
        .toList();

    final currentLocation = _currentLocation;
    if (currentLocation != null) {
      markers.add(
        Marker(
          point: currentLocation,
          width: 24,
          height: 24,
          child: Container(
            decoration: BoxDecoration(
              color: Colors.blue,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 3),
              boxShadow: const [
                BoxShadow(color: Colors.black38, blurRadius: 4),
              ],
            ),
          ),
        ),
      );
    }
    return markers;
  }

  void _showMarkerDetails(Map<String, dynamic> point) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${point['category']}',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Status: ${humanizeStatus(point['status'] as String)} • Severity: ${point['severity']}',
              ),
              Text('Reports linked: ${point['report_count']}'),
              if (point['locality'] != null) Text('Area: ${point['locality']}'),
              Text(
                'Coordinates: ${(point['latitude'] as num).toStringAsFixed(5)}, ${(point['longitude'] as num).toStringAsFixed(5)}',
              ),
              if (point['is_synthetic'] == true)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text(
                    'Synthetic demonstration record — not official municipal data.',
                    style: TextStyle(color: Colors.deepOrange),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilters() => Material(
    color: Colors.white,
    elevation: 3,
    borderRadius: BorderRadius.circular(12),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Wrap(
        spacing: 12,
        runSpacing: 4,
        children: [
          DropdownButton<String?>(
            value: _selectedCategory,
            hint: const Text('All categories'),
            items: [
              const DropdownMenuItem<String?>(
                value: null,
                child: Text('All categories'),
              ),
              ...const [
                'Pothole/Road Damage',
                'Garbage',
                'Water Leakage',
                'Streetlight Issue',
                'Drainage Problem',
                'Traffic Issue',
              ].map(
                (value) =>
                    DropdownMenuItem<String?>(value: value, child: Text(value)),
              ),
            ],
            onChanged: (value) {
              setState(() => _selectedCategory = value);
              _loadMapPoints();
            },
          ),
          DropdownButton<String?>(
            value: _selectedStatus,
            hint: const Text('All statuses'),
            items: const [
              DropdownMenuItem<String?>(
                value: null,
                child: Text('All statuses'),
              ),
              DropdownMenuItem<String?>(
                value: 'PENDING',
                child: Text('Pending'),
              ),
              DropdownMenuItem<String?>(
                value: 'ASSIGNED',
                child: Text('Assigned'),
              ),
              DropdownMenuItem<String?>(
                value: 'IN_PROGRESS',
                child: Text('In Progress'),
              ),
              DropdownMenuItem<String?>(
                value: 'RESOLVED',
                child: Text('Resolved'),
              ),
              DropdownMenuItem<String?>(value: 'CLOSED', child: Text('Closed')),
            ],
            onChanged: (value) {
              setState(() => _selectedStatus = value);
              _loadMapPoints();
            },
          ),
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
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
          : _loadError != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.cloud_off, size: 40, color: Colors.grey),
                    const SizedBox(height: 12),
                    Text(
                      'Could not load public issue locations: $_loadError',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: _loadMapPoints,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            )
          : _useListView
          ? Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: _buildFilters(),
                ),
                Expanded(
                  child: _mapPoints.isEmpty
                      ? const Center(
                          child: Text(
                            'No public civic issues with saved coordinates yet.',
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: _mapPoints.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 12),
                          itemBuilder: (context, index) {
                            final p = _mapPoints[index];
                            final statusColor = AppColors.getStatusColor(
                              p['status'] as String,
                            );

                            return Card(
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: statusColor.withOpacity(0.2),
                                  child: Icon(
                                    Icons.location_city,
                                    color: statusColor,
                                    size: 20,
                                  ),
                                ),
                                title: Text(
                                  '${p['category']}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                subtitle: Text(
                                  '${p['is_synthetic'] == true ? 'Demo example • ' : ''}${humanizeStatus(p['status'] as String)} • ${(p['latitude'] as num).toStringAsFixed(4)}, ${(p['longitude'] as num).toStringAsFixed(4)}',
                                  style: const TextStyle(fontSize: 12),
                                ),
                                trailing: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: AppColors.primary.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    '${p['report_count']} Reports',
                                    style: const TextStyle(
                                      fontSize: 10,
                                      color: AppColors.primary,
                                    ),
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            )
          : Stack(
              children: [
                Positioned.fill(
                  child: FlutterMap(
                    mapController: _mapController,
                    options: const MapOptions(
                      initialCenter: _initialCenter,
                      initialZoom: _initialZoom,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.example.frontend',
                      ),
                      MarkerLayer(markers: _buildMarkers()),
                    ],
                  ),
                ),

                Positioned(
                  top: 12,
                  left: 12,
                  right: 12,
                  child: _buildFilters(),
                ),

                Positioned(
                  top: 80,
                  right: 12,
                  child: FloatingActionButton.small(
                    heroTag: 'center_on_location',
                    tooltip: 'Center on my location (optional)',
                    onPressed: _centerOnCurrentLocation,
                    child: const Icon(Icons.my_location),
                  ),
                ),

                Positioned(
                  bottom: 20,
                  left: 20,
                  right: 20,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: const [
                        BoxShadow(color: Colors.black12, blurRadius: 8),
                      ],
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${_mapPoints.length} public issue locations',
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const Text(
                              '© OpenStreetMap contributors',
                              style: TextStyle(
                                fontSize: 10,
                                color: Colors.grey,
                              ),
                            ),
                          ],
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
