from pathlib import Path
import re
import shutil
from collections import Counter

# =========================================================
# Paths
# =========================================================

INPUT_FILE = Path(
    r"C:\Users\simobimo\Documents\AI_Language_App111"
    r"\ai_app_flutter_backend\backend\data\vocabulary"
    r"\ar_vocavulary_to_generet\a1.txt"
)

BACKUP_FILE = INPUT_FILE.with_name("a1_backup.txt")
REPORT_FILE = INPUT_FILE.with_name("a1_duplicates_report.txt")


# =========================================================
# Normalize Arabic word
# =========================================================

def normalize_word(word: str) -> str:
    """
    Normalize Arabic text for duplicate detection.
    This does NOT modify the original word.
    """

    word = word.strip()

    # Remove Arabic diacritics
    word = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", word)

    # Normalize Alef variations
    word = re.sub(r"[إأآٱ]", "ا", word)

    # Normalize Alef Maqsura
    word = word.replace("ى", "ي")

    # Normalize Persian/Arabic Ya
    word = word.replace("ی", "ي")

    # Normalize Persian Kaf
    word = word.replace("ک", "ك")

    # Normalize whitespace
    word = re.sub(r"\s+", " ", word)

    return word


# =========================================================
# Read words
# =========================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"File not found: {INPUT_FILE}")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    lines = f.readlines()


words = []

for line in lines:
    line = line.strip()

    if not line:
        continue

    # Remove numbering such as:
    # 1. مرحبا
    # 25. مدرسة
    match = re.match(r"^\d+\.\s*(.+)$", line)

    if match:
        word = match.group(1).strip()
        words.append(word)


# =========================================================
# Analyze duplicates
# =========================================================

normalized_words = [normalize_word(word) for word in words]

counter = Counter(normalized_words)

duplicates = {
    normalized: count
    for normalized, count in counter.items()
    if count > 1
}


# =========================================================
# Statistics
# =========================================================

total_words = len(words)
unique_words = len(counter)
duplicate_entries = sum(count - 1 for count in counter.values() if count > 1)


print()
print("=" * 60)
print("A1 Arabic Vocabulary - Duplicate Analysis")
print("=" * 60)
print()

print(f"Total entries       : {total_words}")
print(f"Unique words        : {unique_words}")
print(f"Duplicate entries   : {duplicate_entries}")
print(f"Number of duplicates: {len(duplicates)}")
print()


# =========================================================
# Show duplicates
# =========================================================

if duplicates:
    print("DUPLICATES FOUND")
    print("-" * 60)

    for normalized, count in duplicates.items():

        original_words = [
            word
            for word in words
            if normalize_word(word) == normalized
        ]

        print(f"{normalized} -> {count} times")
        print(f"  {original_words}")

else:
    print("No duplicates found.")


# =========================================================
# Create report
# =========================================================

with REPORT_FILE.open("w", encoding="utf-8") as f:

    f.write("A1 Arabic Vocabulary - Duplicate Report\n")
    f.write("=" * 60 + "\n\n")

    f.write(f"Total entries: {total_words}\n")
    f.write(f"Unique words: {unique_words}\n")
    f.write(f"Duplicate entries: {duplicate_entries}\n")
    f.write(f"Number of duplicate groups: {len(duplicates)}\n\n")

    if duplicates:

        f.write("DUPLICATES\n")
        f.write("-" * 60 + "\n")

        for normalized, count in duplicates.items():

            original_words = [
                word
                for word in words
                if normalize_word(word) == normalized
            ]

            f.write(f"{normalized} -> {count} times\n")
            f.write(f"  {original_words}\n")

    else:
        f.write("No duplicates found.\n")


print()
print(f"Report saved to:")
print(REPORT_FILE)
print()
print("IMPORTANT: Original file was NOT modified.")