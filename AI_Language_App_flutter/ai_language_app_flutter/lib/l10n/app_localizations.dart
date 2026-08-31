import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';
import 'app_localizations_es.dart';
import 'app_localizations_fr.dart';
import 'app_localizations_ja.dart';
import 'app_localizations_ko.dart';
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
    Locale('en'),
    Locale('es'),
    Locale('fr'),
    Locale('ja'),
    Locale('ko'),
    Locale('zh'),
  ];

  /// No description provided for @appName.
  ///
  /// In ar, this message translates to:
  /// **'مدرس اللغات بالذكاء الاصطناعي'**
  String get appName;

  /// No description provided for @welcome.
  ///
  /// In ar, this message translates to:
  /// **'مرحبًا'**
  String get welcome;

  /// No description provided for @welcomeBack.
  ///
  /// In ar, this message translates to:
  /// **'أهلًا بعودتك 👋'**
  String get welcomeBack;

  /// No description provided for @continueLearning.
  ///
  /// In ar, this message translates to:
  /// **'هل أنت مستعد لمتابعة التعلّم؟'**
  String get continueLearning;

  /// No description provided for @home.
  ///
  /// In ar, this message translates to:
  /// **'الرئيسية'**
  String get home;

  /// No description provided for @profile.
  ///
  /// In ar, this message translates to:
  /// **'الملف الشخصي'**
  String get profile;

  /// No description provided for @words.
  ///
  /// In ar, this message translates to:
  /// **'كلماتي'**
  String get words;

  /// No description provided for @settings.
  ///
  /// In ar, this message translates to:
  /// **'الإعدادات'**
  String get settings;

  /// No description provided for @language.
  ///
  /// In ar, this message translates to:
  /// **'اللغة'**
  String get language;

  /// No description provided for @appLanguage.
  ///
  /// In ar, this message translates to:
  /// **'لغة التطبيق'**
  String get appLanguage;

  /// No description provided for @learningLanguage.
  ///
  /// In ar, this message translates to:
  /// **'لغة التعلّم'**
  String get learningLanguage;

  /// No description provided for @arabic.
  ///
  /// In ar, this message translates to:
  /// **'العربية'**
  String get arabic;

  /// No description provided for @english.
  ///
  /// In ar, this message translates to:
  /// **'الإنجليزية'**
  String get english;

  /// No description provided for @french.
  ///
  /// In ar, this message translates to:
  /// **'الفرنسية'**
  String get french;

  /// No description provided for @spanish.
  ///
  /// In ar, this message translates to:
  /// **'الإسبانية'**
  String get spanish;

  /// No description provided for @chinese.
  ///
  /// In ar, this message translates to:
  /// **'الصينية'**
  String get chinese;

  /// No description provided for @japanese.
  ///
  /// In ar, this message translates to:
  /// **'اليابانية'**
  String get japanese;

  /// No description provided for @korean.
  ///
  /// In ar, this message translates to:
  /// **'الكورية'**
  String get korean;

  /// No description provided for @lightMode.
  ///
  /// In ar, this message translates to:
  /// **'الوضع الفاتح'**
  String get lightMode;

  /// No description provided for @darkMode.
  ///
  /// In ar, this message translates to:
  /// **'الوضع الداكن'**
  String get darkMode;

  /// No description provided for @systemMode.
  ///
  /// In ar, this message translates to:
  /// **'إعدادات النظام'**
  String get systemMode;

  /// No description provided for @auto.
  ///
  /// In ar, this message translates to:
  /// **'تلقائي'**
  String get auto;

  /// No description provided for @light.
  ///
  /// In ar, this message translates to:
  /// **'فاتح'**
  String get light;

  /// No description provided for @dark.
  ///
  /// In ar, this message translates to:
  /// **'داكن'**
  String get dark;

  /// No description provided for @appAppearance.
  ///
  /// In ar, this message translates to:
  /// **'مظهر التطبيق'**
  String get appAppearance;

  /// No description provided for @startLearning.
  ///
  /// In ar, this message translates to:
  /// **'ابدأ التعلّم'**
  String get startLearning;

  /// No description provided for @practiceWithAI.
  ///
  /// In ar, this message translates to:
  /// **'تدرّب مع الذكاء الاصطناعي'**
  String get practiceWithAI;

  /// No description provided for @practiceWithAIDescription.
  ///
  /// In ar, this message translates to:
  /// **'طوّر لغتك من خلال محادثات طبيعية.'**
  String get practiceWithAIDescription;

  /// No description provided for @myWords.
  ///
  /// In ar, this message translates to:
  /// **'كلماتي'**
  String get myWords;

  /// No description provided for @myWordsDescription.
  ///
  /// In ar, this message translates to:
  /// **'راجع الكلمات التي حفظتها أثناء التعلّم.'**
  String get myWordsDescription;

  /// No description provided for @yourLearning.
  ///
  /// In ar, this message translates to:
  /// **'تعلّمك'**
  String get yourLearning;

  /// No description provided for @streakDays.
  ///
  /// In ar, this message translates to:
  /// **'أيام متتالية'**
  String get streakDays;

  /// No description provided for @learnedWords.
  ///
  /// In ar, this message translates to:
  /// **'كلمات متعلّمة'**
  String get learnedWords;

  /// No description provided for @conversations.
  ///
  /// In ar, this message translates to:
  /// **'محادثات'**
  String get conversations;

  /// No description provided for @dailyTip.
  ///
  /// In ar, this message translates to:
  /// **'نصيحة يومية'**
  String get dailyTip;

  /// No description provided for @dailyTipDescription.
  ///
  /// In ar, this message translates to:
  /// **'تدرّب قليلًا كل يوم؛ الاستمرارية هي مفتاح تطوير مهاراتك اللغوية.'**
  String get dailyTipDescription;

  /// No description provided for @aiConversationComingSoon.
  ///
  /// In ar, this message translates to:
  /// **'ستتوفر محادثة الذكاء الاصطناعي قريبًا.'**
  String get aiConversationComingSoon;

  /// No description provided for @account.
  ///
  /// In ar, this message translates to:
  /// **'حسابي'**
  String get account;

  /// No description provided for @name.
  ///
  /// In ar, this message translates to:
  /// **'الاسم'**
  String get name;

  /// No description provided for @email.
  ///
  /// In ar, this message translates to:
  /// **'البريد الإلكتروني'**
  String get email;

  /// No description provided for @userId.
  ///
  /// In ar, this message translates to:
  /// **'رقم المستخدم'**
  String get userId;

  /// No description provided for @nativeLanguage.
  ///
  /// In ar, this message translates to:
  /// **'لغتك الأم'**
  String get nativeLanguage;

  /// No description provided for @logout.
  ///
  /// In ar, this message translates to:
  /// **'تسجيل الخروج'**
  String get logout;

  /// No description provided for @learningLanguages.
  ///
  /// In ar, this message translates to:
  /// **'لغات التعلّم'**
  String get learningLanguages;

  /// No description provided for @chooseLearningLanguage.
  ///
  /// In ar, this message translates to:
  /// **'اختر إحدى لغاتك أو أضف لغة جديدة.'**
  String get chooseLearningLanguage;

  /// No description provided for @noLearningLanguages.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد لغات تعلّم بعد.'**
  String get noLearningLanguages;

  /// No description provided for @addNewLanguage.
  ///
  /// In ar, this message translates to:
  /// **'إضافة لغة جديدة'**
  String get addNewLanguage;

  /// No description provided for @switchLearningLanguage.
  ///
  /// In ar, this message translates to:
  /// **'اضغط لتبديل لغة التعلّم'**
  String get switchLearningLanguage;

  /// No description provided for @addOrChangeLearningLanguage.
  ///
  /// In ar, this message translates to:
  /// **'اضغط لإضافة أو تغيير لغة'**
  String get addOrChangeLearningLanguage;

  /// No description provided for @learningLanguageChanged.
  ///
  /// In ar, this message translates to:
  /// **'تم تغيير لغة التعلّم إلى {language}'**
  String learningLanguageChanged(Object language);

  /// No description provided for @addLanguageTitle.
  ///
  /// In ar, this message translates to:
  /// **'إضافة لغة جديدة'**
  String get addLanguageTitle;

  /// No description provided for @yourLearningLevel.
  ///
  /// In ar, this message translates to:
  /// **'مستواك في اللغة'**
  String get yourLearningLevel;

  /// No description provided for @cancel.
  ///
  /// In ar, this message translates to:
  /// **'إلغاء'**
  String get cancel;

  /// No description provided for @add.
  ///
  /// In ar, this message translates to:
  /// **'إضافة'**
  String get add;

  /// No description provided for @noNewLanguagesAvailable.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد لغات جديدة متاحة للإضافة.'**
  String get noNewLanguagesAvailable;

  /// No description provided for @levelA1.
  ///
  /// In ar, this message translates to:
  /// **'A1 - مبتدئ'**
  String get levelA1;

  /// No description provided for @levelA2.
  ///
  /// In ar, this message translates to:
  /// **'A2 - أساسي'**
  String get levelA2;

  /// No description provided for @levelB1.
  ///
  /// In ar, this message translates to:
  /// **'B1 - متوسط'**
  String get levelB1;

  /// No description provided for @levelB2.
  ///
  /// In ar, this message translates to:
  /// **'B2 - فوق المتوسط'**
  String get levelB2;

  /// No description provided for @levelC1.
  ///
  /// In ar, this message translates to:
  /// **'C1 - متقدم'**
  String get levelC1;

  /// No description provided for @levelC2.
  ///
  /// In ar, this message translates to:
  /// **'C2 - متقن'**
  String get levelC2;

  /// No description provided for @login.
  ///
  /// In ar, this message translates to:
  /// **'تسجيل الدخول'**
  String get login;

  /// No description provided for @welcomeBackTitle.
  ///
  /// In ar, this message translates to:
  /// **'مرحبًا بعودتك'**
  String get welcomeBackTitle;

  /// No description provided for @loginSubtitle.
  ///
  /// In ar, this message translates to:
  /// **'سجّل دخولك وتابع رحلة تعلّمك.'**
  String get loginSubtitle;

  /// No description provided for @password.
  ///
  /// In ar, this message translates to:
  /// **'كلمة المرور'**
  String get password;

  /// No description provided for @enterEmail.
  ///
  /// In ar, this message translates to:
  /// **'أدخل بريدًا إلكترونيًا صحيحًا.'**
  String get enterEmail;

  /// No description provided for @enterPassword.
  ///
  /// In ar, this message translates to:
  /// **'أدخل كلمة المرور.'**
  String get enterPassword;

  /// No description provided for @passwordVisibilityShow.
  ///
  /// In ar, this message translates to:
  /// **'إظهار كلمة المرور'**
  String get passwordVisibilityShow;

  /// No description provided for @passwordVisibilityHide.
  ///
  /// In ar, this message translates to:
  /// **'إخفاء كلمة المرور'**
  String get passwordVisibilityHide;

  /// No description provided for @loginButton.
  ///
  /// In ar, this message translates to:
  /// **'دخول'**
  String get loginButton;

  /// No description provided for @noAccount.
  ///
  /// In ar, this message translates to:
  /// **'ليس لديك حساب؟'**
  String get noAccount;

  /// No description provided for @createAccount.
  ///
  /// In ar, this message translates to:
  /// **'أنشئ حسابًا'**
  String get createAccount;

  /// No description provided for @loginError.
  ///
  /// In ar, this message translates to:
  /// **'تعذّر تسجيل الدخول. تحقّق من البريد وكلمة المرور.'**
  String get loginError;

  /// No description provided for @continueWithGoogle.
  ///
  /// In ar, this message translates to:
  /// **'المتابعة باستخدام Google'**
  String get continueWithGoogle;

  /// No description provided for @or.
  ///
  /// In ar, this message translates to:
  /// **'أو'**
  String get or;

  /// No description provided for @createYourAccount.
  ///
  /// In ar, this message translates to:
  /// **'أنشئ حسابك'**
  String get createYourAccount;

  /// No description provided for @createAccountSubtitle.
  ///
  /// In ar, this message translates to:
  /// **'اختر لغاتك وابدأ تجربة تعلّم مصممة لك.'**
  String get createAccountSubtitle;

  /// No description provided for @usernameMinLength.
  ///
  /// In ar, this message translates to:
  /// **'أدخل اسمًا من حرفين على الأقل.'**
  String get usernameMinLength;

  /// No description provided for @passwordMinLength.
  ///
  /// In ar, this message translates to:
  /// **'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل.'**
  String get passwordMinLength;

  /// No description provided for @passwordHelper.
  ///
  /// In ar, this message translates to:
  /// **'8 أحرف على الأقل'**
  String get passwordHelper;

  /// No description provided for @differentLanguages.
  ///
  /// In ar, this message translates to:
  /// **'اختر لغتين مختلفتين للبدء.'**
  String get differentLanguages;

  /// No description provided for @nativeLanguageLabel.
  ///
  /// In ar, this message translates to:
  /// **'لغتك الأم'**
  String get nativeLanguageLabel;

  /// No description provided for @languageYouWantToLearn.
  ///
  /// In ar, this message translates to:
  /// **'اللغة التي تريد تعلّمها'**
  String get languageYouWantToLearn;

  /// No description provided for @createAccountButton.
  ///
  /// In ar, this message translates to:
  /// **'إنشاء الحساب'**
  String get createAccountButton;

  /// No description provided for @accountCreated.
  ///
  /// In ar, this message translates to:
  /// **'تم إنشاء الحساب. يمكنك تسجيل الدخول الآن.'**
  String get accountCreated;

  /// No description provided for @registrationError.
  ///
  /// In ar, this message translates to:
  /// **'تعذّر إنشاء الحساب. قد يكون البريد مستخدمًا بالفعل.'**
  String get registrationError;

  /// No description provided for @myVocabulary.
  ///
  /// In ar, this message translates to:
  /// **'مفرداتك'**
  String get myVocabulary;

  /// No description provided for @savedWordsCount.
  ///
  /// In ar, this message translates to:
  /// **'{count} كلمة محفوظة'**
  String savedWordsCount(Object count);

  /// No description provided for @learning.
  ///
  /// In ar, this message translates to:
  /// **'جاري التعلّم...'**
  String get learning;

  /// No description provided for @learned.
  ///
  /// In ar, this message translates to:
  /// **'تم التعلّم'**
  String get learned;

  /// No description provided for @all.
  ///
  /// In ar, this message translates to:
  /// **'الكل'**
  String get all;

  /// No description provided for @completeWord.
  ///
  /// In ar, this message translates to:
  /// **'تحديد كمكتملة؟'**
  String get completeWord;

  /// No description provided for @returnToLearning.
  ///
  /// In ar, this message translates to:
  /// **'إعادتها إلى جاري التعلّم...؟'**
  String get returnToLearning;

  /// No description provided for @masteredWord.
  ///
  /// In ar, this message translates to:
  /// **'هل أتقنت كلمة \"{word}\"؟'**
  String masteredWord(Object word);

  /// No description provided for @returnWordToLearning.
  ///
  /// In ar, this message translates to:
  /// **'ستعود كلمة \"{word}\" إلى قائمة جاري التعلّم...'**
  String returnWordToLearning(Object word);

  /// No description provided for @markCompleted.
  ///
  /// In ar, this message translates to:
  /// **'تحديد كمكتملة'**
  String get markCompleted;

  /// No description provided for @returnToLearningButton.
  ///
  /// In ar, this message translates to:
  /// **'إعادة إلى التعلّم'**
  String get returnToLearningButton;

  /// No description provided for @wordMovedToLearned.
  ///
  /// In ar, this message translates to:
  /// **'تم نقل الكلمة إلى تم التعلّم.'**
  String get wordMovedToLearned;

  /// No description provided for @wordMovedToLearning.
  ///
  /// In ar, this message translates to:
  /// **'تم نقل الكلمة إلى جاري التعلّم...'**
  String get wordMovedToLearning;

  /// No description provided for @deleteWordTitle.
  ///
  /// In ar, this message translates to:
  /// **'حذف الكلمة؟'**
  String get deleteWordTitle;

  /// No description provided for @deleteWordConfirmation.
  ///
  /// In ar, this message translates to:
  /// **'هل تريد حذف كلمة \"{word}\"؟ لا يمكن التراجع عن هذا الإجراء.'**
  String deleteWordConfirmation(Object word);

  /// No description provided for @delete.
  ///
  /// In ar, this message translates to:
  /// **'حذف'**
  String get delete;

  /// No description provided for @wordDeleted.
  ///
  /// In ar, this message translates to:
  /// **'تم حذف الكلمة.'**
  String get wordDeleted;

  /// No description provided for @noLearnedWords.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد كلمات تم التعلّم بعد'**
  String get noLearnedWords;

  /// No description provided for @noLearningWords.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد كلمات في جاري التعلّم...'**
  String get noLearningWords;

  /// No description provided for @keepPracticing.
  ///
  /// In ar, this message translates to:
  /// **'واصل التدريب، وستظهر الكلمات التي تتعلمها هنا.'**
  String get keepPracticing;

  /// No description provided for @wordsAddedDuringLearning.
  ///
  /// In ar, this message translates to:
  /// **'ستظهر هنا الكلمات التي تضيفها أثناء التعلّم.'**
  String get wordsAddedDuringLearning;

  /// No description provided for @noSavedWords.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد كلمات محفوظة بعد'**
  String get noSavedWords;

  /// No description provided for @saveWordsDuringConversation.
  ///
  /// In ar, this message translates to:
  /// **'عند اكتشاف كلمة جديدة أثناء محادثة الذكاء الاصطناعي، أضفها إلى مفرداتك.'**
  String get saveWordsDuringConversation;

  /// No description provided for @learnNaturally.
  ///
  /// In ar, this message translates to:
  /// **'تعلّم بصورة طبيعية من خلال المحادثة'**
  String get learnNaturally;

  /// No description provided for @errorOccurred.
  ///
  /// In ar, this message translates to:
  /// **'حدث خطأ ما'**
  String get errorOccurred;

  /// No description provided for @tryAgain.
  ///
  /// In ar, this message translates to:
  /// **'حاول مجددًا'**
  String get tryAgain;

  /// No description provided for @automatic.
  ///
  /// In ar, this message translates to:
  /// **'تلقائي'**
  String get automatic;

  /// No description provided for @systemDefault.
  ///
  /// In ar, this message translates to:
  /// **'افتراضي النظام'**
  String get systemDefault;

  /// No description provided for @userInformationReadError.
  ///
  /// In ar, this message translates to:
  /// **'تعذر قراءة معلومات المستخدم.'**
  String get userInformationReadError;

  /// No description provided for @onboardingSaveError.
  ///
  /// In ar, this message translates to:
  /// **'تعذر حفظ إعداداتك. حاول مرة أخرى.'**
  String get onboardingSaveError;

  /// No description provided for @placementTestTitle.
  ///
  /// In ar, this message translates to:
  /// **'اختبار تحديد المستوى'**
  String get placementTestTitle;

  /// No description provided for @placementTestDescription.
  ///
  /// In ar, this message translates to:
  /// **'اختبر مستواك في اللغة لنحدد المستوى المناسب لك.'**
  String get placementTestDescription;

  /// No description provided for @later.
  ///
  /// In ar, this message translates to:
  /// **'لاحقًا'**
  String get later;

  /// No description provided for @startTest.
  ///
  /// In ar, this message translates to:
  /// **'ابدأ الاختبار'**
  String get startTest;

  /// No description provided for @chooseAppLanguage.
  ///
  /// In ar, this message translates to:
  /// **'اختر لغة التطبيق'**
  String get chooseAppLanguage;

  /// No description provided for @nativeLanguageQuestion.
  ///
  /// In ar, this message translates to:
  /// **'ما لغتك الأم؟'**
  String get nativeLanguageQuestion;

  /// No description provided for @learningLanguageQuestion.
  ///
  /// In ar, this message translates to:
  /// **'ما اللغة التي تريد تعلمها؟'**
  String get learningLanguageQuestion;

  /// No description provided for @chooseAppLanguageDescription.
  ///
  /// In ar, this message translates to:
  /// **'اختر اللغة التي تريد استخدامها في واجهة التطبيق.'**
  String get chooseAppLanguageDescription;

  /// No description provided for @nativeLanguageDescription.
  ///
  /// In ar, this message translates to:
  /// **'اختر لغتك الأم.'**
  String get nativeLanguageDescription;

  /// No description provided for @learningLanguageDescription.
  ///
  /// In ar, this message translates to:
  /// **'اختر اللغة التي تريد تعلمها.'**
  String get learningLanguageDescription;

  /// No description provided for @nativeLanguageCannotBeLearningLanguage.
  ///
  /// In ar, this message translates to:
  /// **'لا يمكن أن تكون اللغة الأم ولغة التعلّم متطابقتين.'**
  String get nativeLanguageCannotBeLearningLanguage;

  /// No description provided for @back.
  ///
  /// In ar, this message translates to:
  /// **'رجوع'**
  String get back;

  /// No description provided for @setupYourAccount.
  ///
  /// In ar, this message translates to:
  /// **'إعداد حسابك'**
  String get setupYourAccount;

  /// No description provided for @saveAndContinue.
  ///
  /// In ar, this message translates to:
  /// **'حفظ ومتابعة'**
  String get saveAndContinue;

  /// No description provided for @continueButton.
  ///
  /// In ar, this message translates to:
  /// **'متابعة'**
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
    'en',
    'es',
    'fr',
    'ja',
    'ko',
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
    case 'en':
      return AppLocalizationsEn();
    case 'es':
      return AppLocalizationsEs();
    case 'fr':
      return AppLocalizationsFr();
    case 'ja':
      return AppLocalizationsJa();
    case 'ko':
      return AppLocalizationsKo();
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
