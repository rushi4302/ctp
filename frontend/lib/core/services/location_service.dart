import 'dart:async';
import 'package:dio/dio.dart';
import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';

/// Structured container holding civic GPS and reverse-geocoded location metadata.
class CivicLocationData {
  final double latitude;
  final double longitude;
  final double accuracy;
  final DateTime timestamp;
  final String? address;
  final String? landmark;
  final String? locality;
  final String? subLocality;
  final String? city;
  final String? district;
  final String? state;
  final String? postalCode;
  final String? country;

  const CivicLocationData({
    required this.latitude,
    required this.longitude,
    required this.accuracy,
    required this.timestamp,
    this.address,
    this.landmark,
    this.locality,
    this.subLocality,
    this.city,
    this.district,
    this.state,
    this.postalCode,
    this.country,
  });

  /// Best human-readable address line.
  String get displayAddress {
    if (address != null && address!.trim().isNotEmpty) {
      return address!.trim();
    }
    final parts = <String>[];
    if (landmark != null && landmark!.isNotEmpty) parts.add(landmark!);
    if (subLocality != null && subLocality!.isNotEmpty && subLocality != landmark) {
      parts.add(subLocality!);
    }
    if (locality != null && locality!.isNotEmpty && locality != subLocality) {
      parts.add(locality!);
    }
    if (city != null && city!.isNotEmpty && city != locality) {
      parts.add(city!);
    }
    if (state != null && state!.isNotEmpty) parts.add(state!);
    if (postalCode != null && postalCode!.isNotEmpty) parts.add(postalCode!);
    if (country != null && country!.isNotEmpty) parts.add(country!);

    if (parts.isNotEmpty) {
      return parts.join(', ');
    }
    return '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}';
  }

  /// Locality or area name (e.g. Wagholi)
  String get displayArea {
    if (locality != null && locality!.trim().isNotEmpty) {
      return locality!.trim();
    }
    if (subLocality != null && subLocality!.trim().isNotEmpty) {
      return subLocality!.trim();
    }
    if (district != null && district!.trim().isNotEmpty) {
      return district!.trim();
    }
    return 'Area not detected';
  }

  /// City name (e.g. Pune)
  String get displayCity {
    if (city != null && city!.trim().isNotEmpty) {
      return city!.trim();
    }
    if (district != null && district!.trim().isNotEmpty) {
      return district!.trim();
    }
    if (locality != null && locality!.trim().isNotEmpty) {
      return locality!.trim();
    }
    return 'City not detected';
  }

  /// Formatted coordinates string
  String get coordinatesFormatted =>
      '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}';

  /// Formatted accuracy string
  String get accuracyFormatted => '${accuracy.toStringAsFixed(1)} m';

  CivicLocationData copyWith({
    double? latitude,
    double? longitude,
    double? accuracy,
    DateTime? timestamp,
    String? address,
    String? landmark,
    String? locality,
    String? subLocality,
    String? city,
    String? district,
    String? state,
    String? postalCode,
    String? country,
  }) {
    return CivicLocationData(
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      accuracy: accuracy ?? this.accuracy,
      timestamp: timestamp ?? this.timestamp,
      address: address ?? this.address,
      landmark: landmark ?? this.landmark,
      locality: locality ?? this.locality,
      subLocality: subLocality ?? this.subLocality,
      city: city ?? this.city,
      district: district ?? this.district,
      state: state ?? this.state,
      postalCode: postalCode ?? this.postalCode,
      country: country ?? this.country,
    );
  }
}

class LocationException implements Exception {
  final String message;
  const LocationException(this.message);

  @override
  String toString() => message;
}

class LocationServiceDisabledException extends LocationException {
  const LocationServiceDisabledException()
      : super('Device location service (GPS) is disabled. Please enable GPS in settings.');
}

class LocationPermissionDeniedException extends LocationException {
  const LocationPermissionDeniedException()
      : super('Location permission was denied. Permission is required to tag civic reports.');
}

class LocationPermissionPermanentlyDeniedException extends LocationException {
  const LocationPermissionPermanentlyDeniedException()
      : super('Location permission is permanently denied. Please enable location permissions in app settings.');
}

/// Service abstraction for GPS acquisition and reverse geocoding.
class LocationService {
  final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(seconds: 5),
  ));

  /// Checks if device GPS location services are active.
  Future<bool> isLocationServiceEnabled() async {
    return await Geolocator.isLocationServiceEnabled();
  }

  /// Checks current location permission state.
  Future<LocationPermission> checkPermission() async {
    return await Geolocator.checkPermission();
  }

  /// Requests location permission from the citizen.
  Future<LocationPermission> requestPermission() async {
    return await Geolocator.requestPermission();
  }

  /// Opens the device app settings screen.
  Future<bool> openAppSettings() async {
    return await Geolocator.openAppSettings();
  }

  /// Opens the device location settings screen.
  Future<bool> openLocationSettings() async {
    return await Geolocator.openLocationSettings();
  }

  /// Acquires high-accuracy GPS coordinates and optionally reverse geocodes them.
  Future<CivicLocationData> getCurrentLocation({bool doReverseGeocode = true}) async {
    // 1. Verify service enabled
    final serviceEnabled = await isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw const LocationServiceDisabledException();
    }

    // 2. Verify / Request permissions
    var permission = await checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await requestPermission();
    }

    if (permission == LocationPermission.denied) {
      throw const LocationPermissionDeniedException();
    }

    if (permission == LocationPermission.deniedForever) {
      throw const LocationPermissionPermanentlyDeniedException();
    }

    // 3. Acquire GPS position
    Position? pos;
    try {
      pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 15),
      );
    } catch (_) {
      // Fallback to last known position if current request timed out
      pos = await Geolocator.getLastKnownPosition();
    }

    if (pos == null) {
      throw const LocationException('Unable to acquire GPS fix. Please ensure you are outdoors or near a window.');
    }

    final baseData = CivicLocationData(
      latitude: pos.latitude,
      longitude: pos.longitude,
      accuracy: pos.accuracy,
      timestamp: pos.timestamp,
    );

    if (!doReverseGeocode) {
      return baseData;
    }

    // 4. Reverse geocode
    return await reverseGeocode(
      pos.latitude,
      pos.longitude,
      accuracy: pos.accuracy,
      timestamp: pos.timestamp,
    );
  }

  /// Reverse geocodes coordinates to a human-readable address and structured fields.
  /// Falls back cleanly without fabricating any landmark names.
  Future<CivicLocationData> reverseGeocode(
    double latitude,
    double longitude, {
    double accuracy = 0.0,
    DateTime? timestamp,
  }) async {
    final captureTime = timestamp ?? DateTime.now();

    // 1. Try native platform geocoder
    try {
      final placemarks = await placemarkFromCoordinates(
        latitude,
        longitude,
      ).timeout(const Duration(seconds: 8));

      if (placemarks.isNotEmpty) {
        final place = placemarks.first;

        final landmark = _cleanString(place.name);
        final street = _cleanString(place.street);
        final subLocality = _cleanString(place.subLocality);
        final locality = _cleanString(place.locality);
        final district = _cleanString(place.subAdministrativeArea);
        final state = _cleanString(place.administrativeArea);
        final postalCode = _cleanString(place.postalCode);
        final country = _cleanString(place.country);

        // Check if landmark is a meaningful POI name (not street number or repetition)
        String? meaningfulLandmark;
        if (landmark != null &&
            landmark.isNotEmpty &&
            landmark != street &&
            landmark != postalCode &&
            !_isJustNumber(landmark)) {
          meaningfulLandmark = landmark;
        }

        final addressParts = <String>[];
        if (meaningfulLandmark != null) addressParts.add(meaningfulLandmark);
        if (street != null && street != meaningfulLandmark && street.isNotEmpty) {
          addressParts.add(street);
        }
        if (subLocality != null && subLocality.isNotEmpty && !addressParts.contains(subLocality)) {
          addressParts.add(subLocality);
        }
        if (locality != null && locality.isNotEmpty && !addressParts.contains(locality)) {
          addressParts.add(locality);
        }
        if (district != null && district.isNotEmpty && !addressParts.contains(district)) {
          addressParts.add(district);
        }
        if (state != null && state.isNotEmpty && !addressParts.contains(state)) {
          addressParts.add(state);
        }
        if (postalCode != null && postalCode.isNotEmpty) {
          addressParts.add(postalCode);
        }
        if (country != null && country.isNotEmpty && !addressParts.contains(country)) {
          addressParts.add(country);
        }

        final fullAddress = addressParts.isNotEmpty
            ? addressParts.join(', ')
            : '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}';

        return CivicLocationData(
          latitude: latitude,
          longitude: longitude,
          accuracy: accuracy,
          timestamp: captureTime,
          address: fullAddress,
          landmark: meaningfulLandmark,
          locality: (locality != null && locality.isNotEmpty) ? locality : subLocality,
          subLocality: subLocality,
          city: (locality != null && locality.isNotEmpty) ? locality : district,
          district: district,
          state: state,
          postalCode: postalCode,
          country: country,
        );
      }
    } catch (_) {
      // Native geocoder failed or timed out; try network fallback
    }

    // 2. Network Fallback: OpenStreetMap Nominatim
    try {
      final response = await _dio.get(
        'https://nominatim.openstreetmap.org/reverse',
        queryParameters: {
          'format': 'json',
          'lat': latitude,
          'lon': longitude,
          'zoom': 18,
          'addressdetails': 1,
        },
        options: Options(
          headers: {'User-Agent': 'CivicIntelligencePlatform/1.0'},
        ),
      );

      if (response.statusCode == 200 && response.data is Map<String, dynamic>) {
        final data = response.data as Map<String, dynamic>;
        final addressMap = data['address'] as Map<String, dynamic>? ?? {};

        final displayName = data['display_name'] as String?;
        final amenity = _cleanString(addressMap['amenity'] as String?) ??
            _cleanString(addressMap['building'] as String?) ??
            _cleanString(addressMap['college'] as String?) ??
            _cleanString(addressMap['university'] as String?);

        final suburb = _cleanString(addressMap['suburb'] as String?) ??
            _cleanString(addressMap['neighbourhood'] as String?);
        final city = _cleanString(addressMap['city'] as String?) ??
            _cleanString(addressMap['town'] as String?) ??
            _cleanString(addressMap['village'] as String?);
        final district = _cleanString(addressMap['state_district'] as String?) ??
            _cleanString(addressMap['county'] as String?);
        final state = _cleanString(addressMap['state'] as String?);
        final postcode = _cleanString(addressMap['postcode'] as String?);
        final country = _cleanString(addressMap['country'] as String?);

        return CivicLocationData(
          latitude: latitude,
          longitude: longitude,
          accuracy: accuracy,
          timestamp: captureTime,
          address: displayName ?? '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}',
          landmark: amenity,
          locality: suburb ?? city,
          subLocality: suburb,
          city: city ?? district,
          district: district,
          state: state,
          postalCode: postcode,
          country: country,
        );
      }
    } catch (_) {
      // Both geocoders failed (e.g. offline)
    }

    // 3. Graceful offline fallback: keep exact coordinates, do not fabricate place name
    return CivicLocationData(
      latitude: latitude,
      longitude: longitude,
      accuracy: accuracy,
      timestamp: captureTime,
      address: '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}',
      locality: null,
      subLocality: null,
      city: null,
      district: null,
      state: null,
      postalCode: null,
      country: null,
    );
  }

  static String? _cleanString(String? val) {
    if (val == null) return null;
    final trimmed = val.trim();
    return trimmed.isNotEmpty ? trimmed : null;
  }

  static bool _isJustNumber(String str) {
    return RegExp(r'^[0-9\-\+/ ]+$').hasMatch(str.trim());
  }
}
