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
      return;
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
    return AnimatedBuilder(
      animation: widget.languageController,
      builder: (context, _) {
        final code = widget.languageController.locale.languageCode;

        return Scaffold(
          appBar: AppBar(
            title: Text(
              _placementTitle(code),
            ),
          ),
          body: PlacementTestView(
            controller: controller,
            themeController: widget.themeController,
            languageController: widget.languageController,
          ),
        );
      },
    );
  }

  String _placementTitle(String code) {
    const values = <String, String>{
      'ar': 'اختبار تحديد المستوى',
      'en': 'Placement test',
      'fr': 'Test de placement',
      'es': 'Prueba de nivel',
      'zh': '分级测试',
      'ja': 'レベル判定テスト',
      'ko': '레벨 테스트',
      'de': 'Einstufungstest',
      'id': 'Tes penempatan',
      'it': 'Test di livello',
      'nl': 'Niveautest',
      'pl': 'Test poziomujący',
      'pt': 'Teste de nivelamento',
      'ru': 'Тест на определение уровня',
      'th': 'แบบทดสอบวัดระดับ',
      'tr': 'Seviye belirleme testi',
      'uk': 'Тест на визначення рівня',
      'vi': 'Bài kiểm tra trình độ',
    };

    return values[code] ?? values['en']!;
  }
}
