"""Pure Rock-Paper-Scissors logic. No discord imports."""

BEATS = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}


def winner(choice_a, choice_b):
    """Return 'a' if choice_a wins, 'b' if choice_b wins, or None for a tie."""
    if choice_a == choice_b:
        return None
    return "a" if BEATS[choice_a] == choice_b else "b"
