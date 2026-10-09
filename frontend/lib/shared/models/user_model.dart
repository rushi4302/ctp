class UserModel {
  final int id;
  final String email;
  final String fullName;
  final String role;
  final bool isActive;

  UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.isActive = true,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      role: json['role'] as String,
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'role': role,
      'is_active': isActive,
    };
  }

  bool get isAdmin => role.toLowerCase() == 'admin';
  bool get isMunicipality => role.toLowerCase() == 'municipality' || isAdmin;
  bool get isCitizen => role.toLowerCase() == 'citizen';
}
