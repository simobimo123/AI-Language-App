LEVELS = [
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]

ALL_LEVELS = [
    "PRE_A1",
    *LEVELS,
]

# The user must know at least half of the sampled words
# to pass vocabulary screening for a level.
PASS_THRESHOLD = 50.0

# Each level must have a bank of 100 active words.
# The placement test randomly presents only 20 words
# from that bank for each attempt.
VOCABULARY_BANK_SIZE = 100
WORDS_PER_LEVEL = 20

QUIZ_QUESTIONS_PER_TEST = 10
QUIZ_PASS_THRESHOLD = 50.0
