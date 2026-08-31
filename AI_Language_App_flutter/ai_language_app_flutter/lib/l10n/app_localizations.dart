import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_de.dart';
import 'app_localizations_en.dart';
import 'app_localizations_es.dart';
import 'app_localizations_fr.dart';
import 'app_localizations_id.dart';
import 'app_localizations_it.dart';
import 'app_localizations_ja.dart';
import 'app_localizations_ko.dart';
import 'app_localizations_nl.dart';
import 'app_localizations_pl.dart';
import 'app_localizations_pt.dart';
import 'app_localizations_ru.dart';
import 'app_localizations_th.dart';
import 'app_localizations_tr.dart';
import 'app_localizations_uk.dart';
import 'app_localizations_vi.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('de'),
    Locale('en'),
    Locale('es'),
    Locale('fr'),
    Locale('id'),
    Locale('it'),
    Locale('ja'),
    Locale('ko'),
    Locale('nl'),
    Locale('pl'),
    Locale('pt'),
    Locale('ru'),
    Locale('th'),
    Locale('tr'),
    Locale('uk'),
    Locale('vi'),
    Locale('zh'),
  ];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'AI Language Tutor'**
  String get appName;

  /// No description provided for @welcome.
  ///
  /// In en, this message translates to:
  /// **'Welcome'**
  String get welcome;

  /// No description provided for @welcomeBack.
  ///
  /// In en, this message translates to:
  /// **'Welcome back 👋'**
  String get welcomeBack;

  /// No description provided for @continueLearning.
  ///
  /// In en, this message translates to:
  /// **'Are you ready to continue learning?'**
  String get continueLearning;

  /// No description provided for @home.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get home;

  /// No description provided for @profile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profile;

  /// No description provided for @words.
  ///
  /// In en, this message translates to:
  /// **'My Words'**
  String get words;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @appLanguage.
  ///
  /// In en, this message translates to:
  /// **'App Language'**
  String get appLanguage;

  /// No description provided for @learningLanguage.
  ///
  /// In en, this message translates to:
  /// **'Learning Language'**
  String get learningLanguage;

  /// No description provided for @arabic.
  ///
  /// In en, this message translates to:
  /// **'Arabic'**
  String get arabic;

  /// No description provided for @english.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get english;

  /// No description provided for @french.
  ///
  /// In en, this message translates to:
  /// **'French'**
  String get french;

  /// No description provided for @spanish.
  ///
  /// In en, this message translates to:
  /// **'Spanish'**
  String get spanish;

  /// No description provided for @chinese.
  ///
  /// In en, this message translates to:
  /// **'Chinese'**
  String get chinese;

  /// No description provided for @japanese.
  ///
  /// In en, this message translates to:
  /// **'Japanese'**
  String get japanese;

  /// No description provided for @korean.
  ///
  /// In en, this message translates to:
  /// **'Korean'**
  String get korean;

  /// No description provided for @lightMode.
  ///
  /// In en, this message translates to:
  /// **'Light mode'**
  String get lightMode;

  /// No description provided for @darkMode.
  ///
  /// In en, this message translates to:
  /// **'Dark mode'**
  String get darkMode;

  /// No description provided for @systemMode.
  ///
  /// In en, this message translates to:
  /// **'System settings'**
  String get systemMode;

  /// No description provided for @auto.
  ///
  /// In en, this message translates to:
  /// **'Automatic'**
  String get auto;

  /// No description provided for @light.
  ///
  /// In en, this message translates to:
  /// **'Light'**
  String get light;

  /// No description provided for @dark.
  ///
  /// In en, this message translates to:
  /// **'Dark'**
  String get dark;

  /// No description provided for @appAppearance.
  ///
  /// In en, this message translates to:
  /// **'App appearance'**
  String get appAppearance;

  /// No description provided for @startLearning.
  ///
  /// In en, this message translates to:
  /// **'Start learning'**
  String get startLearning;

  /// No description provided for @practiceWithAI.
  ///
  /// In en, this message translates to:
  /// **'Practice with AI'**
  String get practiceWithAI;

  /// No description provided for @practiceWithAIDescription.
  ///
  /// In en, this message translates to:
  /// **'Improve your language through natural conversations.'**
  String get practiceWithAIDescription;

  /// No description provided for @myWords.
  ///
  /// In en, this message translates to:
  /// **'My Words'**
  String get myWords;

  /// No description provided for @myWordsDescription.
  ///
  /// In en, this message translates to:
  /// **'Review the words you saved while learning.'**
  String get myWordsDescription;

  /// No description provided for @yourLearning.
  ///
  /// In en, this message translates to:
  /// **'Your Learning'**
  String get yourLearning;

  /// No description provided for @streakDays.
  ///
  /// In en, this message translates to:
  /// **'Streak days'**
  String get streakDays;

  /// No description provided for @learnedWords.
  ///
  /// In en, this message translates to:
  /// **'Learned words'**
  String get learnedWords;

  /// No description provided for @conversations.
  ///
  /// In en, this message translates to:
  /// **'Conversations'**
  String get conversations;

  /// No description provided for @dailyTip.
  ///
  /// In en, this message translates to:
  /// **'Daily Tip'**
  String get dailyTip;

  /// No description provided for @dailyTipDescription.
  ///
  /// In en, this message translates to:
  /// **'Practice a little every day; consistency is the key to improving your language skills.'**
  String get dailyTipDescription;

  /// No description provided for @aiConversationComingSoon.
  ///
  /// In en, this message translates to:
  /// **'AI conversation will be available soon.'**
  String get aiConversationComingSoon;

  /// No description provided for @account.
  ///
  /// In en, this message translates to:
  /// **'My Account'**
  String get account;

  /// No description provided for @name.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get name;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @userId.
  ///
  /// In en, this message translates to:
  /// **'User ID'**
  String get userId;

  /// No description provided for @nativeLanguage.
  ///
  /// In en, this message translates to:
  /// **'Native language'**
  String get nativeLanguage;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get logout;

  /// No description provided for @learningLanguages.
  ///
  /// In en, this message translates to:
  /// **'Learning Languages'**
  String get learningLanguages;

  /// No description provided for @chooseLearningLanguage.
  ///
  /// In en, this message translates to:
  /// **'Choose one of your languages or add a new language.'**
  String get chooseLearningLanguage;

  /// No description provided for @noLearningLanguages.
  ///
  /// In en, this message translates to:
  /// **'No learning languages yet.'**
  String get noLearningLanguages;

  /// No description provided for @addNewLanguage.
  ///
  /// In en, this message translates to:
  /// **'Add a new language'**
  String get addNewLanguage;

  /// No description provided for @switchLearningLanguage.
  ///
  /// In en, this message translates to:
  /// **'Tap to switch learning language'**
  String get switchLearningLanguage;

  /// No description provided for @addOrChangeLearningLanguage.
  ///
  /// In en, this message translates to:
  /// **'Tap to add or change a language'**
  String get addOrChangeLearningLanguage;

  /// No description provided for @learningLanguageChanged.
  ///
  /// In en, this message translates to:
  /// **'Learning language changed to {language}'**
  String learningLanguageChanged(Object language);

  /// No description provided for @addLanguageTitle.
  ///
  /// In en, this message translates to:
  /// **'Add a new language'**
  String get addLanguageTitle;

  /// No description provided for @yourLearningLevel.
  ///
  /// In en, this message translates to:
  /// **'Your language level'**
  String get yourLearningLevel;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @add.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get add;

  /// No description provided for @noNewLanguagesAvailable.
  ///
  /// In en, this message translates to:
  /// **'No new languages are available to add.'**
  String get noNewLanguagesAvailable;

  /// No description provided for @levelA1.
  ///
  /// In en, this message translates to:
  /// **'A1 - Beginner'**
  String get levelA1;

  /// No description provided for @levelA2.
  ///
  /// In en, this message translates to:
  /// **'A2 - Elementary'**
  String get levelA2;

  /// No description provided for @levelB1.
  ///
  /// In en, this message translates to:
  /// **'B1 - Intermediate'**
  String get levelB1;

  /// No description provided for @levelB2.
  ///
  /// In en, this message translates to:
  /// **'B2 - Upper-intermediate'**
  String get levelB2;

  /// No description provided for @levelC1.
  ///
  /// In en, this message translates to:
  /// **'C1 - Advanced'**
  String get levelC1;

  /// No description provided for @levelC2.
  ///
  /// In en, this message translates to:
  /// **'C2 - Proficient'**
  String get levelC2;

  /// No description provided for @login.
  ///
  /// In en, this message translates to:
  /// **'Log in'**
  String get login;

  /// No description provided for @welcomeBackTitle.
  ///
  /// In en, this message translates to:
  /// **'Welcome back'**
  String get welcomeBackTitle;

  /// No description provided for @loginSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Log in and continue your learning journey.'**
  String get loginSubtitle;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @enterEmail.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid email address.'**
  String get enterEmail;

  /// No description provided for @enterPassword.
  ///
  /// In en, this message translates to:
  /// **'Enter your password.'**
  String get enterPassword;

  /// No description provided for @passwordVisibilityShow.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get passwordVisibilityShow;

  /// No description provided for @passwordVisibilityHide.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get passwordVisibilityHide;

  /// No description provided for @loginButton.
  ///
  /// In en, this message translates to:
  /// **'Log in'**
  String get loginButton;

  /// No description provided for @noAccount.
  ///
  /// In en, this message translates to:
  /// **'Don\'t have an account?'**
  String get noAccount;

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create an account'**
  String get createAccount;

  /// No description provided for @loginError.
  ///
  /// In en, this message translates to:
  /// **'Unable to log in. Check your email and password.'**
  String get loginError;

  /// No description provided for @continueWithGoogle.
  ///
  /// In en, this message translates to:
  /// **'Continue with Google'**
  String get continueWithGoogle;

  /// No description provided for @or.
  ///
  /// In en, this message translates to:
  /// **'or'**
  String get or;

  /// No description provided for @createYourAccount.
  ///
  /// In en, this message translates to:
  /// **'Create your account'**
  String get createYourAccount;

  /// No description provided for @createAccountSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Choose your languages and start a learning experience designed for you.'**
  String get createAccountSubtitle;

  /// No description provided for @usernameMinLength.
  ///
  /// In en, this message translates to:
  /// **'Enter a name with at least two characters.'**
  String get usernameMinLength;

  /// No description provided for @passwordMinLength.
  ///
  /// In en, this message translates to:
  /// **'Password must contain at least 8 characters.'**
  String get passwordMinLength;

  /// No description provided for @passwordHelper.
  ///
  /// In en, this message translates to:
  /// **'At least 8 characters'**
  String get passwordHelper;

  /// No description provided for @differentLanguages.
  ///
  /// In en, this message translates to:
  /// **'Choose two different languages to get started.'**
  String get differentLanguages;

  /// No description provided for @nativeLanguageLabel.
  ///
  /// In en, this message translates to:
  /// **'Your native language'**
  String get nativeLanguageLabel;

  /// No description provided for @languageYouWantToLearn.
  ///
  /// In en, this message translates to:
  /// **'The language you want to learn'**
  String get languageYouWantToLearn;

  /// No description provided for @createAccountButton.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get createAccountButton;

  /// No description provided for @accountCreated.
  ///
  /// In en, this message translates to:
  /// **'Your account has been created. You can log in now.'**
  String get accountCreated;

  /// No description provided for @registrationError.
  ///
  /// In en, this message translates to:
  /// **'Unable to create the account. The email may already be in use.'**
  String get registrationError;

  /// No description provided for @myVocabulary.
  ///
  /// In en, this message translates to:
  /// **'Your Vocabulary'**
  String get myVocabulary;

  /// No description provided for @savedWordsCount.
  ///
  /// In en, this message translates to:
  /// **'{count} saved words'**
  String savedWordsCount(Object count);

  /// No description provided for @learning.
  ///
  /// In en, this message translates to:
  /// **'Currently learning...'**
  String get learning;

  /// No description provided for @learned.
  ///
  /// In en, this message translates to:
  /// **'Learned'**
  String get learned;

  /// No description provided for @all.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get all;

  /// No description provided for @completeWord.
  ///
  /// In en, this message translates to:
  /// **'Mark as completed?'**
  String get completeWord;

  /// No description provided for @returnToLearning.
  ///
  /// In en, this message translates to:
  /// **'Return it to currently learning...?'**
  String get returnToLearning;

  /// No description provided for @masteredWord.
  ///
  /// In en, this message translates to:
  /// **'Have you mastered the word \"{word}\"?'**
  String masteredWord(Object word);

  /// No description provided for @returnWordToLearning.
  ///
  /// In en, this message translates to:
  /// **'The word \"{word}\" will return to your currently learning list...'**
  String returnWordToLearning(Object word);

  /// No description provided for @markCompleted.
  ///
  /// In en, this message translates to:
  /// **'Mark as completed'**
  String get markCompleted;

  /// No description provided for @returnToLearningButton.
  ///
  /// In en, this message translates to:
  /// **'Return to learning'**
  String get returnToLearningButton;

  /// No description provided for @wordMovedToLearned.
  ///
  /// In en, this message translates to:
  /// **'The word was moved to Learned.'**
  String get wordMovedToLearned;

  /// No description provided for @wordMovedToLearning.
  ///
  /// In en, this message translates to:
  /// **'The word was moved to Currently Learning.'**
  String get wordMovedToLearning;

  /// No description provided for @deleteWordTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete word?'**
  String get deleteWordTitle;

  /// No description provided for @deleteWordConfirmation.
  ///
  /// In en, this message translates to:
  /// **'Do you want to delete the word \"{word}\"? This action cannot be undone.'**
  String deleteWordConfirmation(Object word);

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

  /// No description provided for @wordDeleted.
  ///
  /// In en, this message translates to:
  /// **'The word was deleted.'**
  String get wordDeleted;

  /// No description provided for @noLearnedWords.
  ///
  /// In en, this message translates to:
  /// **'No learned words yet'**
  String get noLearnedWords;

  /// No description provided for @noLearningWords.
  ///
  /// In en, this message translates to:
  /// **'No words currently being learned...'**
  String get noLearningWords;

  /// No description provided for @keepPracticing.
  ///
  /// In en, this message translates to:
  /// **'Keep practicing, and the words you learn will appear here.'**
  String get keepPracticing;

  /// No description provided for @wordsAddedDuringLearning.
  ///
  /// In en, this message translates to:
  /// **'The words you add while learning will appear here.'**
  String get wordsAddedDuringLearning;

  /// No description provided for @noSavedWords.
  ///
  /// In en, this message translates to:
  /// **'No saved words yet'**
  String get noSavedWords;

  /// No description provided for @saveWordsDuringConversation.
  ///
  /// In en, this message translates to:
  /// **'When you discover a new word during an AI conversation, add it to your vocabulary.'**
  String get saveWordsDuringConversation;

  /// No description provided for @learnNaturally.
  ///
  /// In en, this message translates to:
  /// **'Learn naturally through conversation'**
  String get learnNaturally;

  /// No description provided for @errorOccurred.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get errorOccurred;

  /// No description provided for @tryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get tryAgain;

  /// No description provided for @automatic.
  ///
  /// In en, this message translates to:
  /// **'Automatic'**
  String get automatic;

  /// No description provided for @systemDefault.
  ///
  /// In en, this message translates to:
  /// **'System default'**
  String get systemDefault;

  /// No description provided for @userInformationReadError.
  ///
  /// In en, this message translates to:
  /// **'Unable to read user information.'**
  String get userInformationReadError;

  /// No description provided for @onboardingSaveError.
  ///
  /// In en, this message translates to:
  /// **'Unable to save your settings. Please try again.'**
  String get onboardingSaveError;

  /// No description provided for @placementTestTitle.
  ///
  /// In en, this message translates to:
  /// **'Placement Test'**
  String get placementTestTitle;

  /// No description provided for @placementTestDescription.
  ///
  /// In en, this message translates to:
  /// **'Test your language level so we can determine the right level for you.'**
  String get placementTestDescription;

  /// No description provided for @later.
  ///
  /// In en, this message translates to:
  /// **'Later'**
  String get later;

  /// No description provided for @startTest.
  ///
  /// In en, this message translates to:
  /// **'Start test'**
  String get startTest;

  /// No description provided for @chooseAppLanguage.
  ///
  /// In en, this message translates to:
  /// **'Choose app language'**
  String get chooseAppLanguage;

  /// No description provided for @nativeLanguageQuestion.
  ///
  /// In en, this message translates to:
  /// **'What is your native language?'**
  String get nativeLanguageQuestion;

  /// No description provided for @learningLanguageQuestion.
  ///
  /// In en, this message translates to:
  /// **'What language do you want to learn?'**
  String get learningLanguageQuestion;

  /// No description provided for @chooseAppLanguageDescription.
  ///
  /// In en, this message translates to:
  /// **'Choose the language you want to use for the app interface.'**
  String get chooseAppLanguageDescription;

  /// No description provided for @nativeLanguageDescription.
  ///
  /// In en, this message translates to:
  /// **'Choose your native language.'**
  String get nativeLanguageDescription;

  /// No description provided for @learningLanguageDescription.
  ///
  /// In en, this message translates to:
  /// **'Choose the language you want to learn.'**
  String get learningLanguageDescription;

  /// No description provided for @nativeLanguageCannotBeLearningLanguage.
  ///
  /// In en, this message translates to:
  /// **'Your native language and learning language cannot be the same.'**
  String get nativeLanguageCannotBeLearningLanguage;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @setupYourAccount.
  ///
  /// In en, this message translates to:
  /// **'Set up your account'**
  String get setupYourAccount;

  /// No description provided for @saveAndContinue.
  ///
  /// In en, this message translates to:
  /// **'Save and continue'**
  String get saveAndContinue;

  /// No description provided for @continueButton.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueButton;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>[
    'ar',
    'de',
    'en',
    'es',
    'fr',
    'id',
    'it',
    'ja',
    'ko',
    'nl',
    'pl',
    'pt',
    'ru',
    'th',
    'tr',
    'uk',
    'vi',
    'zh',
  ].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
    case 'es':
      return AppLocalizationsEs();
    case 'fr':
      return AppLocalizationsFr();
    case 'id':
      return AppLocalizationsId();
    case 'it':
      return AppLocalizationsIt();
    case 'ja':
      return AppLocalizationsJa();
    case 'ko':
      return AppLocalizationsKo();
    case 'nl':
      return AppLocalizationsNl();
    case 'pl':
      return AppLocalizationsPl();
    case 'pt':
      return AppLocalizationsPt();
    case 'ru':
      return AppLocalizationsRu();
    case 'th':
      return AppLocalizationsTh();
    case 'tr':
      return AppLocalizationsTr();
    case 'uk':
      return AppLocalizationsUk();
    case 'vi':
      return AppLocalizationsVi();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
