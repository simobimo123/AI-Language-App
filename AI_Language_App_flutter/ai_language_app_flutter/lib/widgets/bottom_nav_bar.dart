import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/app_localizations.dart';

class AppBottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onItemSelected;

  const AppBottomNavBar({
    super.key,
    required this.currentIndex,
    required this.onItemSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: theme.dividerColor.withValues(alpha: 0.15),
            width: 1,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 20,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          HapticFeedback.mediumImpact();
          onItemSelected(index);
        },
        height: 76,
        backgroundColor: Colors.transparent,
        elevation: 0,
        indicatorColor: theme.colorScheme.primaryContainer,
        indicatorShape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
        ),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        animationDuration: const Duration(milliseconds: 300),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: Icon(
              Icons.home_rounded,
              color: theme.colorScheme.onPrimaryContainer,
            ),
            label: l10n.home,
          ),

          NavigationDestination(
            icon: const Icon(Icons.route_outlined),
            selectedIcon: Icon(
              Icons.route_rounded,
              color: theme.colorScheme.onPrimaryContainer,
            ),
            label: _learningPathLabel(context),
          ),

          NavigationDestination(
            icon: const Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(
              Icons.menu_book_rounded,
              color: theme.colorScheme.onPrimaryContainer,
            ),
            label: l10n.words,
          ),

          NavigationDestination(
            icon: const Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(
              Icons.person_rounded,
              color: theme.colorScheme.onPrimaryContainer,
            ),
            label: l10n.account,
          ),
        ],
      ),
    );
  }

  String _learningPathLabel(BuildContext context) {
    switch (Localizations.localeOf(context).languageCode) {
      case 'ar':
        return 'المسار';
      case 'fr':
        return 'Parcours';
      case 'es':
        return 'Ruta';
      case 'zh':
        return '学习路径';
      case 'ja':
        return '学習パス';
      case 'ko':
        return '학습 경로';
      case 'en':
      default:
        return 'Path';
    }
  }
}
