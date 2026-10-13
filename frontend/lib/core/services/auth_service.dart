import '../constants/api_constants.dart';

import '../network/api_client.dart';
import '../storage/token_storage.dart';
import '../../shared/models/user_model.dart';

class AuthService {
  final ApiClient _client = ApiClient();

  Future<UserModel> login({required String email, required String password}) async {
    try {
      final response = await _client.dio.post(
        ApiConstants.login,
        data: {
          'email': email.trim(),
          'password': password,
        },
      );

      final token = response.data['access_token'] as String;
      await TokenStorage.saveToken(token);

      // Fetch user profile
      final user = await getMe();
      await TokenStorage.saveUserData(
        id: user.id,
        email: user.email,
        fullName: user.fullName,
        role: user.role,
      );

      return user;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<UserModel> register({
    required String email,
    required String password,
    required String fullName,
    String role = 'citizen',
  }) async {
    try {
      final response = await _client.dio.post(
        ApiConstants.register,
        data: {
          'email': email.trim(),
          'password': password,
          'full_name': fullName.trim(),
          'role': role,
        },
      );
      return UserModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<UserModel> getMe() async {
    try {
      final response = await _client.dio.get(ApiConstants.me);
      return UserModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<UserModel> updateProfile({required String fullName, required String email}) async {
    try {
      final response = await _client.dio.patch(
        ApiConstants.userProfile,
        data: {'full_name': fullName.trim(), 'email': email.trim()},
      );
      final user = UserModel.fromJson(response.data as Map<String, dynamic>);
      await TokenStorage.saveUserData(
        id: user.id,
        email: user.email,
        fullName: user.fullName,
        role: user.role,
      );
      return user;
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<String> forgotPassword(String email) async {
    try {
      final response = await _client.dio.post(
        ApiConstants.forgotPassword,
        data: {'email': email.trim()},
      );
      return response.data['message'] as String? ?? 'Password reset link sent.';
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<String> resetPassword({
    required String token,
    required String newPassword,
  }) async {
    try {
      final response = await _client.dio.post(
        ApiConstants.resetPassword,
        data: {
          'token': token.trim(),
          'new_password': newPassword,
        },
      );
      return response.data['message'] as String? ?? 'Password reset successful.';
    } catch (e) {
      throw ApiClient.getErrorMessage(e);
    }
  }

  Future<void> logout() async {
    await TokenStorage.clear();
  }
}
