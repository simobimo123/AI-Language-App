import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../services/theme_controller.dart';
import 'login_page.dart';

class ProfilePage extends StatefulWidget {
  final ThemeController themeController;

  const ProfilePage({super.key, required this.themeController});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final ApiService apiService = ApiService();
  final StorageService storageService = StorageService();

  String name = 'Loading...';
  String email = '';
  String userId = '';
  String nativeLanguage = '';
  String learningLanguage = '';

  bool isLoading = true;

  @override
  void initState() {
    super.initState();

    loadProfile();
  }

  Future<void> loadProfile() async {
    try {
      final user = await apiService.getCurrentUser();

      if (!mounted) return;

      setState(() {
        name = user['name'] ?? 'Learner';
        email = user['email'] ?? '';
        userId = user['id']?.toString() ?? '';
        nativeLanguage = _languageName(user['native_language']);
        learningLanguage = _languageName(user['learning_language']);
        isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        name = 'Unable to load profile';
      });
    }
  }

  String _languageName(dynamic code) {
    const languages = {
      'ar': 'العربية',
      'en': 'الإنجليزية',
      'fr': 'الفرنسية',
      'es': 'الإسبانية',
      'de': 'الألمانية',
      'tr': 'التركية',
    };
    return languages[code] ?? code?.toString() ?? '';
  }

  Future<void> logout() async {
    await storageService.deleteToken();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (_) => LoginPage(themeController: widget.themeController),
      ),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,

      appBar: AppBar(
        backgroundColor: const Color(0xFFF7F7FB),
        elevation: 0,
        title: const Text(
          'حسابي',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),

      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const SizedBox(height: 10),

                Center(
                  child: Container(
                    width: 92,
                    height: 92,
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primaryContainer,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.person_rounded,
                      size: 48,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                Center(
                  child: Text(
                    name,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),

                const SizedBox(height: 6),

                Center(
                  child: Text(
                    email,
                    style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                  ),
                ),

                const SizedBox(height: 30),

                _ProfileInfoCard(
                  icon: Icons.person_outline_rounded,
                  title: 'الاسم',
                  value: name,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.email_outlined,
                  title: 'البريد الإلكتروني',
                  value: email,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.badge_outlined,
                  title: 'رقم المستخدم',
                  value: userId,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.translate_rounded,
                  title: 'لغتك الأم',
                  value: nativeLanguage,
                ),

                const SizedBox(height: 12),

                _ProfileInfoCard(
                  icon: Icons.school_outlined,
                  title: 'لغة التعلّم',
                  value: learningLanguage,
                ),

                const SizedBox(height: 24),

                Text(
                  'مظهر التطبيق',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 12),

                _ThemeSettingsCard(themeController: widget.themeController),

                const SizedBox(height: 30),

                SizedBox(
                  height: 52,
                  child: OutlinedButton.icon(
                    onPressed: logout,
                    icon: const Icon(Icons.logout_rounded),
                    label: const Text(
                      'تسجيل الخروج',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: BorderSide(color: Colors.red.shade200),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

class _ProfileInfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _ProfileInfoCard({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: theme.colorScheme.onPrimaryContainer),
          ),

          const SizedBox(width: 14),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                ),

                const SizedBox(height: 4),

                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ThemeSettingsCard extends StatelessWidget {
  final ThemeController themeController;

  const _ThemeSettingsCard({required this.themeController});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: SegmentedButton<ThemeMode>(
        segments: const [
          ButtonSegment(
            value: ThemeMode.system,
            icon: Icon(Icons.brightness_auto_rounded),
            label: Text('تلقائي'),
          ),
          ButtonSegment(
            value: ThemeMode.light,
            icon: Icon(Icons.light_mode_outlined),
            label: Text('فاتح'),
          ),
          ButtonSegment(
            value: ThemeMode.dark,
            icon: Icon(Icons.dark_mode_outlined),
            label: Text('داكن'),
          ),
        ],
        selected: {themeController.themeMode},
        onSelectionChanged: (selection) {
          themeController.setThemeMode(selection.first);
        },
        showSelectedIcon: false,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          textStyle: WidgetStatePropertyAll(theme.textTheme.labelMedium),
        ),
      ),
    );
  }
}
