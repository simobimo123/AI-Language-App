import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import 'app_localizations.dart';
import 'app_localizations_en.dart';

/// Supplies localization objects for the additional interface locales.
///
/// The new locales intentionally reuse the English message set until their
/// complete native translations are added. This keeps the interface fully
/// selectable and avoids falling back to Arabic or an unsupported locale.
class ExtendedAppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const ExtendedAppLocalizationsDelegate();

  static const supportedLanguageCodes = <String>{
    'de',
    'id',
    'it',
    'nl',
    'pl',
    'pt',
    'ru',
    'th',
    'tr',
    'uk',
    'vi',
  };

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(
      AppLocalizationsEn(locale.languageCode),
    );
  }

  @override
  bool isSupported(Locale locale) =>
      supportedLanguageCodes.contains(locale.languageCode);

  @override
  bool shouldReload(ExtendedAppLocalizationsDelegate old) => false;
}
