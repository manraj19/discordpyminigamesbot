"""Pure Bomb Party logic: game state, prompts, word judging, lives and turns.

No discord here. A game is a free-for-all for 2 to 6 players who take turns
typing a word containing the current letter fragment before the bomb goes off.
The cog owns the clock and the messages; everything about the rules lives here.
"""

from dataclasses import dataclass, field

from bot.data import BOMB_PROMPTS, DICTIONARY

STARTING_LIVES = 2
MAX_LIVES = 3  # the alphabet bonus cannot push you past this
MIN_PLAYERS = 2
MAX_PLAYERS = 6  # past this the wait between your turns drags

# Every turn gets its own clock instead of one fuse handed along with the bomb.
# A shared fuse is truer to the original, but next to a visible countdown it pays
# you to sit on the bomb and pass it on with two seconds left: no risk to you,
# no chance for them. The clock instead tightens per round, so the pressure still
# climbs and two stubborn players cannot stall forever.
TURN_SECONDS_START = 15
TURN_SECONDS_MIN = 7
TURN_SECONDS_DECAY = 1  # trimmed per completed round

# Use every one of these in your words to earn a life back. X and Z are left out
# so the bonus is actually reachable in a normal game.
BONUS_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyz") - {"x", "z"}

# Prompts get rarer as the game drags on: each tier is the fewest matching words
# a fragment may have to appear in that round.
EASY_FLOOR = 500
MEDIUM_FLOOR = 150
HARD_FLOOR = min(BOMB_PROMPTS.values(), default=40)
_POOLS = {
    floor: sorted(f for f, n in BOMB_PROMPTS.items() if n >= floor) for floor in (EASY_FLOOR, MEDIUM_FLOOR, HARD_FLOOR)
}


@dataclass
class BombGame:
    players: list  # user ids, in turn order
    lives: dict  # user id -> lives left (0 means eliminated)
    letters: dict  # user id -> letters they have used, for the alphabet bonus
    used: set = field(default_factory=set)  # words already played this game
    turn: int = 0  # index into players
    prompt: str = ""
    round: int = 1


def new_game(player_ids):
    return BombGame(
        players=list(player_ids),
        lives={pid: STARTING_LIVES for pid in player_ids},
        letters={pid: set() for pid in player_ids},
    )


def current_player(game):
    return game.players[game.turn]


def alive(game):
    return [pid for pid in game.players if game.lives[pid] > 0]


def winner(game):
    """The last player standing, or None while the game is still going."""
    survivors = alive(game)
    return survivors[0] if len(survivors) == 1 else None


def turn_seconds(round_no):
    """Seconds the player on turn gets. A function of the round and nothing else,
    so how long the player before you dawdled can never cost you time."""
    return max(TURN_SECONDS_MIN, TURN_SECONDS_START - (round_no - 1) * TURN_SECONDS_DECAY)


def sample_prompt(rng, round_no):
    floor = EASY_FLOOR if round_no <= 3 else MEDIUM_FLOOR if round_no <= 7 else HARD_FLOOR
    return rng.choice(_POOLS[floor])


def normalize(text):
    """Reduce a chat message to a candidate word, or "" if it cannot be one."""
    word = text.strip().lower()
    return word if word.isalpha() and word.isascii() else ""


def judge(game, word):
    """Rate a guess: 'ok', 'no_prompt', 'not_a_word', or 'used'."""
    if not word:
        return "not_a_word"
    if game.prompt not in word:
        return "no_prompt"
    if word in game.used:
        return "used"
    if word not in DICTIONARY:
        return "not_a_word"
    return "ok"


def accept(game, word):
    """Bank a valid word for the current player. Returns True if it completed the
    alphabet and earned them a life back."""
    pid = current_player(game)
    game.used.add(word)
    used_letters = game.letters[pid]
    used_letters.update(word)
    if BONUS_LETTERS <= used_letters:
        used_letters.clear()
        if game.lives[pid] < MAX_LIVES:
            game.lives[pid] += 1
            return True
    return False


def explode(game):
    """The bomb goes off in the current player's hands. Returns True if that
    knocked them out."""
    pid = current_player(game)
    game.lives[pid] = max(0, game.lives[pid] - 1)
    return game.lives[pid] == 0


def advance(game):
    """Pass the bomb to the next player who is still alive."""
    for _ in range(len(game.players)):
        game.turn = (game.turn + 1) % len(game.players)
        if game.turn == 0:
            game.round += 1
        if game.lives[game.players[game.turn]] > 0:
            return
