import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "test_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SAMPLE_TEXTS = {
    "ar": "مرحباً بك، هذا اختبار للصوت العربي.",
    "de": "Hallo, das ist ein Test für die deutsche Stimme.",
    "es": "Hola, esta es una prueba de voz en español.",
    "fr": "Bonjour, ceci est un test pour la voix française.",
    "id": "Halo, ini adalah tes untuk suara Bahasa Indonesia.",
    "it": "Ciao, questo è un test per la voce italiana.",
    "ja": "こんにちは、これは日本語の音声テストです。",
    "ko": "안녕하세요, 한국어 음성 테스트입니다.",
    "nl": "Hallo, dit is een test voor de Nederlandse stem.",
    "pl": "Cześć, to jest test polskiego głosu.",
    "pt": "Olá, este é um teste para a voz em português.",
    "ru": "Привет, это тест русского голоса.",
    "th": "สวัสดีครับ นี่คือการทดสอบเสียงภาษาไทย",
    "tr": "Merhaba, bu Türkçe ses için bir testtir.",
    "uk": "Привіт, це тест українського голосу.",
    "vi": "Xin chào, đây là bài kiểm tra giọng nói tiếng Việt.",
    "zh": "你好，这是中文语音测试。",
    "en": "Hello, this is a test for the English voice."
}

def test_all_voices():
    onnx_files = [f for f in os.listdir(BASE_DIR) if f.endswith(".onnx")]
    print(f"--- جاري اختبار {len(onnx_files)} صوت متاح ---\n")

    for file in onnx_files:
        model_path = os.path.join(BASE_DIR, file)
        lang_code = file.split("_")[0].lower()
        text = SAMPLE_TEXTS.get(lang_code, "Hello, this is a voice test.")
        output_wav = os.path.join(OUTPUT_DIR, f"{os.path.splitext(file)[0]}.wav")

        print(f"[+] جاري اختبار: {file}")
        
        # حذف الملف القديم إن وجد لتفادي القراءة الخاطئة
        if os.path.exists(output_wav):
            os.remove(output_wav)

        try:
            # إضافة --speaker 0 للأصوات التي تحتوي على عدة متحدثين
            cmd = ["piper", "--model", model_path, "--output_file", output_wav, "--speaker", "0"]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            _, stderr = process.communicate(input=text)

            # التحقق من أن الملف تم إنشاؤه بحجم أكبر من 0
            if os.path.exists(output_wav) and os.path.getsize(output_wav) > 0:
                print(f"[✓] تم توليد الصوت بنجاح ({os.path.getsize(output_wav)} bytes)\n")
            else:
                print(f"[X] فشل التوليد! تفاصيل الخطأ من Piper:\n{stderr.strip()}\n")
                if os.path.exists(output_wav):
                    os.remove(output_wav)
        except Exception as e:
            print(f"[X] خطأ في تنفيذ الأمر: {e}\n")

if __name__ == "__main__":
    test_all_voices()