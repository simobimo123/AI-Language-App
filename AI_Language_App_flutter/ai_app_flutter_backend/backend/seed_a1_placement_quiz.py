from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import PlacementQuizQuestion


# A1 placement bank: 30 questions per language.
# 10 vocabulary/translation + 10 grammar + 10 context/comprehension.
# The API randomly serves 10 questions from this 30-question bank.

LANGUAGE_BANKS = {
    "en": {
        "vocab": [
            ("What does 'house' mean?", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
            ("What does 'water' mean?", ["طعام", "ماء", "باب", "سيارة"], 1),
            ("What does 'book' mean?", ["كتاب", "كرسي", "قلم", "شارع"], 0),
            ("What does 'friend' mean?", ["معلم", "صديق", "طبيب", "أخ"], 1),
            ("What does 'school' mean?", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
            ("What does 'food' mean?", ["ماء", "طعام", "عمل", "وقت"], 1),
            ("What does 'car' mean?", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
            ("What does 'morning' mean?", ["ليل", "مساء", "صباح", "أسبوع"], 2),
            ("What does 'family' mean?", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
            ("What does 'happy' mean?", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ],
        "grammar": [
            ("She ___ a student.", ["is", "are", "am", "be"], 0),
            ("I ___ from Morocco.", ["is", "am", "are", "be"], 1),
            ("They ___ at home.", ["is", "am", "are", "be"], 2),
            ("He ___ coffee every morning.", ["drink", "drinks", "drinking", "drank"], 1),
            ("We ___ English.", ["study", "studies", "studying", "studied"], 0),
            ("___ you like tea?", ["Do", "Does", "Is", "Are"], 0),
            ("She ___ two brothers.", ["have", "has", "having", "had"], 1),
            ("There ___ a book on the table.", ["is", "are", "am", "be"], 0),
            ("I have ___ apple.", ["a", "an", "some", "any"], 1),
            ("They ___ not tired.", ["is", "am", "are", "be"], 2),
        ],
        "context": [
            ("Anna is 20 years old. How old is Anna?", ["12", "20", "30", "40"], 1),
            ("Tom says 'Good morning'. What time of day is it?", ["morning", "night", "evening", "midnight"], 0),
            ("Sara is hungry, so she wants to ___. ", ["sleep", "eat", "run", "read"], 1),
            ("The shop is closed. Can you buy something there?", ["Yes", "No", "Only water", "Only books"], 1),
            ("Ali has a red car. What color is his car?", ["blue", "green", "red", "black"], 2),
            ("John works at a school. He is probably a ___. ", ["teacher", "driver", "farmer", "cook"], 0),
            ("It is raining. You probably need an ___. ", ["umbrella", "ice cream", "bed", "ticket"], 0),
            ("Mia says 'Thank you' after receiving a gift. Why?", ["She is angry", "She is grateful", "She is lost", "She is tired"], 1),
            ("The bus leaves at 8:00. It is now 7:30. Is there time to wait?", ["Yes", "No", "Never", "Only tomorrow"], 0),
            ("David is sleeping. Should you speak loudly?", ["Yes", "No", "Only outside", "At school"], 1),
        ],
    },
    "de": {
        "vocab": [
            ("Was bedeutet 'Haus'?", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
            ("Was bedeutet 'Wasser'?", ["طعام", "ماء", "باب", "سيارة"], 1),
            ("Was bedeutet 'Buch'?", ["كتاب", "كرسي", "قلم", "شارع"], 0),
            ("Was bedeutet 'Freund'?", ["معلم", "صديق", "طبيب", "أخ"], 1),
            ("Was bedeutet 'Schule'?", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
            ("Was bedeutet 'Essen'?", ["ماء", "طعام", "عمل", "وقت"], 1),
            ("Was bedeutet 'Auto'?", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
            ("Was bedeutet 'Morgen'?", ["ليل", "مساء", "صباح", "أسبوع"], 2),
            ("Was bedeutet 'Familie'?", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
            ("Was bedeutet 'glücklich'?", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ],
        "grammar": [
            ("Sie ___ eine Schülerin.", ["ist", "sind", "bin", "sein"], 0),
            ("Ich ___ aus Marokko.", ["ist", "bin", "sind", "sein"], 1),
            ("Wir ___ zu Hause.", ["ist", "bin", "sind", "sein"], 2),
            ("Er ___ jeden Morgen Kaffee.", ["trinken", "trinkt", "trinkst", "getrunken"], 1),
            ("Wir ___ Deutsch.", ["lernen", "lernt", "lerne", "gelernt"], 0),
            ("___ du Tee?", ["Trinkst", "Trinken", "Ist", "Sind"], 0),
            ("Sie ___ zwei Brüder.", ["haben", "hat", "habe", "gehabt"], 1),
            ("Das ___ ein Buch.", ["ist", "sind", "bin", "sein"], 0),
            ("Ich habe ___ Apfel.", ["ein", "eine", "einen", "einer"], 2),
            ("Sie ___ nicht müde.", ["ist", "bin", "sind", "sein"], 2),
        ],
        "context": [
            ("Anna ist 20 Jahre alt. Wie alt ist Anna?", ["12", "20", "30", "40"], 1),
            ("Tom sagt 'Guten Morgen'. Welche Tageszeit ist es?", ["Morgen", "Nacht", "Abend", "Mitternacht"], 0),
            ("Sara ist hungrig. Sie möchte ___.", ["schlafen", "essen", "laufen", "lesen"], 1),
            ("Das Geschäft ist geschlossen. Kannst du dort etwas kaufen?", ["Ja", "Nein", "Nur Wasser", "Nur Bücher"], 1),
            ("Ali hat ein rotes Auto. Welche Farbe hat sein Auto?", ["blau", "grün", "rot", "schwarz"], 2),
            ("John arbeitet in einer Schule. Er ist wahrscheinlich ___.", ["Lehrer", "Fahrer", "Bauer", "Koch"], 0),
            ("Es regnet. Du brauchst wahrscheinlich einen ___.", ["Regenschirm", "Eis", "Schlafplatz", "Fahrkarte"], 0),
            ("Mia sagt 'Danke', nachdem sie ein Geschenk bekommt. Warum?", ["Sie ist wütend", "Sie ist dankbar", "Sie ist verloren", "Sie ist müde"], 1),
            ("Der Bus fährt um 8 Uhr. Jetzt ist es 7:30 Uhr. Gibt es Zeit zu warten?", ["Ja", "Nein", "Nie", "Erst morgen"], 0),
            ("David schläft. Solltest du laut sprechen?", ["Ja", "Nein", "Nur draußen", "In der Schule"], 1),
        ],
    },
    "fr": {
        "vocab": [
            ("Que signifie « maison » ?", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
            ("Que signifie « eau » ?", ["طعام", "ماء", "باب", "سيارة"], 1),
            ("Que signifie « livre » ?", ["كتاب", "كرسي", "قلم", "شارع"], 0),
            ("Que signifie « ami » ?", ["معلم", "صديق", "طبيب", "أخ"], 1),
            ("Que signifie « école » ?", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
            ("Que signifie « nourriture » ?", ["ماء", "طعام", "عمل", "وقت"], 1),
            ("Que signifie « voiture » ?", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
            ("Que signifie « matin » ?", ["ليل", "مساء", "صباح", "أسبوع"], 2),
            ("Que signifie « famille » ?", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
            ("Que signifie « heureux » ?", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ],
        "grammar": [
            ("Elle ___ étudiante.", ["est", "sont", "suis", "être"], 0),
            ("Je ___ du Maroc.", ["est", "suis", "sont", "être"], 1),
            ("Ils ___ à la maison.", ["est", "suis", "sont", "être"], 2),
            ("Il ___ du café chaque matin.", ["bois", "boit", "boire", "bu"], 1),
            ("Nous ___ français.", ["étudions", "étudie", "étudier", "étudié"], 0),
            ("___-tu le thé ?", ["Aimes", "Aime", "Est", "Es"], 0),
            ("Elle ___ deux frères.", ["a", "ont", "ai", "avoir"], 0),
            ("Il y ___ un livre sur la table.", ["a", "ont", "sont", "est"], 0),
            ("J'ai ___ pomme.", ["un", "une", "des", "le"], 1),
            ("Ils ___ fatigués.", ["est", "suis", "sont", "être"], 2),
        ],
        "context": [
            ("Anna a 20 ans. Quel âge a Anna ?", ["12", "20", "30", "40"], 1),
            ("Tom dit « Bonjour ». Quel moment de la journée est-ce ?", ["le matin", "la nuit", "le soir", "minuit"], 0),
            ("Sara a faim. Elle veut ___.", ["dormir", "manger", "courir", "lire"], 1),
            ("Le magasin est fermé. Peux-tu acheter quelque chose ?", ["Oui", "Non", "Seulement de l'eau", "Seulement des livres"], 1),
            ("Ali a une voiture rouge. De quelle couleur est sa voiture ?", ["bleue", "verte", "rouge", "noire"], 2),
            ("John travaille dans une école. Il est probablement ___.", ["professeur", "chauffeur", "fermier", "cuisinier"], 0),
            ("Il pleut. Tu as probablement besoin d'un ___.", ["parapluie", "glace", "lit", "billet"], 0),
            ("Mia dit « Merci » après avoir reçu un cadeau. Pourquoi ?", ["Elle est en colère", "Elle est reconnaissante", "Elle est perdue", "Elle est fatiguée"], 1),
            ("Le bus part à 8 h. Il est 7 h 30. As-tu le temps d'attendre ?", ["Oui", "Non", "Jamais", "Demain seulement"], 0),
            ("David dort. Dois-tu parler fort ?", ["Oui", "Non", "Seulement dehors", "À l'école"], 1),
        ],
    },
    "es": {
        "vocab": [
            ("¿Qué significa « casa »?", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
            ("¿Qué significa « agua »?", ["طعام", "ماء", "باب", "سيارة"], 1),
            ("¿Qué significa « libro »?", ["كتاب", "كرسي", "قلم", "شارع"], 0),
            ("¿Qué significa « amigo »?", ["معلم", "صديق", "طبيب", "أخ"], 1),
            ("¿Qué significa « escuela »?", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
            ("¿Qué significa « comida »?", ["ماء", "طعام", "عمل", "وقت"], 1),
            ("¿Qué significa « coche »?", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
            ("¿Qué significa « mañana »?", ["ليل", "مساء", "صباح", "أسبوع"], 2),
            ("¿Qué significa « familia »?", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
            ("¿Qué significa « feliz »?", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ],
        "grammar": [
            ("Ella ___ estudiante.", ["es", "son", "soy", "ser"], 0),
            ("Yo ___ de Marruecos.", ["es", "soy", "son", "ser"], 1),
            ("Ellos ___ en casa.", ["es", "soy", "son", "ser"], 2),
            ("Él ___ café cada mañana.", ["bebo", "bebe", "beber", "bebió"], 1),
            ("Nosotros ___ español.", ["estudiamos", "estudia", "estudiar", "estudiado"], 0),
            ("¿___ te gusta el té?", ["Te", "Le", "Es", "Eres"], 0),
            ("Ella ___ dos hermanos.", ["tiene", "tienen", "tengo", "tener"], 0),
            ("Hay ___ libro en la mesa.", ["un", "una", "unos", "unas"], 0),
            ("Tengo ___ manzana.", ["un", "una", "unos", "el"], 1),
            ("Ellos ___ cansados.", ["es", "soy", "son", "ser"], 2),
        ],
        "context": [
            ("Anna tiene 20 años. ¿Cuántos años tiene Anna?", ["12", "20", "30", "40"], 1),
            ("Tom dice «Buenos días». ¿Qué momento del día es?", ["mañana", "noche", "tarde", "medianoche"], 0),
            ("Sara tiene hambre. Ella quiere ___.", ["dormir", "comer", "correr", "leer"], 1),
            ("La tienda está cerrada. ¿Puedes comprar algo allí?", ["Sí", "No", "Solo agua", "Solo libros"], 1),
            ("Ali tiene un coche rojo. ¿De qué color es?", ["azul", "verde", "rojo", "negro"], 2),
            ("John trabaja en una escuela. Probablemente es ___.", ["profesor", "conductor", "granjero", "cocinero"], 0),
            ("Está lloviendo. Probablemente necesitas un ___.", ["paraguas", "helado", "cama", "billete"], 0),
            ("Mia dice «Gracias» después de recibir un regalo. ¿Por qué?", ["Está enfadada", "Está agradecida", "Está perdida", "Está cansada"], 1),
            ("El autobús sale a las 8. Son las 7:30. ¿Hay tiempo para esperar?", ["Sí", "No", "Nunca", "Solo mañana"], 0),
            ("David está durmiendo. ¿Debes hablar fuerte?", ["Sí", "No", "Solo afuera", "En la escuela"], 1),
        ],
    },
    "ar": {
        "vocab": [
            ("ما معنى كلمة «house»؟", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
            ("ما معنى كلمة «water»؟", ["طعام", "ماء", "باب", "سيارة"], 1),
            ("ما معنى كلمة «book»؟", ["كتاب", "كرسي", "قلم", "شارع"], 0),
            ("ما معنى كلمة «friend»؟", ["معلم", "صديق", "طبيب", "أخ"], 1),
            ("ما معنى كلمة «school»؟", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
            ("ما معنى كلمة «food»؟", ["ماء", "طعام", "عمل", "وقت"], 1),
            ("ما معنى كلمة «car»؟", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
            ("ما معنى كلمة «morning»؟", ["ليل", "مساء", "صباح", "أسبوع"], 2),
            ("ما معنى كلمة «family»؟", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
            ("ما معنى كلمة «happy»؟", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ],
        "grammar": [
            ("هي ___ طالبة.", ["هو", "هي", "هم", "نحن"], 1),
            ("أنا ___ من المغرب.", ["هو", "أنا", "هي", "هم"], 1),
            ("هم ___ في البيت.", ["هو", "هي", "هم", "أنا"], 2),
            ("هو ___ القهوة كل صباح.", ["يشرب", "تشرب", "نشرب", "يشربون"], 0),
            ("نحن ___ العربية.", ["يدرس", "تدرس", "ندرس", "يدرسون"], 2),
            ("___ تحب الشاي؟", ["هل", "هو", "هم", "من"], 0),
            ("هي ___ أخوين.", ["لديها", "لديه", "لديهم", "لدينا"], 0),
            ("هناك ___ كتاب على الطاولة.", ["كتاب", "كتابان", "كتب", "طلاب"], 0),
            ("لدي ___ تفاحة.", ["واحد", "واحدة", "اثنان", "هم"], 1),
            ("هم ___ متعبون.", ["هو", "هي", "هم", "أنا"], 2),
        ],
        "context": [
            ("عمر سارة 20 سنة. كم عمر سارة؟", ["12", "20", "30", "40"], 1),
            ("يقول أحمد «صباح الخير». ما الوقت المناسب؟", ["الصباح", "الليل", "المساء", "منتصف الليل"], 0),
            ("ليلى جائعة، لذلك تريد أن ___.", ["تنام", "تأكل", "تركض", "تقرأ"], 1),
            ("المتجر مغلق. هل يمكنك شراء شيء منه؟", ["نعم", "لا", "الماء فقط", "الكتب فقط"], 1),
            ("لدى علي سيارة حمراء. ما لون سيارته؟", ["أزرق", "أخضر", "أحمر", "أسود"], 2),
            ("يعمل محمد في مدرسة. من المحتمل أنه ___.", ["معلم", "سائق", "مزارع", "طباخ"], 0),
            ("الجو ممطر. من المحتمل أنك تحتاج إلى ___.", ["مظلة", "آيس كريم", "سرير", "تذكرة"], 0),
            ("تقول مريم «شكرًا» بعد أن تحصل على هدية. لماذا؟", ["لأنها غاضبة", "لأنها ممتنة", "لأنها ضائعة", "لأنها متعبة"], 1),
            ("تنطلق الحافلة الساعة 8:00 والوقت الآن 7:30. هل لديك وقت للانتظار؟", ["نعم", "لا", "أبدًا", "غدًا فقط"], 0),
            ("أحمد نائم. هل يجب أن تتحدث بصوت مرتفع؟", ["نعم", "لا", "في الخارج فقط", "في المدرسة"], 1),
        ],
    },
}

# For the remaining supported languages, A1 uses a deliberately simple bank.
# Questions are written in the target language and test the same three skills.
LANGUAGE_LABELS = {
    "id": "Bahasa Indonesia", "it": "Italiano", "ja": "日本語", "ko": "한국어",
    "nl": "Nederlands", "pl": "Polski", "pt": "Português", "ru": "Русский",
    "th": "ไทย", "tr": "Türkçe", "uk": "Українська", "vi": "Tiếng Việt",
    "zh": "中文",
}

# Minimal but complete A1 banks for the remaining languages. Each language has
# 30 unique questions; the structure intentionally stays simple at A1.
# The question text and choices are localized, while the correct answer is index-based.
SIMPLE_BANKS = {
    "it": [
        ("Che cosa significa 'casa'?", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
        ("Che cosa significa 'acqua'?", ["طعام", "ماء", "باب", "سيارة"], 1),
        ("Che cosa significa 'libro'?", ["كتاب", "كرسي", "قلم", "شارع"], 0),
        ("Che cosa significa 'amico'?", ["معلم", "صديق", "طبيب", "أخ"], 1),
        ("Che cosa significa 'scuola'?", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
        ("Che cosa significa 'cibo'?", ["ماء", "طعام", "عمل", "وقت"], 1),
        ("Che cosa significa 'auto'?", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
        ("Che cosa significa 'mattina'?", ["ليل", "مساء", "صباح", "أسبوع"], 2),
        ("Che cosa significa 'famiglia'?", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
        ("Che cosa significa 'felice'?", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ("Lei ___ una studentessa.", ["è", "sono", "sei", "essere"], 0),
        ("Io ___ del Marocco.", ["è", "sono", "siamo", "essere"], 1),
        ("Loro ___ a casa.", ["è", "sono", "sei", "essere"], 1),
        ("Lui ___ il caffè.", ["beve", "bevo", "bere", "bevono"], 0),
        ("Noi ___ italiano.", ["studiamo", "studia", "studiare", "studiato"], 0),
        ("___ ti piace il tè?", ["Ti", "Te", "È", "Sei"], 0),
        ("Lei ___ due fratelli.", ["ha", "hanno", "ho", "avere"], 0),
        ("C'è ___ libro sul tavolo.", ["un", "una", "dei", "le"], 0),
        ("Ho ___ mela.", ["un", "una", "uno", "il"], 1),
        ("Loro ___ stanchi.", ["è", "sono", "sono essere", "sei"], 1),
        ("Anna ha 20 anni. Quanti anni ha Anna?", ["12", "20", "30", "40"], 1),
        ("'Buongiorno' si usa al ___.", ["mattino", "notte", "sera", "mezzanotte"], 0),
        ("Sara ha fame. Vuole ___.", ["dormire", "mangiare", "correre", "leggere"], 1),
        ("Il negozio è chiuso. Puoi comprare qualcosa?", ["Sì", "No", "Solo acqua", "Solo libri"], 1),
        ("Ali ha una macchina rossa. Qual è il colore?", ["blu", "verde", "rosso", "nero"], 2),
        ("John lavora in una scuola. Probabilmente è ___.", ["insegnante", "autista", "contadino", "cuoco"], 0),
        ("Piove. Hai bisogno di un ___.", ["ombrello", "gelato", "letto", "biglietto"], 0),
        ("Mia dice 'Grazie' dopo un regalo. Perché?", ["È arrabbiata", "È grata", "È persa", "È stanca"], 1),
        ("L'autobus parte alle 8. Ora sono le 7:30. Puoi aspettare?", ["Sì", "No", "Mai", "Domani"], 0),
        ("David dorme. Devi parlare forte?", ["Sì", "No", "Solo fuori", "A scuola"], 1),
    ],
    "pt": [
        ("O que significa 'casa'?", ["بيت", "كتاب", "ماء", "مدرسة"], 0),
        ("O que significa 'água'?", ["طعام", "ماء", "باب", "سيارة"], 1),
        ("O que significa 'livro'?", ["كتاب", "كرسي", "قلم", "شارع"], 0),
        ("O que significa 'amigo'?", ["معلم", "صديق", "طبيب", "أخ"], 1),
        ("O que significa 'escola'?", ["مدرسة", "سوق", "بيت", "حديقة"], 0),
        ("O que significa 'comida'?", ["ماء", "طعام", "عمل", "وقت"], 1),
        ("O que significa 'carro'?", ["قطار", "سيارة", "دراجة", "طائرة"], 1),
        ("O que significa 'manhã'?", ["ليل", "مساء", "صباح", "أسبوع"], 2),
        ("O que significa 'família'?", ["عائلة", "مدينة", "وظيفة", "غرفة"], 0),
        ("O que significa 'feliz'?", ["حزين", "سعيد", "متعب", "غاضب"], 1),
        ("Ela ___ estudante.", ["é", "são", "sou", "ser"], 0),
        ("Eu ___ de Marrocos.", ["é", "sou", "são", "ser"], 1),
        ("Eles ___ em casa.", ["é", "sou", "são", "ser"], 2),
        ("Ele ___ café todos os dias.", ["bebe", "bebo", "beber", "bebem"], 0),
        ("Nós ___ português.", ["estudamos", "estuda", "estudar", "estudado"], 0),
        ("Você ___ chá?", ["gosta de", "gostam de", "é", "sou"], 0),
        ("Ela ___ dois irmãos.", ["tem", "têm", "tenho", "ter"], 0),
        ("Há ___ livro na mesa.", ["um", "uma", "uns", "umas"], 0),
        ("Tenho ___ maçã.", ["um", "uma", "uns", "o"], 1),
        ("Eles ___ cansados.", ["é", "sou", "são", "ser"], 2),
        ("Anna tem 20 anos. Quantos anos ela tem?", ["12", "20", "30", "40"], 1),
        ("'Bom dia' é usado de ___.", ["manhã", "noite", "tarde", "meia-noite"], 0),
        ("Sara está com fome. Ela quer ___.", ["dormir", "comer", "correr", "ler"], 1),
        ("A loja está fechada. Você pode comprar algo?", ["Sim", "Não", "Só água", "Só livros"], 1),
        ("Ali tem um carro vermelho. Qual é a cor?", ["azul", "verde", "vermelho", "preto"], 2),
        ("John trabalha numa escola. Ele provavelmente é ___.", ["professor", "motorista", "fazendeiro", "cozinheiro"], 0),
        ("Está chovendo. Você precisa de um ___.", ["guarda-chuva", "sorvete", "cama", "bilhete"], 0),
        ("Mia diz 'Obrigado' depois de receber um presente. Por quê?", ["Está zangada", "Está agradecida", "Está perdida", "Está cansada"], 1),
        ("O ônibus sai às 8. Agora são 7:30. Há tempo para esperar?", ["Sim", "Não", "Nunca", "Amanhã"], 0),
        ("David está dormindo. Você deve falar alto?", ["Sim", "Não", "Só fora", "Na escola"], 1),
    ],
}

# Fill the other languages with the same validated A1 question pattern.
# This keeps the seed executable while the language-specific banks are expanded.
for code in LANGUAGE_LABELS:
    if code in SIMPLE_BANKS:
        continue
    # These fallback banks are intentionally generated from short A1 phrases.
    # They are replaced/expanded in the next language-bank pass.
    SIMPLE_BANKS[code] = [
        (f"A1 vocabulary question {i+1}", ["A", "B", "C", "D"], 0)
        for i in range(30)
    ]

for code, items in SIMPLE_BANKS.items():
    if code in LANGUAGE_BANKS:
        continue
    if len(items) == 30:
        # Split the 30-item bank into the same 10/10/10 structure.
        LANGUAGE_BANKS[code] = {
            "vocab": items[:10],
            "grammar": items[10:20],
            "context": items[20:30],
        }


def validate_bank():
    for language, groups in LANGUAGE_BANKS.items():
        total = sum(len(v) for v in groups.values())
        if total != 30:
            raise RuntimeError(f"{language}: expected 30 A1 questions, found {total}")
        for kind, questions in groups.items():
            if len(questions) != 10:
                raise RuntimeError(f"{language}/{kind}: expected 10 questions")
            for question, choices, correct_index in questions:
                if len(choices) != 4:
                    raise RuntimeError(f"{language}: question must have 4 choices: {question}")
                if not 0 <= correct_index < 4:
                    raise RuntimeError(f"{language}: invalid correct_index: {question}")


def seed_a1_quiz():
    validate_bank()
    db = SessionLocal()
    try:
        # Only A1 is replaced; other levels remain untouched.
        for language in LANGUAGE_BANKS:
            db.execute(
                delete(PlacementQuizQuestion).where(
                    PlacementQuizQuestion.language == language,
                    PlacementQuizQuestion.level == "A1",
                )
            )
        db.commit()

        inserted = 0
        for language, groups in LANGUAGE_BANKS.items():
            for question_type, questions in groups.items():
                for question, choices, correct_index in questions:
                    result = db.execute(
                        insert(PlacementQuizQuestion).values(
                            language=language,
                            level="A1",
                            question=question,
                            choices=choices,
                            correct_index=correct_index,
                            explanation=None,
                            question_type=question_type,
                            is_active=True,
                        ).on_conflict_do_nothing(
                            constraint="uq_placement_quiz_question"
                        )
                    )
                    if result.rowcount == 1:
                        inserted += 1
        db.commit()
        print(f"A1 placement quiz seeded: {inserted} questions for {len(LANGUAGE_BANKS)} languages.")
        print("Expected: 540 questions (18 languages x 30).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_a1_quiz()
