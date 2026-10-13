import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
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

  static const CameraPosition _initialCameraPosition = CameraPosition(
    target: LatLng(18.5793, 73.9828), // Wagholi, Pune
    zoom: 12,
  );

  final _transparencyService = TransparencyService();
  static const _mapsChannel = MethodChannel('civic/maps');
  static const _webMapsKeyConfigured = bool.fromEnvironment('MAPS_API_KEY_CONFIGURED');
  List<Map<String, dynamic>> _mapPoints = [];
  bool _isLoading = true;
  bool _mapsApiKeyConfigured = false;
  bool _locationPermissionGranted = false;
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
    var mapsKeyConfigured = kIsWeb && _webMapsKeyConfigured;
    if (!kIsWeb) {
      try {
        mapsKeyConfigured =
            await _mapsChannel.invokeMethod<bool>('isMapsApiKeyConfigured') ??
            false;
      } on PlatformException {
        // The report list remains available when native map configuration fails.
      } on MissingPluginException {
        // The report list remains available on platforms without the Android channel.
      }
    }
    if (mapsKeyConfigured) {
      await _requestMapLocationPermission();
    }

    try {
      final points = await _transparencyService.getPublicMapPoints(
        category: _selectedCategory,
        status: _selectedStatus,
      );
      if (!mounted) return;
      setState(() {
        _mapPoints = points;
        _mapsApiKeyConfigured = mapsKeyConfigured;
        if (!mapsKeyConfigured) _useListView = true;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _mapsApiKeyConfigured = mapsKeyConfigured;
        if (!mapsKeyConfigured) _useListView = true;
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
        _locationPermissionGranted = permission == LocationPermission.whileInUse ||
            permission == LocationPermission.always;
      });
    } catch (_) {
      // Location is optional. The map and report list remain usable without it.
    }
  }

  void _showMarkerDetails(Map<String, dynamic> point) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${point['category']}', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text('Status: ${humanizeStatus(point['status'] as String)} • Severity: ${point['severity']}'),
            Text('Reports linked: ${point['report_count']}'),
            if (point['locality'] != null) Text('Area: ${point['locality']}'),
            Text('Coordinates: ${(point['latitude'] as num).toStringAsFixed(5)}, ${(point['longitude'] as num).toStringAsFixed(5)}'),
            if (point['is_synthetic'] == true)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text('Synthetic demonstration record — not official municipal data.', style: TextStyle(color: Colors.deepOrange)),
              ),
          ]),
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
                  const DropdownMenuItem<String?>(value: null, child: Text('All categories')),
                  ...const ['Pothole/Road Damage', 'Garbage', 'Water Leakage', 'Streetlight Issue', 'Drainage Problem', 'Traffic Issue']
                      .map((value) => DropdownMenuItem<String?>(value: value, child: Text(value))),
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
                  DropdownMenuItem<String?>(value: null, child: Text('All statuses')),
                  DropdownMenuItem<String?>(value: 'PENDING', child: Text('Pending')),
                  DropdownMenuItem<String?>(value: 'ASSIGNED', child: Text('Assigned')),
                  DropdownMenuItem<String?>(value: 'IN_PROGRESS', child: Text('In progress')),
                  DropdownMenuItem<String?>(value: 'RESOLVED', child: Text('Resolved')),
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
    final markers = _mapPoints
        .where((p) => p['latitude'] is num && p['longitude'] is num)
        .map((p) {
          return Marker(
            markerId: MarkerId('issue_${p['id']}'),
            position: LatLng(
              (p['latitude'] as num).toDouble(),
              (p['longitude'] as num).toDouble(),
            ),
            infoWindow: InfoWindow(
              title: '${p['category']}',
              snippet:
                  '${p['is_synthetic'] == true ? 'Demo example • ' : ''}${humanizeStatus(p['status'] as String)} • ${p['report_count']} reports',
            ),
            onTap: () => _showMarkerDetails(p),
          );
        })
        .toSet();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Public Civic Map'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(_useListView ? Icons.map : Icons.format_list_bulleted),
            tooltip: !_mapsApiKeyConfigured
                ? 'Configure a Maps key to enable the map'
                : _useListView
                    ? 'Show Map'
                    : 'Show List',
            onPressed: !_mapsApiKeyConfigured
                ? null
                : () => setState(() => _useListView = !_useListView),
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
                if (!_mapsApiKeyConfigured)
                  const MaterialBanner(
                    leading: Icon(Icons.map_outlined),
                    content: Text(
                      kIsWeb
                          ? 'Google Maps is not configured. Showing real complaint locations as a list. Set MAPS_API_KEY when building the web client to enable the map.'
                          : 'Google Maps is not configured. Showing real complaint locations as a list. Set MAPS_API_KEY in frontend/android/local.properties to enable the map.',
                    ),
                    actions: [
                      TextButton(onPressed: null, child: Text('List fallback')),
                    ],
                  ),
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
                  child: GoogleMap(
                    initialCameraPosition: _initialCameraPosition,
                    markers: markers,
                    myLocationButtonEnabled: _locationPermissionGranted,
                    myLocationEnabled: _locationPermissionGranted,
                    zoomControlsEnabled: true,
                  ),
                ),

                Positioned(
                  top: 12,
                  left: 12,
                  right: 12,
                  child: _buildFilters(),
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
                        Text(
                          '${_mapPoints.length} public issue locations',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
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
