// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appName => 'AI语言导师';

  @override
  String get welcome => '欢迎';

  @override
  String get welcomeBack => '欢迎回来 👋';

  @override
  String get continueLearning => '准备好继续学习了吗？';

  @override
  String get home => '首页';

  @override
  String get profile => '个人资料';

  @override
  String get words => '我的单词';

  @override
  String get settings => '设置';

  @override
  String get language => '语言';

  @override
  String get appLanguage => '应用语言';

  @override
  String get learningLanguage => '学习语言';

  @override
  String get arabic => '阿拉伯语';

  @override
  String get english => '英语';

  @override
  String get french => '法语';

  @override
  String get spanish => '西班牙语';

  @override
  String get chinese => '中文';

  @override
  String get japanese => '日语';

  @override
  String get korean => '韩语';

  @override
  String get lightMode => '浅色模式';

  @override
  String get darkMode => '深色模式';

  @override
  String get systemMode => '系统设置';

  @override
  String get auto => '自动';

  @override
  String get light => '浅色';

  @override
  String get dark => '深色';

  @override
  String get appAppearance => '应用外观';

  @override
  String get startLearning => '开始学习';

  @override
  String get practiceWithAI => '与 AI 练习';

  @override
  String get practiceWithAIDescription => '通过自然对话提高你的语言能力。';

  @override
  String get myWords => '我的单词';

  @override
  String get myWordsDescription => '复习你在学习过程中保存的单词。';

  @override
  String get yourLearning => '你的学习';

  @override
  String get streakDays => '连续学习天数';

  @override
  String get learnedWords => '已学单词';

  @override
  String get conversations => '对话';

  @override
  String get dailyTip => '每日提示';

  @override
  String get dailyTipDescription => '每天练习一点；坚持是提高语言能力的关键。';

  @override
  String get aiConversationComingSoon => 'AI 对话功能即将推出。';

  @override
  String get account => '我的账户';

  @override
  String get name => '姓名';

  @override
  String get email => '电子邮箱';

  @override
  String get userId => '用户 ID';

  @override
  String get nativeLanguage => '母语';

  @override
  String get logout => '退出登录';

  @override
  String get learningLanguages => '学习语言';

  @override
  String get chooseLearningLanguage => '选择你的语言之一，或添加一种新语言。';

  @override
  String get noLearningLanguages => '还没有学习语言。';

  @override
  String get addNewLanguage => '添加新语言';

  @override
  String get switchLearningLanguage => '点击切换学习语言';

  @override
  String get addOrChangeLearningLanguage => '点击添加或更改语言';

  @override
  String learningLanguageChanged(Object language) {
    return '学习语言已更改为 $language';
  }

  @override
  String get addLanguageTitle => '添加新语言';

  @override
  String get yourLearningLevel => '你的语言水平';

  @override
  String get cancel => '取消';

  @override
  String get add => '添加';

  @override
  String get noNewLanguagesAvailable => '没有可添加的新语言。';

  @override
  String get levelA1 => 'A1 - 初学者';

  @override
  String get levelA2 => 'A2 - 基础';

  @override
  String get levelB1 => 'B1 - 中级';

  @override
  String get levelB2 => 'B2 - 中高级';

  @override
  String get levelC1 => 'C1 - 高级';

  @override
  String get levelC2 => 'C2 - 熟练';

  @override
  String get login => '登录';

  @override
  String get welcomeBackTitle => '欢迎回来';

  @override
  String get loginSubtitle => '登录并继续你的学习之旅。';

  @override
  String get password => '密码';

  @override
  String get enterEmail => '请输入有效的电子邮箱地址。';

  @override
  String get enterPassword => '请输入密码。';

  @override
  String get passwordVisibilityShow => '显示密码';

  @override
  String get passwordVisibilityHide => '隐藏密码';

  @override
  String get loginButton => '登录';

  @override
  String get noAccount => '还没有账户？';

  @override
  String get createAccount => '创建账户';

  @override
  String get loginError => '无法登录。请检查你的邮箱和密码。';

  @override
  String get continueWithGoogle => '使用 Google 继续';

  @override
  String get or => '或';

  @override
  String get createYourAccount => '创建你的账户';

  @override
  String get createAccountSubtitle => '选择你的语言，开始专为你设计的学习体验。';

  @override
  String get usernameMinLength => '请输入至少包含两个字符的姓名。';

  @override
  String get passwordMinLength => '密码必须至少包含 8 个字符。';

  @override
  String get passwordHelper => '至少 8 个字符';

  @override
  String get differentLanguages => '请选择两种不同的语言开始学习。';

  @override
  String get nativeLanguageLabel => '你的母语';

  @override
  String get languageYouWantToLearn => '你想学习的语言';

  @override
  String get createAccountButton => '创建账户';

  @override
  String get accountCreated => '账户已创建。你现在可以登录了。';

  @override
  String get registrationError => '无法创建账户。该邮箱可能已被使用。';

  @override
  String get myVocabulary => '你的词汇';

  @override
  String savedWordsCount(Object count) {
    return '已保存 $count 个单词';
  }

  @override
  String get learning => '正在学习...';

  @override
  String get learned => '已学会';

  @override
  String get all => '全部';

  @override
  String get completeWord => '标记为已完成？';

  @override
  String get returnToLearning => '将其放回正在学习...？';

  @override
  String masteredWord(Object word) {
    return '你已经掌握单词“$word”了吗？';
  }

  @override
  String returnWordToLearning(Object word) {
    return '单词“$word”将返回正在学习列表...';
  }

  @override
  String get markCompleted => '标记为已完成';

  @override
  String get returnToLearningButton => '重新开始学习';

  @override
  String get wordMovedToLearned => '单词已移至“已学会”。';

  @override
  String get wordMovedToLearning => '单词已移至“正在学习”。';

  @override
  String get deleteWordTitle => '删除单词？';

  @override
  String deleteWordConfirmation(Object word) {
    return '确定要删除单词“$word”吗？此操作无法撤销。';
  }

  @override
  String get delete => '删除';

  @override
  String get wordDeleted => '单词已删除。';

  @override
  String get noLearnedWords => '还没有已学会的单词';

  @override
  String get noLearningWords => '没有正在学习的单词...';

  @override
  String get keepPracticing => '继续练习，你学习的单词会显示在这里。';

  @override
  String get wordsAddedDuringLearning => '你在学习过程中添加的单词会显示在这里。';

  @override
  String get noSavedWords => '还没有保存的单词';

  @override
  String get saveWordsDuringConversation => '在 AI 对话中发现新单词时，将其添加到你的词汇中。';

  @override
  String get learnNaturally => '通过对话自然地学习';

  @override
  String get errorOccurred => '发生了错误';

  @override
  String get tryAgain => '重试';

  @override
  String get automatic => '自动';

  @override
  String get systemDefault => '系统默认';

  @override
  String get userInformationReadError => '无法读取用户信息。';

  @override
  String get onboardingSaveError => '无法保存你的设置。请重试。';

  @override
  String get placementTestTitle => '水平测试';

  @override
  String get placementTestDescription => '测试你的语言水平，以便我们确定适合你的等级。';

  @override
  String get later => '稍后';

  @override
  String get startTest => '开始测试';

  @override
  String get chooseAppLanguage => '选择应用语言';

  @override
  String get nativeLanguageQuestion => '你的母语是什么？';

  @override
  String get learningLanguageQuestion => '你想学习什么语言？';

  @override
  String get chooseAppLanguageDescription => '选择你想用于应用界面的语言。';

  @override
  String get nativeLanguageDescription => '选择你的母语。';

  @override
  String get learningLanguageDescription => '选择你想学习的语言。';

  @override
  String get nativeLanguageCannotBeLearningLanguage => '你的母语和学习语言不能相同。';

  @override
  String get back => '返回';

  @override
  String get setupYourAccount => '设置你的账户';

  @override
  String get saveAndContinue => '保存并继续';

  @override
  String get continueButton => '继续';
}
