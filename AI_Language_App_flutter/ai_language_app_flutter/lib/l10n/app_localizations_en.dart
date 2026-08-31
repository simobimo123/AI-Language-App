// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'AI Language Tutor';

  @override
  String get welcome => 'Welcome';

  @override
  String get welcomeBack => 'Welcome back 👋';

  @override
  String get continueLearning => 'Are you ready to continue learning?';

  @override
  String get home => 'Home';

  @override
  String get profile => 'Profile';

  @override
  String get words => 'My Words';

  @override
  String get settings => 'Settings';

  @override
  String get language => 'Language';

  @override
  String get appLanguage => 'App Language';

  @override
  String get learningLanguage => 'Learning Language';

  @override
  String get arabic => 'Arabic';

  @override
  String get english => 'English';

  @override
  String get french => 'French';

  @override
  String get spanish => 'Spanish';

  @override
  String get chinese => 'Chinese';

  @override
  String get japanese => 'Japanese';

  @override
  String get korean => 'Korean';

  @override
  String get lightMode => 'Light Mode';

  @override
  String get darkMode => 'Dark Mode';

  @override
  String get systemMode => 'System Default';

  @override
  String get auto => 'Automatic';

  @override
  String get light => 'Light';

  @override
  String get dark => 'Dark';

  @override
  String get appAppearance => 'App Appearance';

  @override
  String get startLearning => 'Start Learning';

  @override
  String get practiceWithAI => 'Practice with AI';

  @override
  String get practiceWithAIDescription =>
      'Improve your language through natural conversations.';

  @override
  String get myWords => 'My Words';

  @override
  String get myWordsDescription => 'Review the words you saved while learning.';

  @override
  String get yourLearning => 'Your Learning';

  @override
  String get streakDays => 'Streak Days';

  @override
  String get learnedWords => 'Learned Words';

  @override
  String get conversations => 'Conversations';

  @override
  String get dailyTip => 'Daily Tip';

  @override
  String get dailyTipDescription =>
      'Practice a little every day; consistency is the key to improving your language skills.';

  @override
  String get aiConversationComingSoon =>
      'AI conversation will be available soon.';

  @override
  String get account => 'Account';

  @override
  String get name => 'Name';

  @override
  String get email => 'Email';

  @override
  String get userId => 'User ID';

  @override
  String get nativeLanguage => 'Native Language';

  @override
  String get logout => 'Log Out';

  @override
  String get learningLanguages => 'Learning Languages';

  @override
  String get chooseLearningLanguage =>
      'Choose one of your languages or add a new one.';

  @override
  String get noLearningLanguages => 'No learning languages yet.';

  @override
  String get addNewLanguage => 'Add New Language';

  @override
  String get switchLearningLanguage => 'Tap to switch learning language';

  @override
  String get addOrChangeLearningLanguage => 'Tap to add or change a language';

  @override
  String learningLanguageChanged(Object language) {
    return 'Learning language changed to $language';
  }

  @override
  String get addLanguageTitle => 'Add New Language';

  @override
  String get yourLearningLevel => 'Your Language Level';

  @override
  String get cancel => 'Cancel';

  @override
  String get add => 'Add';

  @override
  String get noNewLanguagesAvailable =>
      'No new languages are available to add.';

  @override
  String get levelA1 => 'A1 - Beginner';

  @override
  String get levelA2 => 'A2 - Elementary';

  @override
  String get levelB1 => 'B1 - Intermediate';

  @override
  String get levelB2 => 'B2 - Upper Intermediate';

  @override
  String get levelC1 => 'C1 - Advanced';

  @override
  String get levelC2 => 'C2 - Proficient';

  @override
  String get login => 'Login';

  @override
  String get welcomeBackTitle => 'Welcome Back';

  @override
  String get loginSubtitle => 'Log in and continue your learning journey.';

  @override
  String get password => 'Password';

  @override
  String get enterEmail => 'Enter a valid email address.';

  @override
  String get enterPassword => 'Enter your password.';

  @override
  String get passwordVisibilityShow => 'Show password';

  @override
  String get passwordVisibilityHide => 'Hide password';

  @override
  String get loginButton => 'Login';

  @override
  String get noAccount => 'Don\'t have an account?';

  @override
  String get createAccount => 'Create an account';

  @override
  String get loginError => 'Unable to log in. Check your email and password.';

  @override
  String get continueWithGoogle => 'Continue with Google';

  @override
  String get or => 'OR';

  @override
  String get createYourAccount => 'Create Your Account';

  @override
  String get createAccountSubtitle =>
      'Choose your languages and start a learning experience designed for you.';

  @override
  String get usernameMinLength => 'Enter a name with at least two characters.';

  @override
  String get passwordMinLength =>
      'Password must contain at least 8 characters.';

  @override
  String get passwordHelper => 'At least 8 characters';

  @override
  String get differentLanguages =>
      'Choose two different languages to get started.';

  @override
  String get nativeLanguageLabel => 'Your Native Language';

  @override
  String get languageYouWantToLearn => 'Language You Want to Learn';

  @override
  String get createAccountButton => 'Create Account';

  @override
  String get accountCreated => 'Account created. You can log in now.';

  @override
  String get registrationError =>
      'Unable to create the account. The email may already be in use.';

  @override
  String get myVocabulary => 'Your Vocabulary';

  @override
  String savedWordsCount(Object count) {
    return '$count saved words';
  }

  @override
  String get learning => 'Learning...';

  @override
  String get learned => 'Learned';

  @override
  String get all => 'All';

  @override
  String get completeWord => 'Mark as learned?';

  @override
  String get returnToLearning => 'Return to learning...?';

  @override
  String masteredWord(Object word) {
    return 'Have you mastered the word \"$word\"?';
  }

  @override
  String returnWordToLearning(Object word) {
    return 'The word \"$word\" will return to your learning list...';
  }

  @override
  String get markCompleted => 'Mark as Learned';

  @override
  String get returnToLearningButton => 'Return to Learning';

  @override
  String get wordMovedToLearned => 'The word was moved to learned.';

  @override
  String get wordMovedToLearning => 'The word was moved back to learning...';

  @override
  String get deleteWordTitle => 'Delete Word?';

  @override
  String deleteWordConfirmation(Object word) {
    return 'Do you want to delete the word \"$word\"? This action cannot be undone.';
  }

  @override
  String get delete => 'Delete';

  @override
  String get wordDeleted => 'The word was deleted.';

  @override
  String get noLearnedWords => 'No learned words yet';

  @override
  String get noLearningWords => 'No words are currently being learned...';

  @override
  String get keepPracticing =>
      'Keep practicing, and the words you learn will appear here.';

  @override
  String get wordsAddedDuringLearning =>
      'Words you add while learning will appear here.';

  @override
  String get noSavedWords => 'No saved words yet';

  @override
  String get saveWordsDuringConversation =>
      'When you discover a new word during an AI conversation, add it to your vocabulary.';

  @override
  String get learnNaturally => 'Learn naturally through conversation';

  @override
  String get errorOccurred => 'Something went wrong';

  @override
  String get tryAgain => 'Try Again';

  @override
  String get automatic => 'Automatic';

  @override
  String get systemDefault => 'System Default';

  @override
  String get userInformationReadError => 'Could not read user information.';

  @override
  String get onboardingSaveError =>
      'Could not save your settings. Please try again.';

  @override
  String get placementTestTitle => 'Placement Test';

  @override
  String get placementTestDescription =>
      'Test your language skills to find the right level for you.';

  @override
  String get later => 'Later';

  @override
  String get startTest => 'Start Test';

  @override
  String get chooseAppLanguage => 'Choose App Language';

  @override
  String get nativeLanguageQuestion => 'What is your native language?';

  @override
  String get learningLanguageQuestion => 'What language do you want to learn?';

  @override
  String get chooseAppLanguageDescription =>
      'Choose the language you want to use for the app interface.';

  @override
  String get nativeLanguageDescription => 'Choose your native language.';

  @override
  String get learningLanguageDescription =>
      'Choose the language you want to learn.';

  @override
  String get nativeLanguageCannotBeLearningLanguage =>
      'Your native language and learning language cannot be the same.';

  @override
  String get back => 'Back';

  @override
  String get setupYourAccount => 'Set Up Your Account';

  @override
  String get saveAndContinue => 'Save and Continue';

  @override
  String get continueButton => 'Continue';
}
