"""Blackjack view (single player vs dealer)."""

import contextlib

import discord

from bot.core import emojis
from bot.games.blackjack import calculate_hand, create_deck
from bot.games.gambling import settle_blackjack


class BlackjackView(discord.ui.View):
    def __init__(self, player, *, bot, bet=0):
        super().__init__(timeout=180.0)
        self.player = player
        self.bot = bot
        self.bet = bet
        self.settled = False
        self.deck = create_deck()
        self.player_hand = [self.draw_card(), self.draw_card()]
        self.dealer_hand = [self.draw_card(), self.draw_card()]
        self.message = None

    def draw_card(self):
        return self.deck.pop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.player.id:
            return True
        await interaction.response.send_message("This is not your game!", ephemeral=True)
        return False

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_hand.append(self.draw_card())
        if calculate_hand(self.player_hand) > 21:
            await self.end_game(interaction, "You busted! Dealer wins.")
        else:
            await interaction.response.edit_message(embed=self.hidden_embed(), view=self)

    @discord.ui.button(label="Stay", style=discord.ButtonStyle.secondary)
    async def stay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.end_game(interaction, self._stand())

    def _stand(self):
        """Play out the dealer's hand and return the result line."""
        while calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())
        dealer_score = calculate_hand(self.dealer_hand)
        player_score = calculate_hand(self.player_hand)
        if dealer_score > 21 or player_score > dealer_score:
            return "You win!"
        if player_score < dealer_score:
            return "Dealer wins."
        return "It's a tie."

    def hidden_embed(self):
        """Embed shown mid-game, with the dealer's second card hidden."""
        player_score = calculate_hand(self.player_hand)
        dealer_score = calculate_hand(self.dealer_hand[:1])
        embed = discord.Embed(title="Blackjack", color=discord.Color.green())
        embed.add_field(name="Your Hand", value=f"{self.player_hand} (Score: {player_score})", inline=False)
        embed.add_field(
            name="Dealer's Hand", value=f"{self.dealer_hand[:1]} [?] (Score: {dealer_score}?)", inline=False
        )
        return embed

    def _settle(self, result):
        """Pay out the wager for ``result`` and return the final embed."""
        lower = result.lower()
        color = 0x00FF00 if "you win" in lower else 0x808080 if "tie" in lower else 0xFF0000
        embed = discord.Embed(title="Blackjack", color=color)
        embed.add_field(
            name="Your Hand", value=f"{self.player_hand} (Score: {calculate_hand(self.player_hand)})", inline=False
        )
        embed.add_field(
            name="Dealer's Hand", value=f"{self.dealer_hand} (Score: {calculate_hand(self.dealer_hand)})", inline=False
        )
        embed.add_field(name="Result", value=result, inline=False)
        if self.bet:
            credit = settle_blackjack(result, self.bet)
            if credit:
                self.bot.economy.add_coins(self.player.id, str(self.player), credit)
            net = credit - self.bet
            if net > 0:
                coins_text = f"You won **+{net}** MiniCoins {emojis.COIN}"
            elif net == 0:
                coins_text = f"Push, your bet was returned {emojis.COIN}"
            else:
                coins_text = f"You lost **{self.bet}** MiniCoins {emojis.COIN}"
            embed.add_field(name="MiniCoins", value=coins_text, inline=False)
        self.settled = True
        self.stop()
        return embed

    async def end_game(self, interaction, result):
        await interaction.response.edit_message(embed=self._settle(result), view=None)

    async def on_timeout(self):
        # Walking away doesn't hand the bet back: the hand stands as it is, so
        # sitting out a bad hand can't dodge the loss.
        if self.settled:
            return
        embed = self._settle(self._stand())
        embed.set_footer(text="You went quiet, so I stood for you.")
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(embed=embed, view=None)
