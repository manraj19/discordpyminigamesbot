"""Small shared helpers used across cogs."""


def invalid_opponent(opponent, author, *, self_message="You cannot play against yourself!"):
    """Return a rejection string for an invalid PvP matchup, or None if valid."""
    if opponent == author:
        return self_message
    if opponent.bot:
        return "You cannot play against a bot!"
    return None
