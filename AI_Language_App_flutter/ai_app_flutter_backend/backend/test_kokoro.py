import os
import soundfile as sf
from kokoro_onnx import Kokoro


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "voice", "kokoro-v1.0.onnx")
VOICES_PATH = os.path.join(BASE_DIR, "voice", "voices-v1.0.bin")
OUTPUT_PATH = os.path.join(BASE_DIR, "voice", "kokoro_test.wav")


text = "Bonjour, bienvenue dans votre leçon de français."


print("Chargement de Kokoro...")

kokoro = Kokoro(
    MODEL_PATH,
    VOICES_PATH,
)

print("Génération de la voix...")

samples, sample_rate = kokoro.create(
    text,
    voice="ff_siwis",
    speed=1.0,
    lang="fr-fr",
)

sf.write(
    OUTPUT_PATH,
    samples,
    sample_rate,
)

print()
print("✅ Test Kokoro terminé avec succès.")
print(f"Fichier audio : {OUTPUT_PATH}")