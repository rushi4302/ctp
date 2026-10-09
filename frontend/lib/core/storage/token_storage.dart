import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  static const _storage = FlutterSecureStorage();

  static const String _keyToken = 'jwt_access_token';
  static const String _keyUserRole = 'user_role';
  static const String _keyUserEmail = 'user_email';
  static const String _keyUserName = 'user_name';
  static const String _keyUserId = 'user_id';

  static Future<void> saveToken(String token) async {
    await _storage.write(key: _keyToken, value: token);
  }

  static Future<String?> getToken() async {
    return await _storage.read(key: _keyToken);
  }

  static Future<void> saveUserData({
    required int id,
    required String email,
    required String fullName,
    required String role,
  }) async {
    await _storage.write(key: _keyUserId, value: id.toString());
    await _storage.write(key: _keyUserEmail, value: email);
    await _storage.write(key: _keyUserName, value: fullName);
    await _storage.write(key: _keyUserRole, value: role);
  }

  static Future<String?> getUserRole() async {
    return await _storage.read(key: _keyUserRole);
  }

  static Future<String?> getUserEmail() async {
    return await _storage.read(key: _keyUserEmail);
  }

  static Future<String?> getUserName() async {
    return await _storage.read(key: _keyUserName);
  }

  static Future<int?> getUserId() async {
    final str = await _storage.read(key: _keyUserId);
    if (str != null) return int.tryParse(str);
    return null;
  }

  static Future<void> clear() async {
    await _storage.deleteAll();
  }
}
