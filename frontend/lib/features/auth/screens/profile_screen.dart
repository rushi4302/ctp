import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/app_colors.dart';
import '../providers/auth_provider.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  bool _loaded = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_loaded) {
      final user = ref.read(authProvider).user;
      _name.text = user?.fullName ?? '';
      _email.text = user?.email ?? '';
      _loaded = true;
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final ok = await ref.read(authProvider.notifier).updateProfile(
          fullName: _name.text,
          email: _email.text,
        );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok ? 'Profile updated.' : ref.read(authProvider).errorMessage ?? 'Profile update failed.'),
      backgroundColor: ok ? Colors.green : Colors.red,
    ));
    if (ok) context.pop();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Your profile'), backgroundColor: AppColors.primary, foregroundColor: Colors.white),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: ListView(padding: const EdgeInsets.all(24), shrinkWrap: true, children: [
            const Icon(Icons.account_circle_outlined, size: 64, color: AppColors.primary),
            const SizedBox(height: 12),
            Text('Account role: ${state.user?.role ?? 'citizen'}', textAlign: TextAlign.center),
            const SizedBox(height: 24),
            Form(
              key: _formKey,
              child: Column(children: [
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Full name', border: OutlineInputBorder()),
                  validator: (value) => value == null || value.trim().isEmpty ? 'Enter your name.' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder()),
                  validator: (value) => value == null || !value.contains('@') ? 'Enter a valid email.' : null,
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: state.isLoading ? null : _save,
                    child: state.isLoading ? const CircularProgressIndicator() : const Text('Save profile'),
                  ),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
