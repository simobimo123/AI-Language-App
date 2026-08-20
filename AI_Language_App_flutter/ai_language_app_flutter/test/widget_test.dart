import 'package:flutter_test/flutter_test.dart';

import 'package:ai_language_app_flutter/main.dart';
import 'package:ai_language_app_flutter/services/theme_controller.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    final themeController = ThemeController();

    await tester.pumpWidget(
      MyApp(
        themeController: themeController,
      ),
    );

    await tester.pumpAndSettle();

    expect(find.byType(MyApp), findsOneWidget);
  });
}