import 'package:flutter/material.dart';

/// UI strings used by the AI lesson conversation screens.
///
/// These strings follow the app interface language. They are deliberately
/// separate from the learning language and native language used by the AI.
String lessonChatUiText(String languageCode, String key) {
  final language = languageCode.toLowerCase().split('-').first;
  const values = <String, Map<String, String>>{
    'ar': {
      'aiTutor': 'المدرّس الذكي', 'stageTeaching': 'المرحلة 2 · التعليم', 'stagePractice': 'المرحلة 3 · الممارسة',
      'translate': 'ترجمة', 'hideTranslation': 'إخفاء الترجمة', 'replySuggestion': 'اقتراح للرد',
      'showSuggestion': 'إظهار الاقتراح', 'hideSuggestion': 'إخفاء الاقتراح', 'suggestReply': 'اقتراح رد مناسب',
      'writeReply': 'اكتب إجابتك...', 'send': 'إرسال', 'complete': 'مكتملة', 'starting': 'جاري بدء المحادثة...',
      'continueStage3': 'فتح المرحلة 3', 'connectionError': 'تعذر الاتصال بالمدرّس الذكي.',
      'sendError': 'تعذر إرسال الرسالة. حاول مرة أخرى.', 'translationError': 'تعذر ترجمة الرسالة.',
      'suggestionError': 'تعذر إنشاء اقتراح للرد.', 'practiceDescription': 'استخدم أهداف الدرس الآن في محادثة طبيعية مع المدرّس الذكي.',
    },
    'de': {
      'aiTutor': 'KI-Tutor', 'stageTeaching': 'Phase 2 · Lernen', 'stagePractice': 'Phase 3 · Üben',
      'translate': 'Übersetzen', 'hideTranslation': 'Übersetzung ausblenden', 'replySuggestion': 'Antwortvorschlag',
      'showSuggestion': 'Vorschlag anzeigen', 'hideSuggestion': 'Vorschlag ausblenden', 'suggestReply': 'Passende Antwort vorschlagen',
      'writeReply': 'Antwort schreiben...', 'send': 'Senden', 'complete': 'Abgeschlossen', 'starting': 'Gespräch wird gestartet...',
      'continueStage3': 'Mit Phase 3 fortfahren', 'connectionError': 'Der KI-Tutor konnte nicht erreicht werden.',
      'sendError': 'Nachricht konnte nicht gesendet werden. Bitte erneut versuchen.', 'translationError': 'Nachricht konnte nicht übersetzt werden.',
      'suggestionError': 'Antwortvorschlag konnte nicht erstellt werden.', 'practiceDescription': 'Verwende die Lernziele jetzt in einem natürlichen Gespräch mit deinem KI-Tutor.',
    },
    'en': {
      'aiTutor': 'AI Tutor', 'stageTeaching': 'Stage 2 · Teaching', 'stagePractice': 'Stage 3 · Practice',
      'translate': 'Translate', 'hideTranslation': 'Hide translation', 'replySuggestion': 'Reply suggestion',
      'showSuggestion': 'Show suggestion', 'hideSuggestion': 'Hide suggestion', 'suggestReply': 'Suggest a suitable reply',
      'writeReply': 'Write your answer...', 'send': 'Send', 'complete': 'Complete', 'starting': 'Starting the conversation...',
      'continueStage3': 'Continue to stage 3', 'connectionError': 'Could not reach the AI tutor.',
      'sendError': 'Could not send the message. Please try again.', 'translationError': 'Could not translate the message.',
      'suggestionError': 'Could not generate a reply suggestion.', 'practiceDescription': 'Now use the lesson goals in a natural conversation with your AI tutor.',
    },
    'es': {
      'aiTutor': 'Tutor de IA', 'stageTeaching': 'Etapa 2 · Enseñanza', 'stagePractice': 'Etapa 3 · Práctica',
      'translate': 'Traducir', 'hideTranslation': 'Ocultar traducción', 'replySuggestion': 'Sugerencia de respuesta',
      'showSuggestion': 'Mostrar sugerencia', 'hideSuggestion': 'Ocultar sugerencia', 'suggestReply': 'Sugerir una respuesta adecuada',
      'writeReply': 'Escribe tu respuesta...', 'send': 'Enviar', 'complete': 'Completada', 'starting': 'Iniciando la conversación...',
      'continueStage3': 'Continuar a la etapa 3', 'connectionError': 'No se pudo conectar con el tutor de IA.',
      'sendError': 'No se pudo enviar el mensaje. Inténtalo de nuevo.', 'translationError': 'No se pudo traducir el mensaje.',
      'suggestionError': 'No se pudo generar una sugerencia de respuesta.', 'practiceDescription': 'Usa ahora los objetivos de la lección en una conversación natural con tu tutor de IA.',
    },
    'fr': {
      'aiTutor': 'Tuteur IA', 'stageTeaching': 'Étape 2 · Enseignement', 'stagePractice': 'Étape 3 · Pratique',
      'translate': 'Traduire', 'hideTranslation': 'Masquer la traduction', 'replySuggestion': 'Suggestion de réponse',
      'showSuggestion': 'Afficher la suggestion', 'hideSuggestion': 'Masquer la suggestion', 'suggestReply': 'Suggérer une réponse adaptée',
      'writeReply': 'Écrivez votre réponse...', 'send': 'Envoyer', 'complete': 'Terminée', 'starting': 'Démarrage de la conversation...',
      'continueStage3': 'Passer à l’étape 3', 'connectionError': 'Impossible de joindre le tuteur IA.',
      'sendError': 'Impossible d’envoyer le message. Réessayez.', 'translationError': 'Impossible de traduire le message.',
      'suggestionError': 'Impossible de générer une suggestion de réponse.', 'practiceDescription': 'Utilisez maintenant les objectifs de la leçon dans une conversation naturelle avec votre tuteur IA.',
    },
    'id': {
      'aiTutor': 'Tutor AI', 'stageTeaching': 'Tahap 2 · Pengajaran', 'stagePractice': 'Tahap 3 · Latihan',
      'translate': 'Terjemahkan', 'hideTranslation': 'Sembunyikan terjemahan', 'replySuggestion': 'Saran balasan',
      'showSuggestion': 'Tampilkan saran', 'hideSuggestion': 'Sembunyikan saran', 'suggestReply': 'Sarankan balasan yang sesuai',
      'writeReply': 'Tulis jawaban Anda...', 'send': 'Kirim', 'complete': 'Selesai', 'starting': 'Memulai percakapan...',
      'continueStage3': 'Lanjut ke tahap 3', 'connectionError': 'Tidak dapat menghubungi tutor AI.',
      'sendError': 'Pesan tidak dapat dikirim. Coba lagi.', 'translationError': 'Pesan tidak dapat diterjemahkan.',
      'suggestionError': 'Saran balasan tidak dapat dibuat.', 'practiceDescription': 'Gunakan tujuan pelajaran sekarang dalam percakapan alami dengan tutor AI Anda.',
    },
    'it': {
      'aiTutor': 'Tutor IA', 'stageTeaching': 'Fase 2 · Insegnamento', 'stagePractice': 'Fase 3 · Pratica',
      'translate': 'Traduci', 'hideTranslation': 'Nascondi traduzione', 'replySuggestion': 'Suggerimento di risposta',
      'showSuggestion': 'Mostra suggerimento', 'hideSuggestion': 'Nascondi suggerimento', 'suggestReply': 'Suggerisci una risposta adatta',
      'writeReply': 'Scrivi la tua risposta...', 'send': 'Invia', 'complete': 'Completata', 'starting': 'Avvio della conversazione...',
      'continueStage3': 'Continua alla fase 3', 'connectionError': 'Impossibile raggiungere il tutor IA.',
      'sendError': 'Impossibile inviare il messaggio. Riprova.', 'translationError': 'Impossibile tradurre il messaggio.',
      'suggestionError': 'Impossibile generare un suggerimento di risposta.', 'practiceDescription': 'Usa ora gli obiettivi della lezione in una conversazione naturale con il tuo tutor IA.',
    },
    'pt': {
      'aiTutor': 'Tutor de IA', 'stageTeaching': 'Etapa 2 · Ensino', 'stagePractice': 'Etapa 3 · Prática',
      'translate': 'Traduzir', 'hideTranslation': 'Ocultar tradução', 'replySuggestion': 'Sugestão de resposta',
      'showSuggestion': 'Mostrar sugestão', 'hideSuggestion': 'Ocultar sugestão', 'suggestReply': 'Sugerir uma resposta adequada',
      'writeReply': 'Escreva sua resposta...', 'send': 'Enviar', 'complete': 'Concluída', 'starting': 'Iniciando a conversa...',
      'continueStage3': 'Continuar para a etapa 3', 'connectionError': 'Não foi possível conectar ao tutor de IA.',
      'sendError': 'Não foi possível enviar a mensagem. Tente novamente.', 'translationError': 'Não foi possível traduzir a mensagem.',
      'suggestionError': 'Não foi possível gerar uma sugestão de resposta.', 'practiceDescription': 'Use agora os objetivos da lição em uma conversa natural com seu tutor de IA.',
    },
    'nl': {
      'aiTutor': 'AI-tutor', 'stageTeaching': 'Fase 2 · Lesgeven', 'stagePractice': 'Fase 3 · Oefenen',
      'translate': 'Vertalen', 'hideTranslation': 'Vertaling verbergen', 'replySuggestion': 'Antwoordsuggestie',
      'showSuggestion': 'Suggestie tonen', 'hideSuggestion': 'Suggestie verbergen', 'suggestReply': 'Een passend antwoord voorstellen',
      'writeReply': 'Schrijf je antwoord...', 'send': 'Verzenden', 'complete': 'Voltooid', 'starting': 'Gesprek wordt gestart...',
      'continueStage3': 'Doorgaan naar fase 3', 'connectionError': 'De AI-tutor kan niet worden bereikt.',
      'sendError': 'Bericht kon niet worden verzonden. Probeer opnieuw.', 'translationError': 'Bericht kon niet worden vertaald.',
      'suggestionError': 'Er kon geen antwoordsuggestie worden gemaakt.', 'practiceDescription': 'Gebruik de lesdoelen nu in een natuurlijk gesprek met je AI-tutor.',
    },
    'pl': {
      'aiTutor': 'Tutor AI', 'stageTeaching': 'Etap 2 · Nauka', 'stagePractice': 'Etap 3 · Praktyka',
      'translate': 'Tłumacz', 'hideTranslation': 'Ukryj tłumaczenie', 'replySuggestion': 'Sugestia odpowiedzi',
      'showSuggestion': 'Pokaż sugestię', 'hideSuggestion': 'Ukryj sugestię', 'suggestReply': 'Zaproponuj odpowiednią odpowiedź',
      'writeReply': 'Wpisz swoją odpowiedź...', 'send': 'Wyślij', 'complete': 'Ukończono', 'starting': 'Rozpoczynanie rozmowy...',
      'continueStage3': 'Przejdź do etapu 3', 'connectionError': 'Nie można połączyć się z tutorem AI.',
      'sendError': 'Nie można wysłać wiadomości. Spróbuj ponownie.', 'translationError': 'Nie można przetłumaczyć wiadomości.',
      'suggestionError': 'Nie można utworzyć sugestii odpowiedzi.', 'practiceDescription': 'Wykorzystaj teraz cele lekcji w naturalnej rozmowie z tutorem AI.',
    },
    'ru': {
      'aiTutor': 'ИИ-репетитор', 'stageTeaching': 'Этап 2 · Обучение', 'stagePractice': 'Этап 3 · Практика',
      'translate': 'Перевести', 'hideTranslation': 'Скрыть перевод', 'replySuggestion': 'Предложение ответа',
      'showSuggestion': 'Показать предложение', 'hideSuggestion': 'Скрыть предложение', 'suggestReply': 'Предложить подходящий ответ',
      'writeReply': 'Введите ответ...', 'send': 'Отправить', 'complete': 'Завершено', 'starting': 'Начинаем разговор...',
      'continueStage3': 'Перейти к этапу 3', 'connectionError': 'Не удалось связаться с ИИ-репетитором.',
      'sendError': 'Не удалось отправить сообщение. Попробуйте ещё раз.', 'translationError': 'Не удалось перевести сообщение.',
      'suggestionError': 'Не удалось создать предложение ответа.', 'practiceDescription': 'Теперь используйте цели урока в естественном разговоре с ИИ-репетитором.',
    },
    'tr': {
      'aiTutor': 'Yapay Zekâ Eğitmeni', 'stageTeaching': 'Aşama 2 · Öğretim', 'stagePractice': 'Aşama 3 · Pratik',
      'translate': 'Çevir', 'hideTranslation': 'Çeviriyi gizle', 'replySuggestion': 'Yanıt önerisi',
      'showSuggestion': 'Öneriyi göster', 'hideSuggestion': 'Öneriyi gizle', 'suggestReply': 'Uygun bir yanıt öner',
      'writeReply': 'Yanıtınızı yazın...', 'send': 'Gönder', 'complete': 'Tamamlandı', 'starting': 'Konuşma başlatılıyor...',
      'continueStage3': '3. aşamaya geç', 'connectionError': 'Yapay zekâ eğitmenine ulaşılamadı.',
      'sendError': 'Mesaj gönderilemedi. Lütfen tekrar deneyin.', 'translationError': 'Mesaj çevrilemedi.',
      'suggestionError': 'Yanıt önerisi oluşturulamadı.', 'practiceDescription': 'Şimdi ders hedeflerini yapay zekâ eğitmeninizle doğal bir konuşmada kullanın.',
    },
    'uk': {
      'aiTutor': 'ШІ-репетитор', 'stageTeaching': 'Етап 2 · Навчання', 'stagePractice': 'Етап 3 · Практика',
      'translate': 'Перекласти', 'hideTranslation': 'Сховати переклад', 'replySuggestion': 'Пропозиція відповіді',
      'showSuggestion': 'Показати пропозицію', 'hideSuggestion': 'Сховати пропозицію', 'suggestReply': 'Запропонувати відповідну відповідь',
      'writeReply': 'Введіть відповідь...', 'send': 'Надіслати', 'complete': 'Завершено', 'starting': 'Розпочинаємо розмову...',
      'continueStage3': 'Перейти до етапу 3', 'connectionError': 'Не вдалося зв’язатися з ШІ-репетитором.',
      'sendError': 'Не вдалося надіслати повідомлення. Спробуйте ще раз.', 'translationError': 'Не вдалося перекласти повідомлення.',
      'suggestionError': 'Не вдалося створити пропозицію відповіді.', 'practiceDescription': 'Тепер використовуйте цілі уроку в природній розмові з ШІ-репетитором.',
    },
    'vi': {
      'aiTutor': 'Gia sư AI', 'stageTeaching': 'Giai đoạn 2 · Học', 'stagePractice': 'Giai đoạn 3 · Luyện tập',
      'translate': 'Dịch', 'hideTranslation': 'Ẩn bản dịch', 'replySuggestion': 'Gợi ý trả lời',
      'showSuggestion': 'Hiện gợi ý', 'hideSuggestion': 'Ẩn gợi ý', 'suggestReply': 'Gợi ý một câu trả lời phù hợp',
      'writeReply': 'Viết câu trả lời...', 'send': 'Gửi', 'complete': 'Hoàn thành', 'starting': 'Đang bắt đầu cuộc trò chuyện...',
      'continueStage3': 'Tiếp tục đến giai đoạn 3', 'connectionError': 'Không thể kết nối với gia sư AI.',
      'sendError': 'Không thể gửi tin nhắn. Vui lòng thử lại.', 'translationError': 'Không thể dịch tin nhắn.',
      'suggestionError': 'Không thể tạo gợi ý trả lời.', 'practiceDescription': 'Bây giờ hãy dùng mục tiêu bài học trong cuộc trò chuyện tự nhiên với gia sư AI.',
    },
    'th': {
      'aiTutor': 'ครูสอน AI', 'stageTeaching': 'ขั้นที่ 2 · การสอน', 'stagePractice': 'ขั้นที่ 3 · ฝึกฝน',
      'translate': 'แปล', 'hideTranslation': 'ซ่อนคำแปล', 'replySuggestion': 'คำแนะนำการตอบ',
      'showSuggestion': 'แสดงคำแนะนำ', 'hideSuggestion': 'ซ่อนคำแนะนำ', 'suggestReply': 'แนะนำคำตอบที่เหมาะสม',
      'writeReply': 'เขียนคำตอบ...', 'send': 'ส่ง', 'complete': 'เสร็จสิ้น', 'starting': 'กำลังเริ่มการสนทนา...',
      'continueStage3': 'ไปยังขั้นที่ 3', 'connectionError': 'ไม่สามารถเชื่อมต่อกับครู AI ได้',
      'sendError': 'ส่งข้อความไม่ได้ โปรดลองอีกครั้ง', 'translationError': 'แปลข้อความไม่ได้',
      'suggestionError': 'สร้างคำแนะนำการตอบไม่ได้', 'practiceDescription': 'ใช้เป้าหมายของบทเรียนในการสนทนาธรรมชาติกับครู AI ของคุณ',
    },
    'ja': {
      'aiTutor': 'AIチューター', 'stageTeaching': 'ステージ2 · 学習', 'stagePractice': 'ステージ3 · 練習',
      'translate': '翻訳', 'hideTranslation': '翻訳を隠す', 'replySuggestion': '返信候補',
      'showSuggestion': '候補を表示', 'hideSuggestion': '候補を隠す', 'suggestReply': '適切な返信を提案',
      'writeReply': '回答を入力...', 'send': '送信', 'complete': '完了', 'starting': '会話を開始しています...',
      'continueStage3': 'ステージ3へ進む', 'connectionError': 'AIチューターに接続できませんでした。',
      'sendError': 'メッセージを送信できませんでした。もう一度お試しください。', 'translationError': 'メッセージを翻訳できませんでした。',
      'suggestionError': '返信候補を作成できませんでした。', 'practiceDescription': 'レッスンの目標をAIチューターとの自然な会話で使ってみましょう。',
    },
    'ko': {
      'aiTutor': 'AI 튜터', 'stageTeaching': '2단계 · 학습', 'stagePractice': '3단계 · 연습',
      'translate': '번역', 'hideTranslation': '번역 숨기기', 'replySuggestion': '답변 제안',
      'showSuggestion': '제안 보기', 'hideSuggestion': '제안 숨기기', 'suggestReply': '적절한 답변 제안',
      'writeReply': '답변을 입력하세요...', 'send': '보내기', 'complete': '완료', 'starting': '대화를 시작하는 중...',
      'continueStage3': '3단계로 계속', 'connectionError': 'AI 튜터에 연결할 수 없습니다.',
      'sendError': '메시지를 보낼 수 없습니다. 다시 시도해 주세요.', 'translationError': '메시지를 번역할 수 없습니다.',
      'suggestionError': '답변 제안을 만들 수 없습니다.', 'practiceDescription': '이제 AI 튜터와 자연스럽게 대화하며 수업 목표를 사용해 보세요.',
    },
    'zh': {
      'aiTutor': 'AI 导师', 'stageTeaching': '第2阶段 · 教学', 'stagePractice': '第3阶段 · 练习',
      'translate': '翻译', 'hideTranslation': '隐藏翻译', 'replySuggestion': '回复建议',
      'showSuggestion': '显示建议', 'hideSuggestion': '隐藏建议', 'suggestReply': '建议合适的回复',
      'writeReply': '输入你的回答...', 'send': '发送', 'complete': '已完成', 'starting': '正在开始对话...',
      'continueStage3': '继续第3阶段', 'connectionError': '无法连接到 AI 导师。',
      'sendError': '无法发送消息，请重试。', 'translationError': '无法翻译消息。',
      'suggestionError': '无法生成回复建议。', 'practiceDescription': '现在与 AI 导师进行自然对话，使用本课的学习目标。',
    },
  };

  // Never use a forced null check here. A missing key or an unexpected
  // interface language must not crash the whole lesson screen.
  return values[language]?[key] ?? values['en']?[key] ?? key;
}

String _languageCode(String code) => code.toLowerCase().split('-').first;

TextDirection directionForLanguage(String? languageCode) {
  final code = _languageCode(languageCode ?? '');
  const rtlLanguages = {'ar', 'fa', 'he', 'ur', 'ps'};
  return rtlLanguages.contains(code) ? TextDirection.rtl : TextDirection.ltr;
}

/// Detects the direction of the actual text. This is used for learner input
/// and translated text because those strings can legitimately differ from
/// the app language and the learning language.
TextDirection directionForText(
  String text, {
  TextDirection fallback = TextDirection.ltr,
}) {
  final value = text.trim();
  if (value.isEmpty) return fallback;

  final rtl = RegExp(r'[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]');
  final ltr = RegExp(r'[A-Za-z\u00C0-\u024F\u0370-\u052F\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF]');

  final rtlMatch = rtl.firstMatch(value);
  final ltrMatch = ltr.firstMatch(value);
  if (rtlMatch == null && ltrMatch == null) return fallback;
  if (rtlMatch == null) return TextDirection.ltr;
  if (ltrMatch == null) return TextDirection.rtl;
  return rtlMatch.start < ltrMatch.start
      ? TextDirection.rtl
      : TextDirection.ltr;
}
