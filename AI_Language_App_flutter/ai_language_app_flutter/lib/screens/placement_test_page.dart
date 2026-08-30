import 'package:flutter/material.dart';

import '../controllers/placement_test_controller.dart';
import '../core/language/language_controller.dart';
import '../core/theme/theme_controller.dart';
import '../widgets/placement/placement_test_view.dart';

class PlacementTestPage extends StatefulWidget {
  final ThemeController themeController;
  final LanguageController languageController;
  final String language;

  const PlacementTestPage({
    super.key,
    required this.themeController,
    required this.languageController,
    required this.language,
  });

  @override
  State<PlacementTestPage> createState() => _PlacementTestPageState();
}

class _PlacementTestPageState extends State<PlacementTestPage> {
  late final PlacementTestController controller;

  @override
  void initState() {
    super.initState();

    controller = PlacementTestController(
      language: widget.language,
    )..addListener(_onControllerChanged);

    controller.initialize();
  }

  void _onControllerChanged() {
    if (!mounted) return;

    if (controller.isFinished && controller.finalLevel != null) {
      final level = controller.finalLevel!;
      controller.isFinished = false;
      Navigator.pop(context, level);
    }

    setState(() {});
  }

  @override
  void dispose() {
    controller.removeListener(_onControllerChanged);
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          controller.isQuizMode
              ? _text(ar: 'اختبار التأكيد', en: 'Confirmation test')
              : _text(ar: 'اختبار تحديد المستوى', en: 'Placement test'),
        ),
      ),
      body: PlacementTestView(
        controller: controller,
        themeController: widget.themeController,
        languageController: widget.languageController,
      ),
    );
  }

  String _text({required String ar, required String en}) {
    return widget.languageController.locale.languageCode == 'ar' ? ar : en;
  }
}
