"""Blackjack view (single player vs dealer)."""

import discord

from bot.games.blackjack import calculate_hand, create_deck
from bot.games.gambling import settle_blackjack


class BlackjackButton(discord.ui.Button):
    def __init__(self, label, style, action):
        super().__init__(label=label, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: BlackjackView = self.view
        if interaction.user != view.player:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        if self.action == "hit":
            view.player_hand.append(view.draw_card())
            if calculate_hand(view.player_hand) > 21:
                await view.end_game(interaction, "You busted! Dealer wins.")
                return
        elif self.action == "stay":
            while calculate_hand(view.dealer_hand) < 17:
                view.dealer_hand.append(view.draw_card())
            dealer_score = calculate_hand(view.dealer_hand)
            player_score = calculate_hand(view.player_hand)
            if dealer_score > 21 or player_score > dealer_score:
                await view.end_game(interaction, "You win!")
            elif player_score < dealer_score:
                await view.end_game(interaction, "Dealer wins.")
            else:
                await view.end_game(interaction, "It's a tie.")
            return

        await view.update_message(interaction)


class BlackjackView(discord.ui.View):
    def __init__(self, player, *, bot=None, bet=0):
        super().__init__(timeout=180.0)
        self.player = player
        self.bot = bot
        self.bet = bet
        self.settled = False
        self.deck = create_deck()
        self.player_hand = [self.draw_card(), self.draw_card()]
        self.dealer_hand = [self.draw_card(), self.draw_card()]
        self.message = None
        self.add_item(BlackjackButton("Hit", discord.ButtonStyle.primary, "hit"))
        self.add_item(BlackjackButton("Stay", discord.ButtonStyle.secondary, "stay"))

    def draw_card(self):
        return self.deck.pop()

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

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.hidden_embed(), view=self)

    async def end_game(self, interaction, result):
        player_score = calculate_hand(self.player_hand)
        dealer_score = calculate_hand(self.dealer_hand)
        lower = result.lower()
        if "you win" in lower:
            color = 0x00FF00
        elif "tie" in lower:
            color = 0x808080
        else:
            color = 0xFF0000

        embed = discord.Embed(title="Blackjack", color=color)
        embed.add_field(name="Your Hand", value=f"{self.player_hand} (Score: {player_score})", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand} (Score: {dealer_score})", inline=False)
        embed.add_field(name="Result", value=result, inline=False)
        if self.bet and self.bot is not None:
            credit = settle_blackjack(result, self.bet)
            if credit:
                self.bot.economy.add_coins(self.player.id, str(self.player), credit)
            net = credit - self.bet
            coins_text = (
                f"You won **+{net}** coins 🪙"
                if net > 0
                else "Push — your bet was returned 🪙"
                if net == 0
                else f"You lost **{self.bet}** coins 🪙"
            )
            embed.add_field(name="Coins", value=coins_text, inline=False)
        self.settled = True
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        # Refund a still-pending wager so an AFK game doesn't quietly eat coins.
        if self.bet and self.bot is not None and not self.settled:
            self.bot.economy.add_coins(self.player.id, str(self.player), self.bet)
            self.settled = True
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
