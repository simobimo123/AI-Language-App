// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Ukrainian (`uk`).
class AppLocalizationsUk extends AppLocalizations {
  AppLocalizationsUk([String locale = 'uk']) : super(locale);

  @override
  String get appName => 'Мовний репетитор зі штучним інтелектом';

  @override
  String get welcome => 'Ласкаво просимо';

  @override
  String get welcomeBack => 'З поверненням 👋';

  @override
  String get continueLearning => 'Готові продовжити навчання?';

  @override
  String get home => 'Головна';

  @override
  String get profile => 'Профіль';

  @override
  String get words => 'Мої слова';

  @override
  String get settings => 'Налаштування';

  @override
  String get language => 'Мова';

  @override
  String get appLanguage => 'Мова застосунку';

  @override
  String get learningLanguage => 'Мова навчання';

  @override
  String get arabic => 'Арабська';

  @override
  String get english => 'Англійська';

  @override
  String get french => 'Французька';

  @override
  String get spanish => 'Іспанська';

  @override
  String get chinese => 'Китайська';

  @override
  String get japanese => 'Японська';

  @override
  String get korean => 'Корейська';

  @override
  String get lightMode => 'Світла тема';

  @override
  String get darkMode => 'Темна тема';

  @override
  String get systemMode => 'Налаштування системи';

  @override
  String get auto => 'Автоматично';

  @override
  String get light => 'Світла';

  @override
  String get dark => 'Темна';

  @override
  String get appAppearance => 'Вигляд застосунку';

  @override
  String get startLearning => 'Почати навчання';

  @override
  String get practiceWithAI => 'Практикуватися з ШІ';

  @override
  String get practiceWithAIDescription =>
      'Покращуйте свої мовні навички за допомогою природних розмов.';

  @override
  String get myWords => 'Мої слова';

  @override
  String get myWordsDescription =>
      'Повторюйте слова, які ви зберегли під час навчання.';

  @override
  String get yourLearning => 'Ваше навчання';

  @override
  String get streakDays => 'Днів поспіль';

  @override
  String get learnedWords => 'Вивчені слова';

  @override
  String get conversations => 'Розмови';

  @override
  String get dailyTip => 'Порада дня';

  @override
  String get dailyTipDescription =>
      'Практикуйтеся потроху щодня; регулярність — ключ до покращення мовних навичок.';

  @override
  String get aiConversationComingSoon =>
      'Розмови з ШІ будуть доступні незабаром.';

  @override
  String get account => 'Мій обліковий запис';

  @override
  String get name => 'Ім\'я';

  @override
  String get email => 'Електронна пошта';

  @override
  String get userId => 'ID користувача';

  @override
  String get nativeLanguage => 'Рідна мова';

  @override
  String get logout => 'Вийти';

  @override
  String get learningLanguages => 'Мови навчання';

  @override
  String get chooseLearningLanguage =>
      'Виберіть одну зі своїх мов або додайте нову.';

  @override
  String get noLearningLanguages => 'Мов для навчання ще немає.';

  @override
  String get addNewLanguage => 'Додати нову мову';

  @override
  String get switchLearningLanguage => 'Натисніть, щоб змінити мову навчання';

  @override
  String get addOrChangeLearningLanguage =>
      'Натисніть, щоб додати або змінити мову';

  @override
  String learningLanguageChanged(Object language) {
    return 'Мову навчання змінено на $language';
  }

  @override
  String get addLanguageTitle => 'Додати нову мову';

  @override
  String get yourLearningLevel => 'Ваш рівень мови';

  @override
  String get cancel => 'Скасувати';

  @override
  String get add => 'Додати';

  @override
  String get noNewLanguagesAvailable =>
      'Немає нових мов, доступних для додавання.';

  @override
  String get levelA1 => 'A1 - Початківець';

  @override
  String get levelA2 => 'A2 - Елементарний';

  @override
  String get levelB1 => 'B1 - Середній';

  @override
  String get levelB2 => 'B2 - Вище середнього';

  @override
  String get levelC1 => 'C1 - Просунутий';

  @override
  String get levelC2 => 'C2 - Вільне володіння';

  @override
  String get login => 'Увійти';

  @override
  String get welcomeBackTitle => 'З поверненням';

  @override
  String get loginSubtitle => 'Увійдіть і продовжуйте свій шлях навчання.';

  @override
  String get password => 'Пароль';

  @override
  String get enterEmail => 'Введіть дійсну адресу електронної пошти.';

  @override
  String get enterPassword => 'Введіть пароль.';

  @override
  String get passwordVisibilityShow => 'Показати пароль';

  @override
  String get passwordVisibilityHide => 'Сховати пароль';

  @override
  String get loginButton => 'Увійти';

  @override
  String get noAccount => 'Немає облікового запису?';

  @override
  String get createAccount => 'Створити обліковий запис';

  @override
  String get loginError =>
      'Не вдалося увійти. Перевірте електронну пошту та пароль.';

  @override
  String get continueWithGoogle => 'Продовжити з Google';

  @override
  String get or => 'або';

  @override
  String get createYourAccount => 'Створіть свій обліковий запис';

  @override
  String get createAccountSubtitle =>
      'Виберіть свої мови та почніть навчання, створене спеціально для вас.';

  @override
  String get usernameMinLength => 'Введіть ім\'я щонайменше з двох символів.';

  @override
  String get passwordMinLength => 'Пароль має містити щонайменше 8 символів.';

  @override
  String get passwordHelper => 'Щонайменше 8 символів';

  @override
  String get differentLanguages => 'Виберіть дві різні мови, щоб почати.';

  @override
  String get nativeLanguageLabel => 'Ваша рідна мова';

  @override
  String get languageYouWantToLearn => 'Мова, яку ви хочете вивчати';

  @override
  String get createAccountButton => 'Створити обліковий запис';

  @override
  String get accountCreated =>
      'Обліковий запис створено. Тепер ви можете увійти.';

  @override
  String get registrationError =>
      'Не вдалося створити обліковий запис. Можливо, ця електронна пошта вже використовується.';

  @override
  String get myVocabulary => 'Ваш словниковий запас';

  @override
  String savedWordsCount(Object count) {
    return '$count збережених слів';
  }

  @override
  String get learning => 'Вивчається...';

  @override
  String get learned => 'Вивчено';

  @override
  String get all => 'Усі';

  @override
  String get completeWord => 'Позначити як вивчене?';

  @override
  String get returnToLearning => 'Повернути до списку слів для вивчення?';

  @override
  String masteredWord(Object word) {
    return 'Ви вже опанували слово \"$word\"?';
  }

  @override
  String returnWordToLearning(Object word) {
    return 'Слово \"$word\" буде повернуто до списку слів для вивчення...';
  }

  @override
  String get markCompleted => 'Позначити як вивчене';

  @override
  String get returnToLearningButton => 'Повернути до навчання';

  @override
  String get wordMovedToLearned => 'Слово переміщено до вивчених.';

  @override
  String get wordMovedToLearning => 'Слово повернуто до списку для вивчення.';

  @override
  String get deleteWordTitle => 'Видалити слово?';

  @override
  String deleteWordConfirmation(Object word) {
    return 'Ви хочете видалити слово \"$word\"? Цю дію неможливо скасувати.';
  }

  @override
  String get delete => 'Видалити';

  @override
  String get wordDeleted => 'Слово видалено.';

  @override
  String get noLearnedWords => 'Ще немає вивчених слів';

  @override
  String get noLearningWords => 'Наразі немає слів для вивчення...';

  @override
  String get keepPracticing =>
      'Продовжуйте практикуватися, і вивчені слова з\'являться тут.';

  @override
  String get wordsAddedDuringLearning =>
      'Слова, які ви додаєте під час навчання, з\'являтимуться тут.';

  @override
  String get noSavedWords => 'Ще немає збережених слів';

  @override
  String get saveWordsDuringConversation =>
      'Коли ви зустрінете нове слово під час розмови з ШІ, додайте його до свого словника.';

  @override
  String get learnNaturally => 'Вивчайте мову природно через розмови';

  @override
  String get errorOccurred => 'Щось пішло не так';

  @override
  String get tryAgain => 'Спробувати ще раз';

  @override
  String get automatic => 'Автоматично';

  @override
  String get systemDefault => 'Системний стандарт';

  @override
  String get userInformationReadError =>
      'Не вдалося прочитати інформацію про користувача.';

  @override
  String get onboardingSaveError =>
      'Не вдалося зберегти налаштування. Спробуйте ще раз.';

  @override
  String get placementTestTitle => 'Тест на визначення рівня';

  @override
  String get placementTestDescription =>
      'Перевірте свій рівень мови, щоб визначити відповідний для вас рівень.';

  @override
  String get later => 'Пізніше';

  @override
  String get startTest => 'Почати тест';

  @override
  String get chooseAppLanguage => 'Виберіть мову застосунку';

  @override
  String get nativeLanguageQuestion => 'Яка ваша рідна мова?';

  @override
  String get learningLanguageQuestion => 'Яку мову ви хочете вивчати?';

  @override
  String get chooseAppLanguageDescription =>
      'Виберіть мову, яку хочете використовувати для інтерфейсу застосунку.';

  @override
  String get nativeLanguageDescription => 'Виберіть свою рідну мову.';

  @override
  String get learningLanguageDescription =>
      'Виберіть мову, яку хочете вивчати.';

  @override
  String get nativeLanguageCannotBeLearningLanguage =>
      'Рідна мова та мова навчання не можуть бути однаковими.';

  @override
  String get back => 'Назад';

  @override
  String get setupYourAccount => 'Налаштуйте свій обліковий запис';

  @override
  String get saveAndContinue => 'Зберегти та продовжити';

  @override
  String get continueButton => 'Продовжити';
}
