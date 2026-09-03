LEVELS = [
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]

ALL_LEVELS = LEVELS.copy()

# The learner must know at least half of the sampled words
# to pass vocabulary screening for a level.
PASS_THRESHOLD = 50.0

# Each level has a bank of 100 active words.
# The placement test randomly presents 20 words per level.
VOCABULARY_BANK_SIZE = 100
WORDS_PER_LEVEL = 20
