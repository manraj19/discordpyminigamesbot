"""Shared reward result and its one-line renderer.

Every game, duel, and quest payout returns a ``RewardResult`` and shows
``line()``, so rewards look the same everywhere from a single place. Later
systems (XP, level-ups, quests) fill the extra fields and they appear across
every game with no per-game work.
"""

from dataclasses import dataclass, field

from bot.core import emojis


@dataclass
class RewardResult:
    coins: int = 0
    xp: int = 0
    new_achievements: list = field(default_factory=list)  # [(name, coin_reward), ...]
    level_up: int | None = None  # the new level number, if the action leveled the player up
    first_win_bonus: int = 0

    def line(self) -> str:
        """One uniform reward line, e.g.
        ``COIN +15 MiniCoins · +5 XP · Achievement: Gladiator +500``.

        Returns an empty string when nothing was earned, so a caller that might
        award nothing (a score of 0) should fall back to its own message."""
        parts = []
        if self.coins:
            parts.append(f"{emojis.COIN} **+{self.coins}** MiniCoins")
        if self.first_win_bonus:
            parts.append(f"🌅 First win of the day **+{self.first_win_bonus}**")
        if self.xp:
            parts.append(f"⭐ **+{self.xp}** XP")
        if self.level_up:
            parts.append(f"⬆️ **Level {self.level_up}!**")
        for name, reward in self.new_achievements:
            bonus = f" **+{reward}**" if reward else ""
            parts.append(f"🏅 Achievement: **{name}**{bonus}")
        return " · ".join(parts)
