"""Pure logic for the 5-letter word guessing game. No discord imports."""

GREEN = "🟩"  # right letter, right spot
YELLOW = "🟨"  # right letter, wrong spot
GRAY = "⬛"  # letter not in the word


def is_valid_guess(guess):
    return len(guess) == 5 and guess.isalpha()


def score_guess(guess, answer):
    """Return five tiles for ``guess`` vs ``answer``, handling repeated
    letters the standard way (a letter only earns yellow/green as many times
    as it actually appears in the answer)."""
    guess = guess.lower()
    answer = answer.lower()
    tiles = [GRAY] * 5
    remaining = list(answer)

    # First pass: exact-position matches.
    for i in range(5):
        if guess[i] == answer[i]:
            tiles[i] = GREEN
            remaining[i] = None

    # Second pass: present-but-misplaced, consuming remaining letters.
    for i in range(5):
        if tiles[i] == GREEN:
            continue
        if guess[i] in remaining:
            tiles[i] = YELLOW
            remaining[remaining.index(guess[i])] = None

    return tiles
