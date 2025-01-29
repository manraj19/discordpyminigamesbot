import random
import discord
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from tabulate import tabulate
from discord import ButtonStyle, Interaction
from discord.ui import Button, View, Select
import asyncio
import sqlite3
import requests
import datetime
import topgg
from discord.app_commands.errors import CommandOnCooldown, CommandInvokeError
from discord.errors import HTTPException

# Cache for frequently requested data
cache = {}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.AutoShardedBot(command_prefix=';', intents=intents)
bot.remove_command('help')

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name=";help"))
    print(f'Logged in as {bot.user}')
    await bot.add_cog(TopGG(bot))

@bot.command()
async def sync(ctx):
    print("sync command")
    if ctx.author.id == 678908396845400074:
        await bot.tree.sync()
        await ctx.send('Command tree synced.')
    else:
        await ctx.send('You must be the owner to use this command!')

#HELP COMMAND
@bot.group(invoke_without_command=True)
async def help(ctx):
    embed = discord.Embed(title="Help", description="Use ;help <command> for more info on a command.\n[Support Server](https://discord.gg/3UpnJhjkKZ) | [Top.gg Vote](https://top.gg/bot/1285070559087951974/vote)", color=0xf1c40f)
    
    embed.add_field(name="Games", value="`dino`, `rockpaperscissors`, `connect4`, `tictactoe`, `fight`, `wordle`, `flagle`, `mathematics`, `blackjack`, `8ball`, `truthordare`, `riddle`, `race`", inline=False)
    embed.add_field(name= "Cricket", value="`simulate`, `livecricket`, `playcricket`", inline=False)
    embed.add_field(name="Utility", value="`profile`, `leaderboard`, `define`, `urbandictionary`, `botinfo`", inline=False)
    embed.set_footer(text="Developed by fzng (fang).")
    embed.set_thumbnail(url=bot.user.avatar)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="help", description="See the list of commands.")
async def helpmessage(interaction: discord.Interaction):
    embed = discord.Embed(title="Help", description="Use ;help <command> for more info on a command.\n[Support Server](https://discord.gg/3UpnJhjkKZ) | [Top.gg Vote](https://top.gg/bot/1285070559087951974/vote)", color=0xf1c40f)
    
    embed.add_field(name="Games", value="`dino`, `rockpaperscissors`, `connect4`, `tictactoe`, `fight`, `wordle`, `flagle`, `mathematics`, `blackjack`, `8ball`, `truthordare`, `riddle`, `race`", inline=False)
    embed.add_field(name= "Cricket", value="`simulate`, `livecricket`, `playcricket`", inline=False)
    embed.add_field(name="Utility", value="`profile`, `leaderboard`, `define`, `urbandictionary`, `botinfo`", inline=False)
    embed.set_footer(text="Developed by fzng (fang).")
    embed.set_thumbnail(url=bot.user.avatar)
    
    await interaction.response.send_message(embed=embed)

@help.command()
async def dino(ctx):
    embed = discord.Embed(title="Dino", description="Play a game of Dino Run.", color=0x00ff00)
    embed.add_field(name="Usage", value=";dino", inline=False)
    embed.add_field(name="Instructions", value="To evade a cactus you `jump` over it and to evade a bird you `duck` under it.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases=['rps'])
async def rockpaperscissors(ctx):
    embed = discord.Embed(title="Rock Paper Scissors", description="Play a game of Rock Paper Scissors.", color=0x00ff00)
    embed.add_field(name="Aliases", value="rps", inline=False)
    embed.add_field(name="Usage", value=";rockpaperscissors <opponent>", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases=['ttt'])
async def tictactoe(ctx):
    embed = discord.Embed(title="Tic Tac Toe", description="Play a game of Tic Tac Toe.", color=0x00ff00)
    embed.add_field(name="Aliases", value="ttt", inline=False)
    embed.add_field(name="Usage", value=";tictactoe <opponent>", inline=False)
    await ctx.send(embed=embed)

@help.command()
async def wordle(ctx):
    embed = discord.Embed(title="Wordle", description="Play a game of Wordle.", color=0x00ff00)
    embed.add_field(name="Usage", value=";wordle", inline=False)
    embed.add_field(name="Instructions", value="Guess the 5-letter word in 6 attempts. Letters in brackets like `(a)` mean that the letter is there in the word but not in that position. Letters without brackets mean that the letter is in the correct position.", inline=False)
    await ctx.send(embed=embed)

@help.command()
async def flagle(ctx):
    embed = discord.Embed(title="Flagle", description="Play a flag quiz.", color=0x00ff00)
    embed.add_field(name="Usage", value=";flagle", inline=False)
    embed.add_field(name="Instructions", value="Guess the country based on its flag.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases=['sim'])
async def simulate(ctx):
    embed = discord.Embed(title="Simulation", description="Simulate a game of cricket.", color=0x00ff00)
    embed.add_field(name="Aliases", value="sim", inline=False)
    embed.add_field(name="Usage", value=";simulate", inline=False)
    embed.add_field(name="Instructions", value="Enter the names of the teams and players to simulate a game of cricket. Only works with 11 players each side. Player names must be comma-separated.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases=['maths', 'math'])
async def mathematics(ctx):
    embed = discord.Embed(title="Mathematics", description="Solve mathematical problems.", color=0x00ff00)
    embed.add_field(name="Aliases", value="math, maths", inline=False)
    embed.add_field(name="Usage", value=";mathematics <category>", inline=False)
    embed.add_field(name="Instructions", value="There are four categories: addition, substraction, multiplication and division.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases=['lb'])
async def leaderboard(ctx):
    embed = discord.Embed(title="Leaderboard", description="View the leaderboard for various games.", color=0x00ff00)
    embed.add_field(name="Aliases", value="lb", inline=False)
    embed.add_field(name="Usage", value=";leaderboard <game>", inline=False)
    embed.add_field(name="Instructions", value="Currently, only the 'dino' and 'flagle' game leaderboards are supported.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases=['bj'])
async def blackjack(ctx):
    embed = discord.Embed(title="Blackjack", description="Play a game of Blackjack.", color=0x00ff00)
    embed.add_field(name="Aliases", value="bj", inline=False)
    embed.add_field(name="Usage", value=";blackjack", inline=False)
    embed.add_field(name="Instructions", value="The goal is to get as close to 21 as possible without going over. You can `hit` to increase your number or `stay` if you're confident with it.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['def'])
async def define(ctx):
    embed = discord.Embed(title="Define", description="Define a word.", color=0x00ff00)
    embed.add_field(name="Aliases", value="def", inline=False)
    embed.add_field(name="Usage", value=";define <word>", inline=False)
    embed.add_field(name="Instructions", value="Get the definition of any word using this command.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['urban'])
async def urbandictionary(ctx):
    embed = discord.Embed(title="Urban Dictionary", description="Get the definition of a word from Urban Dictionary.", color=0x00ff00)
    embed.add_field(name="Aliases", value="urban", inline=False)
    embed.add_field(name="Usage", value=";urbandictionary <word>", inline=False)
    embed.add_field(name="Instructions", value="Get the definition of any word from Urban Dictionary using this command.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['lc', 'live'])
async def livecricket(ctx):
    embed = discord.Embed(title="Live Cricket", description="Get live cricket scores.", color=0x00ff00)
    embed.add_field(name="Aliases", value="lc, live", inline=False)
    embed.add_field(name="Usage", value=";livecricket", inline=False)
    embed.add_field(name="Instructions", value="Get live cricket scores using this command.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['play'])
async def playcricket(ctx):
    embed = discord.Embed(title="Play Cricket", description="Play a game of classic hand cricket.", color=0x00ff00)
    embed.add_field(name="Aliases", value="play", inline=False)
    embed.add_field(name="Usage", value=";playcricket", inline=False)
    embed.add_field(name="Instructions", value="Don't guess the same number as the bot!", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['8ball'])
async def _8ball(ctx):
    embed = discord.Embed(title="8ball", description="Ask the magic 8ball a question.", color=0x00ff00)
    embed.add_field(name="Usage", value=";8ball <question>", inline=False)
    embed.add_field(name="Instructions", value="Ask the magic 8ball a question and it will give you an answer.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['tod'])
async def truthordare(ctx):
    embed = discord.Embed(title="Truth or Dare", description="Play a game of Truth or Dare.", color=0x00ff00)
    embed.add_field(name="Aliases", value="tod", inline=False)
    embed.add_field(name="Usage", value=";truthordare", inline=False)
    embed.add_field(name="Instructions", value="Play a game of Truth or Dare with your friends.", inline=False)
    await ctx.send(embed=embed)

@help.command()
async def fight(ctx):
    embed = discord.Embed(title="Fight", description="Fight against another user.", color=0x00ff00)
    embed.add_field(name="Usage", value=";fight <opponent>", inline=False)
    embed.add_field(name="Instructions", value="Light attack: 5-15 damage, doesn't miss\nHeavy attack: 25-30 damage, 20 percent chance of missing\nCrash Out: 60 damage, 50/50 chance of hitting either users\nDodge: 60 percent success rate\nParry: 30 percent success rate, does counter-damage if successful", inline=False)
    await ctx.send(embed=embed)

@help.command()
async def race(ctx):
    embed = discord.Embed(title="Race", description="Race against another user.", color=0x00ff00)
    embed.add_field(name="Usage", value=";race <opponent>", inline=False)
    embed.add_field(name="Instructions", value="Type the words in `backticks` as fast as you can!", inline=False)
    await ctx.send(embed=embed)
    
@help.command(aliases = ['bot', 'info'])
async def botinfo(ctx):
    embed = discord.Embed(title="Bot Info", description="Get information about the bot.", color=0x00ff00)
    embed.add_field(name="Aliases", value="bot, info", inline=False)
    embed.add_field(name="Usage", value=";botinfo", inline=False)
    embed.add_field(name="Instructions", value="Get information about the bot using this command.", inline=False)
    await ctx.send(embed=embed)

@help.command(aliases = ['c4'])
async def connect4(ctx):
    embed = discord.Embed(title="Connect 4", description="Play a game of Connect 4.", color=0x00ff00)
    embed.add_field(name="Aliases", value="c4", inline=False)
    embed.add_field(name="Usage", value=";connect4 <opponent>", inline=False)
    embed.add_field(name="Instructions", value="Play a game of classic Connect 4 with your friends. Connect 4 dots in a row to win!", inline=False)
    await ctx.send(embed=embed)

@help.command()
async def riddle(ctx):
    embed = discord.Embed(title="Riddle", description="Solve a riddle.", color=0x00ff00)
    embed.add_field(name="Usage", value=";riddle", inline=False)
    embed.add_field(name="Instructions", value="Solve the riddle to win!", inline=False)
    await ctx.send(embed=embed)

@help.command()
async def profile(ctx):
    embed = discord.Embed(title="Profile", description="View your profile.", color=0x00ff00)
    embed.add_field(name="Usage", value=";profile", inline=False)
    embed.add_field(name="Instructions", value="Shows your scores and ranks in different games.", inline=False)
    await ctx.send(embed=embed)

@bot.tree.command(name="hello", description="A simple slash command")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("this is a slash command")

#ERROR HANDLING
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing Argument! Please use `;help {ctx.command}` to see more.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist. Please use `;help` to see the list of commands.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid Argument! Please use `;help {ctx.command}` to see more.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command cannot be used in private messages.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have the required permissions to use this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Please try again after {error.retry_after:.2f} seconds.")
    else:
        await ctx.send("An error occurred while processing the command.")
        raise error

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if interaction.response.is_done():
        # If the initial response was already sent, use followup to prevent repeated send_message calls
        send_func = interaction.followup.send
    else:
        send_func = interaction.response.send_message
    
    # Handle specific errors
    if isinstance(error, CommandOnCooldown):
        # Only send a cooldown message if needed
        await send_func(f"This command is on cooldown. Please try again after {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, CommandInvokeError):
        await send_func("An error occurred while processing the command.", ephemeral=True)
    elif isinstance(error, HTTPException):
        await send_func("The bot is being rate-limited by Discord. Please wait a moment and try again.", ephemeral=True)
    else:
        await send_func("An unknown error occurred.", ephemeral=True)

async def get_cached_data(key, fetch_function, *args, **kwargs):
    if key in cache:
        return cache[key]
    data = await fetch_function(*args, **kwargs)
    cache[key] = data
    return data

async def fetch_data_with_retry(url, retries=3, backoff_factor=2):
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                await asyncio.sleep(retry_after * backoff_factor ** i)
            else:
                raise e
    raise Exception("Failed to fetch data after retries")

# Set up SQLite database
conn = sqlite3.connect('scores.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS scores (
    user_id INTEGER,
    username TEXT,
    score INTEGER,
    game TEXT,
    PRIMARY KEY (user_id, game)
)''')
conn.commit()

def simulate_innings(batting_team, bowling_team, overs, max_overs_per_bowler, target=None):
    runs = 0
    wickets = 0
    balls_faced = {player: 0 for player in batting_team}
    player_scores = {player: 0 for player in batting_team}
    player_wickets = {player: 0 for player in bowling_team}
    bowler_overs = {player: 0 for player in bowling_team}
    highlights = []
    fifty_highlighted = set()
    hundred_highlighted = set()
    balls_bowled = 0

    for over in range(overs):
        if wickets >= 10:
            break
        for ball in range(6):
            if wickets >= 10:
                break
            balls_bowled += 1
            outcome = random.choices(
                ["dot", "single", "double", "triple", "four", "six", "wicket"],
                [0.3, 0.4, 0.1, 0.05, 0.1, 0.05, 0.1]
            )[0]
            batsman = batting_team[wickets]
            balls_faced[batsman] += 1
            if outcome == "wicket":
                dismissal_type = random.choice(["bowled", "caught", "run out"])
                if dismissal_type == "bowled":
                    bowler = random.choice([b for b in bowling_team if bowler_overs[b] < max_overs_per_bowler])
                    player_wickets[bowler] += 1
                    bowler_overs[bowler] += 1
                    highlights.append(f"Wicket! {batsman} is out for {player_scores[batsman]} runs! Bowled by {bowler}.")
                elif dismissal_type == "caught":
                    bowler = random.choice([b for b in bowling_team if bowler_overs[b] < max_overs_per_bowler])
                    fielder = random.choice(bowling_team)
                    player_wickets[bowler] += 1
                    bowler_overs[bowler] += 1
                    highlights.append(f"Wicket! {batsman} is out for {player_scores[batsman]} runs! Caught by {fielder}. Bowler: {bowler}.")
                elif dismissal_type == "run out":
                    fielder = random.choice(bowling_team)
                    highlights.append(f"Wicket! {batsman} is out for {player_scores[batsman]} runs! Run out by {fielder}.")
                wickets += 1
            else:
                runs_scored = {
                    "dot": 0,
                    "single": 1,
                    "double": 2,
                    "triple": 3,
                    "four": 4,
                    "six": 6
                }[outcome]
                runs += runs_scored
                player_scores[batsman] += runs_scored
                if outcome == "four":
                    highlights.append(f"Four! {batsman} hits a boundary!")
                elif outcome == "six":
                    highlights.append(f"Six! {batsman} hits it out of the park!")
                if player_scores[batsman] >= 50 and player_scores[batsman] < 100:
                    if batsman not in fifty_highlighted:
                        highlights.append(f"50 for {batsman}!")
                        fifty_highlighted.add(batsman)
                elif player_scores[batsman] >= 100:
                    if batsman not in hundred_highlighted:
                        highlights.append(f"100 for {batsman}!")
                        hundred_highlighted.add(batsman)

            if target and runs > target:
                overs_played = balls_bowled // 6 + (balls_bowled % 6) / 10
                return runs, wickets, player_scores, player_wickets, highlights, True, overs_played, balls_faced

    overs_played = balls_bowled // 6 + (balls_bowled % 6) / 10
    return runs, wickets, player_scores, player_wickets, highlights, False, overs_played, balls_faced

def get_top_performers(player_scores, player_wickets, balls_faced):
    top_batsmen = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)[:4]
    top_bowlers = sorted(player_wickets.items(), key=lambda x: x[1], reverse=True)[:4]
    top_batsmen_with_sr = [(player, runs, balls_faced[player], (runs / balls_faced[player]) * 100 if balls_faced[player] > 0 else 0) for player, runs in top_batsmen]
    return top_batsmen_with_sr, top_bowlers

predefined_names = [
    "Sachin Tendulkar", "Virat Kohli", "Ricky Ponting", "Brian Lara", "Jacques Kallis", 
    "Muttiah Muralitharan", "Wasim Akram", "Shane Warne", "MS Dhoni", "Kumar Sangakkara", 
    "AB de Villiers", "Chris Gayle", "Glenn McGrath", "Rahul Dravid", "Allan Border", 
    "Viv Richards", "Sourav Ganguly", "Younis Khan", "Inzamam-ul-Haq", "Anil Kumble", 
    "Steve Waugh", "Mahela Jayawardene", "Graeme Smith", "Hashim Amla", "Adam Gilchrist", 
    "Mitchell Starc", "Ben Stokes", "Joe Root", "James Anderson", "Stuart Broad", 
    "Jasprit Bumrah", "Ravichandran Ashwin", "Babar Azam", "Kane Williamson", "Ross Taylor", 
    "Shaun Pollock", "Michael Clarke", "Andrew Flintoff", "Kevin Pietersen", "Alastair Cook", 
    "Shikhar Dhawan", "Rohit Sharma", "Lasith Malinga", "Faf du Plessis", "Pat Cummins", 
    "David Warner", "Nathan Lyon", "Ravindra Jadeja", "Harbhajan Singh", "Zaheer Khan", 
    "Dale Steyn", "Michael Hussey", "Matthew Hayden", "VVS Laxman", "Mohammad Yousuf", 
    "Mohammad Amir", "Imran Khan", "Kapil Dev", "Sunil Gavaskar", "Javed Miandad", 
    "Clive Lloyd", "Courtney Walsh", "Curtly Ambrose", "Saqlain Mushtaq", "Aravinda de Silva", 
    "Sanath Jayasuriya", "Chaminda Vaas", "Michael Holding", "Dennis Lillee", "Jeff Thomson", 
    "Mark Waugh", "Justin Langer", "Steve Smith", "Mitchell Johnson", "Rangana Herath", 
    "Daniel Vettori", "Brendon McCullum", "Kagiso Rabada", "Shubman Gill", "Rishabh Pant", 
    "Jos Buttler", "Chris Woakes", "Trent Boult", "Tim Southee", "Mohammad Rizwan", 
    "Shakib Al Hasan", "Tamim Iqbal", "Mushfiqur Rahim", "Jason Holder", "Kieron Pollard", 
    "Andre Russell", "Dwayne Bravo", "Shoaib Akhtar", "Waqar Younis", "Morne Morkel", 
    "Albie Morkel", "Paul Collingwood", "Ian Botham", "Richard Hadlee", "Neil Wagner", 
    "Darren Sammy", "Angelo Mathews", "Marnus Labuschagne", "Shivnarine Chanderpaul"
]

async def fill(ctx, exclude_members=[]):
    """
    Pad out empty slots in a new game with default characters.
    """
    # Exclude members already in the list
    available_names = [name for name in predefined_names if name not in exclude_members]
    
    return available_names

@bot.command(aliases=['sim'])
@commands.cooldown(1, 60, commands.BucketType.user)
async def simulate(ctx):
    await ctx.send("Enter the name of Team 1:")
    team1_name = await bot.wait_for('message', check=lambda m: m.author == ctx.author)
    
    await ctx.send(f"Enter the names of the players for {team1_name.content} (comma-separated) or type 'fill' to auto-fill:")
    team1_players = await bot.wait_for('message', check=lambda m: m.author == ctx.author)
    
    if team1_players.content.lower() == 'fill':
        available_members = await fill(ctx)
        if len(available_members) < 11:
            await ctx.send("Not enough members in the predefined list to auto-fill Team 1.")
            return
        team1 = random.sample(available_members, 11)
    else:
        team1 = team1_players.content.split(',')

    await ctx.send("Enter the name of Team 2:")
    team2_name = await bot.wait_for('message', check=lambda m: m.author == ctx.author)
    
    await ctx.send(f"Enter the names of the players for {team2_name.content} (comma-separated) or type 'fill' to auto-fill:")
    team2_players = await bot.wait_for('message', check=lambda m: m.author == ctx.author)
    
    if team2_players.content.lower() == 'fill':
        available_members = await fill(ctx, exclude_members=team1)
        if len(available_members) < 11:
            await ctx.send("Not enough members in the predefined list to auto-fill Team 2.")
            return
        team2 = random.sample(available_members, 11)
    else:
        team2 = team2_players.content.split(',')

    await ctx.send("Select the number of overs per innings (5, 10, 20):")
    overs_message = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content in ['5', '10', '20'])
    overs = int(overs_message.content)
    max_overs_per_bowler = {5: 1, 10: 2, 20: 4}[overs]

    toss_winner = random.choice([team1_name.content, team2_name.content])
    await ctx.send(f"{toss_winner} won the toss and chose to bat first.")

    if toss_winner == team1_name.content:
        batting_team, bowling_team = team1, team2
        batting_team_name, bowling_team_name = team1_name.content, team2_name.content
    else:
        batting_team, bowling_team = team2, team1
        batting_team_name, bowling_team_name = team2_name.content, team1_name.content

    runs1, wickets1, scores1, wickets_taken1, highlights1, _, overs1, balls_faced1 = simulate_innings(batting_team, bowling_team, overs, max_overs_per_bowler)

    await ctx.send("\nFirst Innings Highlights:")
    for highlight in highlights1:
        await ctx.send(highlight)
        await asyncio.sleep(2)

    top_batsmen1, top_bowlers1 = get_top_performers(scores1, wickets_taken1, balls_faced1)

    top_batsmen1_table = tabulate(top_batsmen1, headers=["Player", "Runs", "Balls Faced", "Strike Rate"], tablefmt="grid")
    top_bowlers1_table = tabulate(top_bowlers1, headers=["Player", "Wickets"], tablefmt="grid")

    first_innings_embed = discord.Embed(title="First Innings Summary", color=0x00ff00)
    first_innings_embed.add_field(name=f"Top Batsmen from {batting_team_name}", value=f"```\n{top_batsmen1_table}\n```", inline=False)
    first_innings_embed.add_field(name=f"Top Bowlers from {bowling_team_name}", value=f"```\n{top_bowlers1_table}\n```", inline=False)
    first_innings_embed.add_field(name="Score", value=f"{batting_team_name}: {runs1} runs for {wickets1} wickets in {overs1} overs", inline=False)

    await ctx.send(embed=first_innings_embed)

    await asyncio.sleep(10)

    runs2, wickets2, scores2, wickets_taken2, highlights2, chased, overs2, balls_faced2 = simulate_innings(bowling_team, batting_team, overs, max_overs_per_bowler, target=runs1)

    await ctx.send("\nSecond Innings Highlights:")
    for highlight in highlights2:
        await ctx.send(highlight)
        await asyncio.sleep(2)

    if runs2 > runs1:
        result = f"\n{bowling_team_name} wins by {10 - wickets2} wickets!"
    elif runs1 > runs2:
        result = f"\n{batting_team_name} wins by {runs1 - runs2} runs!"
    else:
        result = "\nThe match is a tie!"

    top_batsmen2, top_bowlers2 = get_top_performers(scores2, wickets_taken2, balls_faced2)

    top_batsmen2_table = tabulate(top_batsmen2, headers=["Player", "Runs", "Balls Faced", "Strike Rate"], tablefmt="grid")
    top_bowlers2_table = tabulate(top_bowlers2, headers=["Player", "Wickets"], tablefmt="grid")

    final_scores = [
        [batting_team_name, runs1, wickets1, overs1],
        [bowling_team_name, runs2, wickets2, overs2]
    ]
    final_scores_table = tabulate(final_scores, headers=["Team", "Runs", "Wickets", "Overs"], tablefmt="grid")

    embed = discord.Embed(title="Cricket Match Simulation", color=0x00ff00)
    embed.add_field(name="Result", value=result, inline=False)
    embed.add_field(name=f"Top Batsmen in innings 1", value=f"```\n{top_batsmen1_table}\n```", inline=False)
    embed.add_field(name=f"Top Bowlers in innings 1", value=f"```\n{top_bowlers1_table}\n```", inline=False)
    embed.add_field(name=f"Top Batsmen in innings 2", value=f"```\n{top_batsmen2_table}\n```", inline=False)
    embed.add_field(name=f"Top Bowlers in innings 2", value=f"```\n{top_bowlers2_table}\n```", inline=False)
    embed.add_field(name="Final Scores", value=f"```\n{final_scores_table}\n```", inline=False)

    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dino(ctx):
    score = 0
    obstacles = ["cactus", "bird"]
    response_time = 8.0  # Start with 8 seconds

    while True:
        obstacle = random.choice(obstacles)
        end_time = discord.utils.utcnow().timestamp() + response_time
        if obstacle == "cactus":
            await ctx.send(f"You're running towards a cactus. You have to respond <t:{int(end_time)}:R> (jump/duck)")
            try:
                response = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ['jump', 'duck'], timeout=response_time)
                if response.content.lower() == 'jump':
                    score += 1
                    if score >= 30:
                        response_time = 1.8  # Set response time to 1.8 second if score reaches 30
                    else:
                        response_time = max(2.0, response_time - 0.5)  # Decrease response time, but not below 2 seconds
                else:
                    break
            except asyncio.TimeoutError:
                break
        elif obstacle == "bird":
            await ctx.send(f"A bird is flying towards you. You have to respond <t:{int(end_time)}:R> (jump/duck)")
            try:
                response = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ['jump', 'duck'], timeout=response_time)
                if response.content.lower() == 'duck':
                    score += 1
                    if score >= 30:
                        response_time = 1.8  # Set response time to 1.8 second if score reaches 30
                    else:
                        response_time = max(2.0, response_time - 0.5)  # Decrease response time, but not below 2 seconds
                else:
                    break
            except asyncio.TimeoutError:
                break

    await ctx.send(f"Game over! Your final score is {score}.")
    update_score(ctx.author.id, str(ctx.author), score, 'dino')

@bot.tree.command(name="dino", description="Play a game of Dino Run")
@app_commands.checks.cooldown(1, 10, key=lambda i:(i.user.id))
async def dino(interaction: discord.Interaction):
    await interaction.response.send_message("**Please use `;dino` to play the game.**\nDue to rate-limit issues /dino has been removed. Sorry for the inconvenience.", ephemeral=True)

def update_score(user_id, username, score, game):
    # Check if the user already has a score for this specific game
    c.execute('SELECT score FROM scores WHERE user_id = ? AND game = ?', (user_id, game))
    result = c.fetchone()

    # Define non-cumulative games
    non_cumulative_games = ['dino', 'flagle']

    if game in non_cumulative_games:
        # For non-cumulative games, only update if the new score is higher than the existing one
        if result is None:
            c.execute('INSERT INTO scores (user_id, username, score, game) VALUES (?, ?, ?, ?)', 
                      (user_id, username, score, game))
        elif score > result[0]:  # Update only if the new score is higher
            c.execute('UPDATE scores SET score = ? WHERE user_id = ? AND game = ?', 
                      (score, user_id, game))
    else:
        # For cumulative games, add the new score to the existing score
        if result is None:
            c.execute('INSERT INTO scores (user_id, username, score, game) VALUES (?, ?, ?, ?)', 
                      (user_id, username, score, game))
        else:
            new_score = result[0] + score
            c.execute('UPDATE scores SET score = ? WHERE user_id = ? AND game = ?', 
                      (new_score, user_id, game))
    
    conn.commit()

@bot.command(aliases=['lb'])
async def leaderboard(ctx, game: str):
    game = game.lower()  # Normalise input for case-insensitivity

    # List of supported games
    supported_games = ['dino', 'flagle', 'wordle', 'fight', 'connect4', 'rockpaperscissors', 'tictactoe']

    if game not in supported_games:
        await ctx.send("Supported leaderboards: dino, flagle, wordle, fight, connect4, rockpaperscissors, tictactoe.")
        return

    # Fetch the top 10 scores for the specified game
    c.execute('SELECT username, score FROM scores WHERE game = ? ORDER BY score DESC LIMIT 10', (game,))
    top_scores = c.fetchall()

    if not top_scores:
        await ctx.send(f"No scores available yet for {game}.")
        return

    # Create leaderboard message
    leaderboard_message = f"**{game.capitalize()} Game Leaderboard**\n"
    for idx, (username, score) in enumerate(top_scores, start=1):
        leaderboard_message += f"{idx}. {username}: {score}\n"

    await ctx.send(leaderboard_message)

@bot.command()
async def profile(ctx):
    user_id = ctx.author.id
    username = str(ctx.author)

    # List of supported games
    supported_games = ['dino', 'flagle', 'wordle', 'fight', 'connect4', 'rockpaperscissors', 'tictactoe']

    # Prepare profile data
    profile_data = []

    for game in supported_games:
        # Fetch the user's score for the game
        c.execute('SELECT score FROM scores WHERE user_id = ? AND game = ?', (user_id, game))
        result = c.fetchone()
        
        if result:
            user_score = result[0]
            
            # Calculate the user's rank for this game
            c.execute('SELECT COUNT(*) + 1 FROM scores WHERE game = ? AND score > ?', (game, user_score))
            rank = c.fetchone()[0]

            # Add the game score and rank to the profile data
            profile_data.append((game.capitalize(), user_score, rank))
        else:
            # If the user has no score in this game, show as "N/A"
            profile_data.append((game.capitalize(), "N/A", "N/A"))

    # Create the profile embed
    embed = discord.Embed(title=f"{username}'s Game Profile", color=discord.Color.random())
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

    for game, score, rank in profile_data:
        embed.add_field(name=game, value=f"Score: {score}\nRank: {rank}", inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def score_summary(ctx):
    # Check if the user is the owner (replace the ID with your actual user ID)
    if ctx.author.id != 678908396845400074:
        await ctx.send("You do not have permission to use this command.")
        return

    # List of supported games
    supported_games = ['dino', 'flagle', 'wordle', 'fight', 'connect4', 'rockpaperscissors', 'tictactoe']

    # Prepare the summary
    summary = "**Total Scores by Game**\n"
    for game in supported_games:
        c.execute('SELECT COUNT(*) FROM scores WHERE game = ?', (game,))
        count = c.fetchone()[0]
        summary += f"{game.capitalize()}: {count} entries\n"

    # Send the summary
    await ctx.send(summary)

class RPSView(View):
    def __init__(self, player, opponent, bot):
        super().__init__(timeout=30.0)  # Set a 30-second timeout for the view
        self.player = player
        self.opponent = opponent
        self.bot = bot
        self.choices = {}

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Allow only the players to interact with the buttons
        return interaction.user.id in [self.player.id, self.opponent.id]

    async def button_callback(self, interaction: Interaction):
        # Register the player's choice
        self.choices[interaction.user.id] = interaction.data['custom_id']
        await interaction.response.send_message(f"{interaction.user.mention} chose {interaction.data['custom_id']}", ephemeral=True)

        # If both players have made their choices, show the result
        if len(self.choices) == 2:
            await self.show_result(interaction)

    async def show_result(self, interaction: Interaction):
        # Retrieve player choices
        player_choice = self.choices.get(self.player.id)
        opponent_choice = self.choices.get(self.opponent.id)

        # Determine and display the result
        result = self.determine_winner(player_choice, opponent_choice)
        result_message = (
            f"{self.player.mention} chose {player_choice}\n"
            f"{self.opponent.mention} chose {opponent_choice}\n"
            f"{result}"
        )
        await interaction.followup.send(result_message)
        self.stop()  # End the game

    def determine_winner(self, player_choice, opponent_choice):
        if player_choice == opponent_choice:
            return "It's a tie!"
        
        winning_conditions = {
            "Rock": "Scissors",
            "Paper": "Rock",
            "Scissors": "Paper"
        }

        if winning_conditions[player_choice] == opponent_choice:
            # Player wins
            update_score(self.player.id, str(self.player), 1, 'rockpaperscissors')
            return f"{self.player.mention} wins!"
        else:
            # Opponent wins
            update_score(self.opponent.id, str(self.opponent), 1, 'rockpaperscissors')
            return f"{self.opponent.mention} wins!"

    async def on_timeout(self):
        # Notify players that the game ended due to inactivity
        channel = await self.bot.fetch_channel(self.player.dm_channel.id if self.player.dm_channel else self.opponent.dm_channel.id)
        await channel.send("Time's up! The Rock-Paper-Scissors game has ended due to inactivity.")
        self.stop()  # Stop the game

@bot.command(aliases=['rps'])
@commands.cooldown(1, 10, commands.BucketType.user)
async def rockpaperscissors(ctx, opponent: discord.Member):
    # Check if the opponent is valid
    if opponent == ctx.author:
        await ctx.send("You cannot play against yourself!")
        return
    if opponent.bot:
        await ctx.send("You cannot play against a bot!")
        return

    # Create and send the Rock-Paper-Scissors game view
    view = RPSView(ctx.author, opponent, bot)
    buttons = [
        Button(label="Rock", custom_id="Rock", style=ButtonStyle.primary),
        Button(label="Paper", custom_id="Paper", style=ButtonStyle.primary),
        Button(label="Scissors", custom_id="Scissors", style=ButtonStyle.primary)
    ]
    for button in buttons:
        button.callback = view.button_callback
        view.add_item(button)

    await ctx.send(f"{ctx.author.mention} vs {opponent.mention}\nChoose your move!", view=view)


@bot.tree.command(name="rockpaperscissors", description="Play a game of Rock-Paper-Scissors")
@app_commands.describe(opponent="The member you want to play against")
@app_commands.checks.cooldown(1, 10, key=lambda i: (i.user.id))
async def rockpaperscissors(interaction: discord.Interaction, opponent: discord.Member):
    # Check if the opponent is valid
    if opponent == interaction.user:
        await interaction.response.send_message("You cannot play against yourself!", ephemeral=True)
        return
    if opponent.bot:
        await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
        return

    # Create and send the Rock-Paper-Scissors game view
    view = RPSView(interaction.user, opponent, bot)
    buttons = [
        Button(label="Rock", custom_id="Rock", style=ButtonStyle.primary),
        Button(label="Paper", custom_id="Paper", style=ButtonStyle.primary),
        Button(label="Scissors", custom_id="Scissors", style=ButtonStyle.primary)
    ]
    for button in buttons:
        button.callback = view.button_callback
        view.add_item(button)

    await interaction.response.send_message(f"{interaction.user.mention} vs {opponent.mention}\nChoose your move!", view=view)

class TicTacToeButton(discord.ui.Button):
    def __init__(self, label, row, col):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.row = row
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user != view.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if view.board[self.row][self.col] != ' ':
            await interaction.response.send_message("This tile is already taken!", ephemeral=True)
            return

        # Update the game board
        view.board[self.row][self.col] = view.current_symbol
        self.label = view.current_symbol
        self.style = discord.ButtonStyle.primary if view.current_symbol == 'X' else discord.ButtonStyle.danger
        self.disabled = True
        await interaction.response.edit_message(view=view)

        # Check for win or draw conditions
        if view.check_winner():
            view.disable_all_buttons()
            await view.message.edit(content=f"{interaction.user.mention} wins! 🎉", view=view)
            update_score(interaction.user.id, str(interaction.user), 1, 'tictactoe')  # Add 1 point for the winner
            view.stop()
            return

        if view.is_draw():
            view.disable_all_buttons()
            await view.message.edit(content="It's a draw! 😐", view=view)
            view.stop()
            return

        # Switch player turn and update the game board message
        view.switch_player()
        await view.message.edit(content=f"It's {view.current_player.mention}'s turn!", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, player1, player2):
        super().__init__(timeout=30.0)  # Set a 30-second timeout
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.current_symbol = 'X'
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.message = None

        # Create a 3x3 grid of TicTacToe buttons
        for row in range(3):
            for col in range(3):
                button = TicTacToeButton(label=f"{chr(65+row)}{col+1}", row=row, col=col)
                self.add_item(button)

    def switch_player(self):
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        self.current_symbol = 'O' if self.current_symbol == 'X' else 'X'

    def check_winner(self):
        for row in self.board:
            if row[0] == row[1] == row[2] != ' ':
                return True
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != ' ':
                return True
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != ' ':
            return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != ' ':
            return True
        return False

    def is_draw(self):
        return all(cell != ' ' for row in self.board for cell in row)

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        if self.message:
            await self.message.channel.send("Time's up! The game has ended due to inactivity.")
        self.stop()

@bot.command(aliases=['ttt'])
@commands.cooldown(1, 20, commands.BucketType.user)
async def tictactoe(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("You cannot play against yourself!")
        return
    if opponent.bot:
        await ctx.send("You cannot play against a bot!")
        return

    view = TicTacToeView(ctx.author, opponent)
    view.message = await ctx.send(f"{ctx.author.mention} vs {opponent.mention}\n{ctx.author.mention}, you're up first!", view=view)

@bot.tree.command(name="tictactoe", description="Play a game of Tic-Tac-Toe")
@app_commands.describe(opponent="The member you want to play against")
@app_commands.checks.cooldown(1, 20, key=lambda i: (i.user.id))
async def tictactoe(interaction: discord.Interaction, opponent: discord.Member):
    if opponent == interaction.user:
        await interaction.response.send_message("You cannot play against yourself!", ephemeral=True)
        return
    if opponent.bot:
        await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
        return

    view = TicTacToeView(interaction.user, opponent)
    await interaction.response.send_message(f"{interaction.user.mention} vs {opponent.mention}\n{interaction.user.mention}, you're up first!", view=view)
    view.message = await interaction.original_response()

words = [
    "apple", "grape", "peach", "berry", "melon", "table", "chair", "sugar", "spoon", "brick", "flame", "baker",
    "drain", "frame", "beach", "dream", "flock", "stone", "storm", "globe", "brave", "brush", "crisp", "grill",
    "froze", "zebra", "quilt", "knock", "flute", "grove", "catch", "rival", "twist", "wrath", "charm", "plant",
    "shiny", "slice", "slime", "blink", "crane", "eagle", "flare", "piano", "laugh", "giant", "water", "clear",
    "grave", "shine", "power", "trail", "river", "solid", "cheek", "sweep", "front", "block", "proud", "bloom",
    "glove", "chase", "jelly", "swift", "trick", "vivid", "sword", "noise", "shock", "craze", "cloud", "trout",
    "bring", "frost", "blame", "point", "prize", "flask", "liver", "dance", "mount", "slide", "raise", "sheet",
    "crush", "paint", "pouch", "lemon", "brace", "fresh", "drink", "queen", "merry", "goose", "bunch", "pitch",
    "check", "grind", "chill", "penny", "press", "shark", "smile", "crown", "boost", "tiger", "feast", "quiet",
    "table", "treat", "bread", "pulse", "sheep", "creek", "spell", "merge", "ghost", "jewel", "blade", "bound",
    "tease", "scale", "flood", "drift", "laugh", "crack", "vault", "prime", "steal", "sheer", "fling", "froth",
    "shine", "shore", "match", "tight", "bliss", "flock", "spear", "grasp", "spare", "blend", "straw", "chief",
    "purse", "fancy", "glide", "doubt", "jumpy", "fuzzy", "crisp", "spike", "grant", "crash", "fetch", "drill",
    "mango", "flour", "raise", "witch", "glass", "front", "grape", "scale", "flame", "slice", "smoke", "brace",
    "glory", "power", "reach", "blaze", "steep", "treat", "glide", "slope", "gloom", "batch", "craze", "creek",
    "waste", "lunch", "cream", "sharp", "swing", "vocal", "spoon", "chant", "reach", "smart", "prize", "grind",
    "charm", "whale", "grape", "bloom", "quilt", "grand", "shock", "lunar", "fluke", "crisp", "twist", "feast",
    "badge", "pride", "shock", "spice", "clock", "piano", "flash", "crane", "grove", "blame", "swift", "pride",
    "pouch", "glove", "steep", "frown", "shoot", "creep", "spill", "crack", "boost", "boast", "globe", "climb",
    "probe", "tough", "flute", "raven", "plant", "tiger", "grill", "slant", "crest", "plane", "stock", "track",
    "whisk", "shock", "stack", "pilot", "drink", "proud", "chase", "flame", "fleet", "drain", "trout", "snack",
    "blush", "quail", "grasp", "frost", "space", "reign", "plume", "throw", "crash", "crawl", "blaze", "choke",
    "drake", "spine", "grind", "trail", "craft", "flock", "tough", "swing", "pouch", "catch", "chill", "piano",
    "quiet", "blend", "merry", "grace", "spike", "twist", "patch", "flute", "pouch", "fluke", "grand", "reach",
    "wrist", "flint", "sharp", "brave", "quiet", "gloom", "fuzzy", "prize", "climb", "drill", "spear", "twist",
    "brisk", "goose", "flock", "prime", "brisk", "tight", "clash", "boost", "brace", "trail", "slime", "pride",
    "stack", "crest", "shine", "fleet", "prime", "storm", "witch", "shock", "sharp", "stage", "grind", "flame",
    "flock", "grill", "grove", "drink", "whale", "jelly", "clash", "proud", "spike", "boost", "whisk", "flour",
    "blame", "blend", "stock", "plane", "flock", "proud", "raven", "stone", "trout", "spike", "shock", "pouch",
    "waste", "tiger", "plant", "drift", "blush", "grant", "flare", "crown", "brisk", "craft", "craze", "swing",
    "drain", "flask", "scale", "track", "crack", "piano", "stage", "choke", "snack", "sharp", "track", "wrist",
    "raven", "creep", "prime", "pouch", "creek", "fleet", "creep", "crest", "grand", "goose", "quilt", "flask",
    "brisk", "blend", "witch", "stack", "probe", "crest", "steep", "creek", "whale", "stack", "proud", "snack",
    "flute", "quilt", "sharp", "tiger", "storm", "stage", "grasp", "spike", "fluke", "shoot", "creep", "spice",
    "brisk", "tough", "stack", "wrist", "storm", "glove", "creep", "flash", "stage", "chill", "stock", "brave",
    "flask", "flame", "crawl", "drain", "quilt", "blend", "chill", "plant", "craft", "whale", "glove", "stack",
    "stone", "proud", "plane", "plant", "spike", "craze", "prime", "flame", "grill", "wrist", "flute", "pouch",
    "flock", "prime", "craft", "shock", "wrist", "gloom", "fluke", "blend", "flame", "drain", "fluke", "stage",
    "twist", "drain", "track", "flame", "shock", "drake", "spine", "stack", "flask", "prime", "whisk", "craft",
    "whale", "stone", "wrist", "creep", "stage", "spine", "shock", "prime", "piano", "stock", "proud", "flock",
    "brave", "craft", "prime", "sharp", "stage", "tiger", "flask", "boost", "prime", "proud", "stage", "drake",
    "pouch", "proud", "plant", "crest", "drain", "flock", "prime", "flask", "gloom", "whale", "blend", "prime",
    "boost", "prime", "craft", "wrist", "proud", "brave", "stage", "boost", "flask", "flock", "prime", "stage",
    "prime", "whisk", "stack", "flask", "prime", "prime", "craft", "prime", "wrist", "stage", "craft", "sharp",
    "prime", "prime", "whale", "flask", "prime", "prime", "brave", "prime", "craft", "aback", "abase", "abate", 
    "abbey", "abbot", "abhor", "abide", "abled", "abode", "abort", "about", "above", 
    "abuse", "abyss", "acorn", "acrid", "actor", "acute", "adage", "adapt", "adept", "admin", "admit", "adobe", 
    "adopt", "adore", "adorn", "adult", "affix", "afire", "afoot", "afoul", "after", "again", "agape", "agate", 
    "agent", "agile", "aging", "aglow", "agony", "agree", "ahead", "aider", "aisle", "alarm", "album", "alert", 
    "algae", "alibi", "alien", "align", "alike", "alive", "allay", "alley", "allot", "allow", "alloy", "aloft", 
    "alone", "along", "aloof", "aloud", "alpha", "altar", "alter", "amass", "amaze", "amber", "amend", "amiss", 
    "amity", "among", "ample", "amuse", "angel", "anger", "angle", "angry", "angst", "anime", "ankle", "annex", 
    "annoy", "annul", "anode", "antic", "anvil", "aorta", "apart", "apple", "apply", "apron", "aptly", "arbor", 
    "arche", "ardor", "arena", "argue", "arise", "armor", "aroma", "arose", "array", "arrow", "arson", "artsy", 
    "ascot", "ashen", "aside", "askew", "assay", "asset", "atoll", "atone", "attic", "audio", "audit", "augur", 
    "aunty", "avail", "avert", "avian", "avoid", "await", "awake", "award", "aware", "awash", "awful", "awoke", 
    "axial", "axiom", "axion", "azure", "bacon", "badge", "badly", "bagel", "baggy", "baker", "baldy", "balmy", 
    "banal", "banjo", "barge", "baron", "basal", "basic", "basil", "basin", "basis", "baste", "batch", "bathe", 
    "baton", "batty", "bawdy", "bayou", "beach", "beady", "beard", "beast", "beech", "beefy", "befit", "began", 
    "begat", "beget", "begin", "begun", "being", "belch", "belie", "belle", "belly", "below", "bench", "beret", 
    "berry", "berth", "beset", "betel", "bevel", "bezel", "bible", "bicep", "biddy", "bigot", "bilge", "billy", 
    "binge", "bingo", "biome", "birch", "birth", "bison", "bitty", "black", "blade", "blame", "bland", "blank", 
    "blare", "blast", "blaze", "bleak", "bleat", "bleed", "blend", "bless", "blimp", "blind", "blink", "bloat", 
    "block", "bloke", "blond", "blood", "bloom", "blown", "bluer", "bluff", "blunt", "blurb", "blurt", "blush", 
    "board", "boast", "bobby", "boney", "bongo", "bonus", "booby", "boost", "booth", "booty", "booze", "boozy", 
    "borax", "borne", "bosom", "bossy", "botch", "bough", "boule", "bound", "bowel", "boxer", "brace", "braid", 
    "brain", "brake", "brand", "brash", "brass", "brave", "bravo", "brawl", "brawn", "bread", "break", "breed", 
    "briar", "bribe", "brick", "bride", "brief", "brine", "bring", "brink", "briny", "brisk", "broad", "broil", 
    "broke", "brood", "brook", "broom", "broth", "brown", "brunt", "brush", "brute", "buddy", "budge", "buggy", 
    "bugle", "build", "built", "bulge", "bulky", "bully", "bumpy", "bunch", "bunny", "burly", "burnt", "burst", 
    "bused", "bushy", "butch", "butte", "buxom", "buyer", "bylaw", "cabin", "cable", "cacao", "cache", "caddy", 
    "cadet", "cagey", "cairn", "camel", "cameo", "canal", "candy", "canny", "canoe", "canon", "caper", "caput", 
    "carat", "cargo", "carol", "carry", "carve", "caste", "catch", "cater", "catty", "caulk", "cause", "cavil", 
    "cease", "cedar", "cello", "chafe", "chaff", "chain", "chair", "chalk", "champ", "chant", "chaos", "chard", 
    "charm", "chart", "chase", "chasm", "cheap", "cheat", "check", "cheek", "cheer", "chess", "chest", "chick", 
    "chide", "chief", "child", "chili", "chill", "chime", "china", "chirp", "chock", "choir", "choke", "chomp", 
    "chord", "chore", "chose", "chuck", "chump", "chunk", "churn", "chute", "cider", "cigar", "cinch", "circa", 
    "civic", "civil", "clack", "claim", "clamp", "clang", "clank", "clash", "clasp", "class", "clean", "clear", 
    "cleat", "cleft", "clerk", "click", "cliff", "climb", "cling", "clink", "cloak", "clock", "clone", "close", 
    "cloth", "cloud", "clout", "clove", "clown", "cluck", "clued", "clump", "clung", "coach", "coast", "cobra", 
    "cocky", "cocoa", "colon", "color", "comet", "comfy", "comic", "comma", "conch", "condo", "conic", "copse", 
    "coral", "corer", "corny", "couch", "cough", "could", "count", "coupe", "court", "coven", "cover", "covet", 
    "covey", "cower", "cowry", "coyly", "crack", "craft", "cramp", "crane", "crank", "crash", "crass", "crate", 
    "crave", "crawl", "craze", "crazy", "creak", "cream", "credo", "creed", "creek", "creep", "creme", "crepe", 
    "crept", "cress", "crest", "crick", "cried", "crier", "crime", "crimp", "crisp", "croak", "crock", "crone", 
    "crony", "crook", "cross", "croup", "crowd", "crown", "crude", "cruel", "crumb", "crump", "crush", "crust", 
    "crypt", "cubic", "cumin", "curio", "curly", "curry", "curse", "curve", "curvy", "cutie", "cyber", "cycle", 
    "cynic", "daddy", "daily", "dairy", "daisy", "dally", "dance", "dandy", "datum", "daunt", "dealt", "death", 
    "debar", "debit", "debug", "debut", "decal", "decay", "decor", "decoy", "decry", "defer", "deify", "deign", 
    "deity", "delay", "delta", "delve", "demon", "demur", "denim", "dense", "depot", "depth", "derby", "deter", 
    "detox", "deuce", "devil", "diary", "dicey", "digit", "dilly", "dimly", "dingo", "dingy", "diode", "dirge", 
    "dirty", "disco", "ditch", "ditto", "ditty", "diver", "dizzy", "dodge", "dodgy", "dogma", "doing", "dolly", 
    "donor", "donut", "dopey", "doubt", "dough", "dowdy", "dowel", "downy", "dowry", "dozen", "draft", "drain", 
    "drake", "drama", "drank", "drape", "drawl", "drawn", "dread", "dream", "dress", "dried", "drier", "drift", 
    "drill", "drink", "drive", "droid", "drone", "drool", "droop", "dross", "drove", "drown", "druid", "drunk", 
    "dryly", "duchy", "dully", "dummy", "dumpy", "dunce", "dusky", "dusty", "dutch", "duvet", "dwarf", "dwell", 
    "dwelt", "dying", "eager", "eagle", "early", "earth", "easel", "eaten", "eater", "ebony", "eclat", "edict", 
    "edify", "eerie", "egret", "eight", "eject", "eking", "elate", "elbow", "elder", "elect", "elegy", "elfin", 
    "elide", "elite", "elope", "elude", "email", "embed", "ember", "emcee", "empty", "enact", "endow", "enema", 
    "enemy", "enjoy", "ennui", "ensue", "enter", "entry", "envoy", "epoch", "epoxy", "equal", "equip", "erase", 
    "erect", "erode", "error", "erupt", "essay", "ester", "ethic", "ethos", "etude", "evade", "evict", "evoke", 
    "exact", "exalt", "excel", "exert", "exile", "exist", "expel", "extol", "extra", "exult", "eying", "fable", 
    "facet", "faint", "fairy", "faith", "false", "fancy", "fanny", "farce", "fatal", "fatty", "fault", "fauna", 
    "favor", "feast", "fecal", "feign", "fella", "felon", "femur", "fence", "feral", "ferry", "fetal", "fetch", 
    "fetid", "fetus", "fever", "fewer", "fiber", "fibre", "ficus", "field", "fiend", "fiery", "fifth", "fifty", 
    "fight", "filer", "filet", "filly", "filmy", "filth", "final", "finch", "finis", "first", "fishy", "fixer", 
    "fizzy", "fjord", "flack", "flail", "flair", "flake", "flaky", "flame", "flank", "flare", "flash", "flask", 
    "fleck", "fleet", "flesh", "flick", "flier", "fling", "flint", "flirt", "float", "flock", "flood", "floor", 
    "flora", "floss", "flour", "flout", "flown", "fluff", "fluid", "fluke", "flume", "flung", "flunk", "flush", 
    "flute", "flyer", "foamy", "focal", "focus", "foggy", "foist", "folio", "folly", "foray", "force", "forge", 
    "forgo", "forte", "forth", "forty", "forum", "found", "foyer", "frail", "frame", "frank", "fraud", "freak", 
    "freed", "freer", "fresh", "friar", "fried", "frill", "frisk", "fritz", "frock", "frond", "front", "frost", 
    "froth", "frown", "froze", "fruit", "fudge", "fuels", "fugal", "fully", "fungi", "funky", "funny", "furor", 
    "furry", "fussy", "fuzzy", "gaffe", "gaily", "gamer", "gamma", "gamut", "gassy", "gaudy", "gauge", "gaunt", 
    "gauze", "gavel", "gawky", "gayer", "gayly", "gazer", "gears", "gecko", "geeky", "geese", "genie", "genoa", 
    "genre", "ghost", "ghoul", "giant", "giddy", "gipsy", "girly", "girth", "given", "giver", "glade", "gland", 
    "glare", "glass", "glaze", "gleam", "glean", "glide", "glint", "gloat", "globe", "gloom", "glory", "gloss", 
    "glove", "glyph", "gnash", "gnome", "godly", "going", "golem", "golly", "gonad", "goner", "goofy", "goose", 
    "gorge", "gouge", "gourd", "grace", "grade", "graft", "grail", "grain", "grand", "grant", "grape", "graph", 
    "grasp", "grass", "grate", "grave", "gravy", "graze", "great", "greed", "green", "greet", "grief", "grill", 
    "grime", "grimy", "grind", "gripe", "groan", "groin", "groom", "grope", "gross", "group", "grout", "grove", 
    "growl", "grown", "gruel", "gruff", "grunt", "guard", "guava", "guess", "guest", "guide", "guild", "guile", 
    "guilt", "gully", "gumbo", "gummy", "guppy", "gusto", "gusty", "gypsy", "habit", "hairy", "halve", "handy", 
    "happy", "hardy", "harem", "harpy", "harry", "harsh", "haste", "hasty", "hatch", "hater", "haunt", "haute", 
    "haven", "havoc", "hazel", "heady", "heard", "heart", "heath", "heave", "heavy", "hedge", "hefty", "heist", 
    "helix", "hello", "hence", "heron", "hilly", "hinge", "hippo", "hippy", "hitch", "hoard", "hobby", "hoist", 
    "holly", "homer", "honey", "honor", "horde", "horny", "horse", "hotel", "hotly", "hound", "house", "hovel", 
    "hover", "howdy", "human", "humid", "humor", "humph", "humus", "hunch", "hunky", "hurry", "husky", "hussy", 
    "hydro", "hyena", "hymen", "hyper", "icily", "icing", "ideal", "idiom", "idiot", "idler", "idyll", "igloo", 
    "iliac", "image", "imbue", "impel", "imply", "inane", "inbox", "incur", "index", "inept", "inert", "infer", 
    "ingot", "inlay", "inlet", "inner", "input", "inter", "intro", "ionic", "irate", "irony", "islet", "issue", 
    "itchy", "ivory", "jaded", "jaggy", "jaunt", "jazzy", "jelly", "jerky", "jetty", "jiffy", "joint", "joist", 
    "joker", "jolly", "joust", "judge", "juice", "juicy", "jumbo", "jumpy", "junta", "junto", "juror", "kappa", 
    "karma", "kayak", "kebab", "khaki", "kinky", "kiosk", "kitty", "knack", "knave", "knead", "kneed", "kneel", 
    "knelt", "knife", "knock", "knoll", "known", "koala", "krill", "label", "labor", "laden", "ladle", "lager", 
    "lance", "lanky", "lapel", "lapse", "large", "larva", "lasso", "latch", "later", "lathe", "latte", "laugh", 
    "layer", "leach", "leafy", "leaky", "leant", "leapt", "learn", "lease", "leash", "least", "leave", "ledge", 
    "leech", "leery", "lefty", "legal", "leggy", "lemon", "lemur", "leper", "level", "lever", "libel", "liege", 
    "light", "liken", "lilac", "limbo", "limit", "linen", "liner", "lingo", "lipid", "lithe", "liver", "livid", 
    "llama", "loamy", "loath", "lobby", "local", "locus", "lodge", "lofty", "logic", "login", "loopy", "loose", 
    "lorry", "loser", "louse", "lousy", "lover", "lower", "lowly", "loyal", "lucid", "lucky", "lunar", "lunch", 
    "lunge", "lupus", "lurch", "lurid", "lusty", "lying", "lymph", "lynch", "lyric", "macaw", "macho", "macro", 
    "madam", "madly", "mafia", "magic", "magma", "maize", "major", "maker", "mambo", "mamma", "mammy", "manly", 
    "manor", "maple", "march", "marry", "marsh", "mason", "masse", "match", "matey", "matte", "maxim", "maybe", 
    "mayor", "mealy", "meant", "meaty", "mecca", "medal", "media", "medic", "melee", "melon", "mercy", "merge", 
    "merit", "merry", "metal", "meter", "metro", "micro", "midge", "midst", "mighty", "mince", "miner", "minge",
    "motto", "mould", "movie", "mulch", "music", "muted", "nacho", "nasty", "noble", "noisy", "notch", "oasis",
    "opium", "paint", "quasi", "ranch", "react", "smoke", "spine", "table", "thumb", "urban", "vague", "waste",
    "woven", "yield", "young", "zonal"
    ]

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def wordle(ctx):
    word = random.choice(words)
    attempts = 6
    guessed = False
    display = "- " * 5

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and len(m.content) == 5

    await ctx.send(f"Guess the word! {display}")

    while attempts > 0 and not guessed:
        try:
            guess = await bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send(f"Time's up! You didn't guess the word in time. The word was: {word}")
            return

        guess_content = guess.content.lower()

        if guess_content == word:
            guessed = True
            await ctx.send(f"Congratulations! You guessed the word: {word}")
            update_score(ctx.author.id, str(ctx.author), 1, 'wordle')  # Add 1 point on win
            return

        feedback = ""
        used_letters = set()
        for i in range(5):
            if guess_content[i] == word[i]:
                feedback += f"{guess_content[i]} "
                used_letters.add(guess_content[i])
            elif guess_content[i] in word and guess_content[i] not in used_letters:
                feedback += f"({guess_content[i]}) "
                used_letters.add(guess_content[i])
            else:
                feedback += "- "

        attempts -= 1
        await ctx.send(f"Guess: {guess.content}\nFeedback: {feedback}\nAttempts left: {attempts}")

    if not guessed:
        await ctx.send(f"Sorry, you've run out of attempts! The word was: {word}")

@bot.tree.command(name="wordle", description="Play a game of Wordle")
@app_commands.checks.cooldown(1, 10, key=lambda i:(i.user.id))
async def wordle(interaction: discord.Interaction):
    await interaction.response.send_message("**Please use `;wordle` to play the game.**\nDue to rate-limit issues /wordle has been removed. Sorry for the inconvenience.", ephemeral=True)

@bot.command(aliases=['math', 'maths'])
@commands.cooldown(1, 10, commands.BucketType.user)
async def mathematics(ctx, quiz_type: str):
    if quiz_type not in ['addition', 'subtraction', 'multiplication', 'division']:
        await ctx.send("Invalid quiz type! Please choose from addition, subtraction, multiplication, or division.")
        return

    score = 0
    difficulty = 1
    response_time = 10.0  # Start with 10 seconds

    while True:
        if quiz_type == 'addition':
            a, b = random.randint(1, 10 * difficulty), random.randint(1, 10 * difficulty)
            question = f"{a} + {b}"
            answer = a + b
        elif quiz_type == 'subtraction':
            a, b = random.randint(1, 10 * difficulty), random.randint(1, 10 * difficulty)
            question = f"{a} - {b}"
            answer = a - b
        elif quiz_type == 'multiplication':
            a, b = random.randint(1, 5 * difficulty), random.randint(1, 5 * difficulty)
            question = f"{a} * {b}"
            answer = a * b
        elif quiz_type == 'division':
            b = random.randint(1, 5 * difficulty)
            a = b * random.randint(1, 5 * difficulty)  # Ensure a is divisible by b
            question = f"{a} / {b}"
            answer = round(a / b, 2)  # Round to 2 decimal places

        end_time = discord.utils.utcnow().timestamp() + response_time
        await ctx.send(f"Solve: {question}\nYou have to answer <t:{int(end_time)}:R>.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            guess = await bot.wait_for('message', check=check, timeout=response_time)
            if quiz_type == 'division':
                try:
                    if abs(float(guess.content) - answer) < 0.01:  # Allow a small margin of error
                        score += 1
                        difficulty += 1
                        response_time = max(5.0, response_time - 1.0)  # Decrease response time but not below 5 seconds
                        await ctx.send("Correct!")
                    else:
                        await ctx.send(f"Wrong! The correct answer was {answer}. Your score is {score}")
                        break
                except ValueError:
                    await ctx.send(f"Invalid input! The correct answer was {answer}. Your score is {score}")
                    break
            else:
                if int(guess.content) == answer:
                    score += 1
                    difficulty += 1
                    response_time = max(5.0, response_time - 1.0)  # Decrease response time but not below 5 seconds
                    await ctx.send("Correct!")
                else:
                    await ctx.send(f"Wrong! The correct answer was {answer}. Your score is {score}")
                    break
        except asyncio.TimeoutError:
            await ctx.send(f"Time's up! The correct answer was {answer}. Your score is {score}")
            break
 

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def flagle(ctx):
    score = 0
    response_time = 10.0  # 10 seconds to answer

    embed = discord.Embed(title="Flagle Game", color=discord.Color.blue())
    message = await ctx.send(embed=embed)

    while True:
        country_code = random.choice(['AF', 'AL', 'DZ', 'AD', 'AO', 'AG', 'AR', 'AM', 'AU', 'AT', 'AZ', 'BS', 'BH', 'BD', 'BB', 'BY', 'BE', 'BZ', 'BJ', 
    'BT', 'BO', 'BA', 'BW', 'BR', 'BN', 'BG', 'BF', 'BI', 'CV', 'KH', 'CM', 'CA', 'CF', 'TD', 'CL', 'CN', 'CO', 'KM', 
    'CG', 'CD', 'CR', 'CI', 'HR', 'CU', 'CY', 'CZ', 'DK', 'DJ', 'DM', 'DO', 'EC', 'EG', 'SV', 'GQ', 'ER', 'EE', 'SZ', 
    'ET', 'FJ', 'FI', 'FR', 'GA', 'GM', 'GE', 'DE', 'GH', 'GR', 'GD', 'GT', 'GN', 'GW', 'GY', 'HT', 'HN', 'HU', 'IS', 
    'IN', 'ID', 'IR', 'IQ', 'IE', 'IL', 'IT', 'JM', 'JP', 'JO', 'KZ', 'KE', 'KI', 'KP', 'KR', 'KW', 'KG', 'LA', 'LV', 
    'LB', 'LS', 'LR', 'LY', 'LI', 'LT', 'LU', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MH', 'MR', 'MU', 'MX', 'FM', 'MD', 
    'MC', 'MN', 'ME', 'MA', 'MZ', 'MM', 'NA', 'NR', 'NP', 'NL', 'NZ', 'NI', 'NE', 'NG', 'NO', 'OM', 'PK', 'PW', 'PA', 
    'PG', 'PY', 'PE', 'PH', 'PL', 'PT', 'QA', 'RO', 'RU', 'RW', 'KN', 'LC', 'VC', 'WS', 'SM', 'ST', 'SA', 'SN', 'RS', 
    'SC', 'SL', 'SG', 'SK', 'SI', 'SB', 'SO', 'ZA', 'SS', 'ES', 'LK', 'SD', 'SR', 'SE', 'CH', 'SY', 'TW', 'TJ', 'TZ', 
    'TH', 'TL', 'TG', 'TO', 'TT', 'TN', 'TR', 'TM', 'TV', 'UG', 'UA', 'AE', 'GB', 'US', 'UY', 'UZ', 'VU', 'VE', 'VN', 
    'YE', 'ZM', 'ZW'])
        country_name = {
            'AF': 'Afghanistan', 'AL': 'Albania', 'DZ': 'Algeria', 'AD': 'Andorra', 'AO': 'Angola', 'AG': 'Antigua and Barbuda', 
    'AR': 'Argentina', 'AM': 'Armenia', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan', 'BS': 'Bahamas', 'BH': 'Bahrain', 
    'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus', 'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BT': 'Bhutan', 
    'BO': 'Bolivia', 'BA': 'Bosnia and Herzegovina', 'BW': 'Botswana', 'BR': 'Brazil', 'BN': 'Brunei', 'BG': 'Bulgaria', 
    'BF': 'Burkina Faso', 'BI': 'Burundi', 'CV': 'Cabo Verde', 'KH': 'Cambodia', 'CM': 'Cameroon', 'CA': 'Canada', 
    'CF': 'Central African Republic', 'TD': 'Chad', 'CL': 'Chile', 'CN': 'China', 'CO': 'Colombia', 'KM': 'Comoros', 
    'CG': 'Congo', 'CD': 'Congo (Democratic Republic)', 'CR': 'Costa Rica', 'CI': 'Côte d\'Ivoire', 'HR': 'Croatia', 
    'CU': 'Cuba', 'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'DJ': 'Djibouti', 'DM': 'Dominica', 
    'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador', 'GQ': 'Equatorial Guinea', 
    'ER': 'Eritrea', 'EE': 'Estonia', 'SZ': 'Eswatini', 'ET': 'Ethiopia', 'FJ': 'Fiji', 'FI': 'Finland', 'FR': 'France', 
    'GA': 'Gabon', 'GM': 'Gambia', 'GE': 'Georgia', 'DE': 'Germany', 'GH': 'Ghana', 'GR': 'Greece', 'GD': 'Grenada', 
    'GT': 'Guatemala', 'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti', 'HN': 'Honduras', 'HU': 'Hungary', 
    'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia', 'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland', 'IL': 'Israel', 
    'IT': 'Italy', 'JM': 'Jamaica', 'JP': 'Japan', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya', 'KI': 'Kiribati', 
    'KP': 'North Korea', 'KR': 'South Korea', 'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': 'Laos', 'LV': 'Latvia', 
    'LB': 'Lebanon', 'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libya', 'LI': 'Liechtenstein', 'LT': 'Lithuania', 
    'LU': 'Luxembourg', 'MG': 'Madagascar', 'MW': 'Malawi', 'MY': 'Malaysia', 'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 
    'MH': 'Marshall Islands', 'MR': 'Mauritania', 'MU': 'Mauritius', 'MX': 'Mexico', 'FM': 'Micronesia', 'MD': 'Moldova', 
    'MC': 'Monaco', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MA': 'Morocco', 'MZ': 'Mozambique', 'MM': 'Myanmar', 'NA': 'Namibia', 
    'NR': 'Nauru', 'NP': 'Nepal', 'NL': 'Netherlands', 'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger', 'NG': 'Nigeria', 
    'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan', 'PW': 'Palau', 'PA': 'Panama', 'PG': 'Papua New Guinea', 'PY': 'Paraguay', 
    'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland', 'PT': 'Portugal', 'QA': 'Qatar', 'RO': 'Romania', 'RU': 'Russia', 
    'RW': 'Rwanda', 'KN': 'Saint Kitts and Nevis', 'LC': 'Saint Lucia', 'VC': 'Saint Vincent and the Grenadines', 
    'WS': 'Samoa', 'SM': 'San Marino', 'ST': 'Sao Tome and Principe', 'SA': 'Saudi Arabia', 'SN': 'Senegal', 'RS': 'Serbia', 
    'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore', 'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands', 
    'SO': 'Somalia', 'ZA': 'South Africa', 'SS': 'South Sudan', 'ES': 'Spain', 'LK': 'Sri Lanka', 'SD': 'Sudan', 'SR': 'Suriname', 
    'SE': 'Sweden', 'CH': 'Switzerland', 'SY': 'Syria', 'TW': 'Taiwan', 'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand', 
    'TL': 'Timor-Leste', 'TG': 'Togo', 'TO': 'Tonga', 'TT': 'Trinidad and Tobago', 'TN': 'Tunisia', 'TR': 'Turkey', 
    'TM': 'Turkmenistan', 'TV': 'Tuvalu', 'UG': 'Uganda', 'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom', 
    'US': 'United States', 'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VE': 'Venezuela', 'VN': 'Vietnam', 
    'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
        }[country_code]
        flag_url = f"https://flagsapi.com/{country_code}/flat/64.png"
        end_time = discord.utils.utcnow().timestamp() + response_time

        # Update the embed with the flag, timer, and prompt
        embed.clear_fields()
        embed.description = (
            f"Guess the country for this flag:\n[Flag Image]({flag_url})\n"
            f"You have until <t:{int(end_time)}:R> to respond."
        )
        embed.set_image(url=flag_url)
        await message.edit(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            guess = await bot.wait_for('message', check=check, timeout=response_time)
            if guess.content.strip().lower() == country_name.lower():
                score += 1
                feedback = "Correct!"
            else:
                feedback = f"Wrong! The correct answer was **{country_name}**. Your final score: {score}"
                await ctx.send(feedback)
                break
            embed.clear_fields()
            embed.add_field(name="Result", value=feedback, inline=False)
            embed.add_field(name="Score", value=str(score), inline=True)
            await message.edit(embed=embed)
        except asyncio.TimeoutError:
            await ctx.send(f"Time's up! The correct answer was **{country_name}**. Your final score: {score}")
            break

    update_score(ctx.author.id, str(ctx.author), score, 'flagle')

@bot.tree.command(name="flagle", description="Guess the country based on its flag")
@app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
async def flagle(interaction: discord.Interaction):
    score = 0
    response_time = 10.0  # 10 seconds to answer

    embed = discord.Embed(title="Flagle Game", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()

    while True:
        country_code = random.choice(['AF', 'AL', 'DZ', 'AD', 'AO', 'AG', 'AR', 'AM', 'AU', 'AT', 'AZ', 'BS', 'BH', 'BD', 'BB', 'BY', 'BE', 'BZ', 'BJ', 
    'BT', 'BO', 'BA', 'BW', 'BR', 'BN', 'BG', 'BF', 'BI', 'CV', 'KH', 'CM', 'CA', 'CF', 'TD', 'CL', 'CN', 'CO', 'KM', 
    'CG', 'CD', 'CR', 'CI', 'HR', 'CU', 'CY', 'CZ', 'DK', 'DJ', 'DM', 'DO', 'EC', 'EG', 'SV', 'GQ', 'ER', 'EE', 'SZ', 
    'ET', 'FJ', 'FI', 'FR', 'GA', 'GM', 'GE', 'DE', 'GH', 'GR', 'GD', 'GT', 'GN', 'GW', 'GY', 'HT', 'HN', 'HU', 'IS', 
    'IN', 'ID', 'IR', 'IQ', 'IE', 'IL', 'IT', 'JM', 'JP', 'JO', 'KZ', 'KE', 'KI', 'KP', 'KR', 'KW', 'KG', 'LA', 'LV', 
    'LB', 'LS', 'LR', 'LY', 'LI', 'LT', 'LU', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MH', 'MR', 'MU', 'MX', 'FM', 'MD', 
    'MC', 'MN', 'ME', 'MA', 'MZ', 'MM', 'NA', 'NR', 'NP', 'NL', 'NZ', 'NI', 'NE', 'NG', 'NO', 'OM', 'PK', 'PW', 'PA', 
    'PG', 'PY', 'PE', 'PH', 'PL', 'PT', 'QA', 'RO', 'RU', 'RW', 'KN', 'LC', 'VC', 'WS', 'SM', 'ST', 'SA', 'SN', 'RS', 
    'SC', 'SL', 'SG', 'SK', 'SI', 'SB', 'SO', 'ZA', 'SS', 'ES', 'LK', 'SD', 'SR', 'SE', 'CH', 'SY', 'TW', 'TJ', 'TZ', 
    'TH', 'TL', 'TG', 'TO', 'TT', 'TN', 'TR', 'TM', 'TV', 'UG', 'UA', 'AE', 'GB', 'US', 'UY', 'UZ', 'VU', 'VE', 'VN', 
    'YE', 'ZM', 'ZW'])
        country_name = {
            'AF': 'Afghanistan', 'AL': 'Albania', 'DZ': 'Algeria', 'AD': 'Andorra', 'AO': 'Angola', 'AG': 'Antigua and Barbuda', 
    'AR': 'Argentina', 'AM': 'Armenia', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan', 'BS': 'Bahamas', 'BH': 'Bahrain', 
    'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus', 'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BT': 'Bhutan', 
    'BO': 'Bolivia', 'BA': 'Bosnia and Herzegovina', 'BW': 'Botswana', 'BR': 'Brazil', 'BN': 'Brunei', 'BG': 'Bulgaria', 
    'BF': 'Burkina Faso', 'BI': 'Burundi', 'CV': 'Cabo Verde', 'KH': 'Cambodia', 'CM': 'Cameroon', 'CA': 'Canada', 
    'CF': 'Central African Republic', 'TD': 'Chad', 'CL': 'Chile', 'CN': 'China', 'CO': 'Colombia', 'KM': 'Comoros', 
    'CG': 'Congo', 'CD': 'Congo (Democratic Republic)', 'CR': 'Costa Rica', 'CI': 'Côte d\'Ivoire', 'HR': 'Croatia', 
    'CU': 'Cuba', 'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'DJ': 'Djibouti', 'DM': 'Dominica', 
    'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador', 'GQ': 'Equatorial Guinea', 
    'ER': 'Eritrea', 'EE': 'Estonia', 'SZ': 'Eswatini', 'ET': 'Ethiopia', 'FJ': 'Fiji', 'FI': 'Finland', 'FR': 'France', 
    'GA': 'Gabon', 'GM': 'Gambia', 'GE': 'Georgia', 'DE': 'Germany', 'GH': 'Ghana', 'GR': 'Greece', 'GD': 'Grenada', 
    'GT': 'Guatemala', 'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti', 'HN': 'Honduras', 'HU': 'Hungary', 
    'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia', 'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland', 'IL': 'Israel', 
    'IT': 'Italy', 'JM': 'Jamaica', 'JP': 'Japan', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya', 'KI': 'Kiribati', 
    'KP': 'North Korea', 'KR': 'South Korea', 'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': 'Laos', 'LV': 'Latvia', 
    'LB': 'Lebanon', 'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libya', 'LI': 'Liechtenstein', 'LT': 'Lithuania', 
    'LU': 'Luxembourg', 'MG': 'Madagascar', 'MW': 'Malawi', 'MY': 'Malaysia', 'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 
    'MH': 'Marshall Islands', 'MR': 'Mauritania', 'MU': 'Mauritius', 'MX': 'Mexico', 'FM': 'Micronesia', 'MD': 'Moldova', 
    'MC': 'Monaco', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MA': 'Morocco', 'MZ': 'Mozambique', 'MM': 'Myanmar', 'NA': 'Namibia', 
    'NR': 'Nauru', 'NP': 'Nepal', 'NL': 'Netherlands', 'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger', 'NG': 'Nigeria', 
    'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan', 'PW': 'Palau', 'PA': 'Panama', 'PG': 'Papua New Guinea', 'PY': 'Paraguay', 
    'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland', 'PT': 'Portugal', 'QA': 'Qatar', 'RO': 'Romania', 'RU': 'Russia', 
    'RW': 'Rwanda', 'KN': 'Saint Kitts and Nevis', 'LC': 'Saint Lucia', 'VC': 'Saint Vincent and the Grenadines', 
    'WS': 'Samoa', 'SM': 'San Marino', 'ST': 'Sao Tome and Principe', 'SA': 'Saudi Arabia', 'SN': 'Senegal', 'RS': 'Serbia', 
    'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore', 'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands', 
    'SO': 'Somalia', 'ZA': 'South Africa', 'SS': 'South Sudan', 'ES': 'Spain', 'LK': 'Sri Lanka', 'SD': 'Sudan', 'SR': 'Suriname', 
    'SE': 'Sweden', 'CH': 'Switzerland', 'SY': 'Syria', 'TW': 'Taiwan', 'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand', 
    'TL': 'Timor-Leste', 'TG': 'Togo', 'TO': 'Tonga', 'TT': 'Trinidad and Tobago', 'TN': 'Tunisia', 'TR': 'Turkey', 
    'TM': 'Turkmenistan', 'TV': 'Tuvalu', 'UG': 'Uganda', 'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom', 
    'US': 'United States', 'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VE': 'Venezuela', 'VN': 'Vietnam', 
    'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
        }[country_code]
        flag_url = f"https://flagsapi.com/{country_code}/flat/64.png"
        end_time = discord.utils.utcnow().timestamp() + response_time

        # Update the embed with the flag, timer, and prompt
        embed.clear_fields()
        embed.description = (
            f"Guess the country for this flag:\n[Flag Image]({flag_url})\n"
            f"You have until <t:{int(end_time)}:R> to respond."
        )
        embed.set_image(url=flag_url)
        await message.edit(embed=embed)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            guess = await bot.wait_for('message', check=check, timeout=response_time)
            if guess.content.strip().lower() == country_name.lower():
                score += 1
                feedback = "Correct!"
            else:
                feedback = f"Wrong! The correct answer was **{country_name}**. Your final score: {score}"
                await interaction.followup.send(feedback)
                break
            embed.clear_fields()
            embed.add_field(name="Result", value=feedback, inline=False)
            embed.add_field(name="Score", value=str(score), inline=True)
            await message.edit(embed=embed)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"Time's up! The correct answer was **{country_name}**. Your final score: {score}")
            break

    update_score(interaction.user.id, str(interaction.user), score, 'flagle')

class BlackjackButton(Button):
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
            if view.calculate_hand(view.player_hand) > 21:
                await view.end_game(interaction, "You busted! Dealer wins.")
                return
        elif self.action == "stay":
            while view.calculate_hand(view.dealer_hand) < 17:
                view.dealer_hand.append(view.draw_card())
            dealer_score = view.calculate_hand(view.dealer_hand)
            player_score = view.calculate_hand(view.player_hand)
            if dealer_score > 21 or player_score > dealer_score:
                await view.end_game(interaction, "You win!")
            elif player_score < dealer_score:
                await view.end_game(interaction, "Dealer wins.")
            else:
                await view.end_game(interaction, "It's a tie.")
            return

        await view.update_message(interaction)

class BlackjackView(View):
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.deck = self.create_deck()
        self.player_hand = [self.draw_card(), self.draw_card()]
        self.dealer_hand = [self.draw_card(), self.draw_card()]
        self.add_item(BlackjackButton(label="Hit", style=discord.ButtonStyle.primary, action="hit"))
        self.add_item(BlackjackButton(label="Stay", style=discord.ButtonStyle.secondary, action="stay"))

    def create_deck(self):
        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(deck)
        return deck

    def draw_card(self):
        return self.deck.pop()

    def calculate_hand(self, hand):
        total = sum(hand)
        aces = hand.count(11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    async def update_message(self, interaction):
        player_score = self.calculate_hand(self.player_hand)
        dealer_score = self.calculate_hand(self.dealer_hand[:1])
        embed = discord.Embed(title="Blackjack", color=discord.Color.green())
        embed.add_field(name="Your Hand", value=f"{self.player_hand} (Score: {player_score})", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand[:1]} [?] (Score: {dealer_score}?)", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    async def end_game(self, interaction, result):
        player_score = self.calculate_hand(self.player_hand)
        dealer_score = self.calculate_hand(self.dealer_hand)
        
        if "you win" in result.lower():
            color = 0x00ff00  # Green for user win
        elif "dealer wins" in result.lower() or "busted" in result.lower():
            color = 0xff0000  # Red for dealer win or user busted
        elif "tie" in result.lower():
            color = 0x808080  # Gray for tie
        else:
            color = 0xff0000  # Default to red for any other case

        embed = discord.Embed(title="Blackjack", color=color)
        embed.add_field(name="Your Hand", value=f"{self.player_hand} (Score: {player_score})", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand} (Score: {dealer_score})", inline=False)
        embed.add_field(name="Result", value=result, inline=False)
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(aliases=['bj'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def blackjack(ctx):
    view = BlackjackView(ctx.author)
    embed = discord.Embed(title="Blackjack", color=discord.Color.green())
    player_score = view.calculate_hand(view.player_hand)
    dealer_score = view.calculate_hand(view.dealer_hand[:1])
    embed.add_field(name="Your Hand", value=f"{view.player_hand} (Score: {player_score})", inline=False)
    embed.add_field(name="Dealer's Hand", value=f"{view.dealer_hand[:1]} [?] (Score: {dealer_score}?)", inline=False)
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="blackjack", description="Play a game of Blackjack against the bot")
@app_commands.checks.cooldown(1, 5, key=lambda i:(i.user.id))
async def blackjack(interaction: discord.Interaction):
    view = BlackjackView(interaction.user)
    embed = discord.Embed(title="Blackjack", color=discord.Color.green())
    player_score = view.calculate_hand(view.player_hand)
    dealer_score = view.calculate_hand(view.dealer_hand[:1])
    embed.add_field(name="Your Hand", value=f"{view.player_hand} (Score: {player_score})", inline=False)
    embed.add_field(name="Dealer's Hand", value=f"{view.dealer_hand[:1]} [?] (Score: {dealer_score}?)", inline=False)
    await interaction.response.send_message(embed=embed, view=view)

@bot.command(aliases=['def'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def define(ctx, *, word: str):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    response = requests.get(url)
    
    if response.status_code != 200:
        await ctx.send(f"No definition found for '{word}'.")
        return

    data = response.json()
    if not data or 'title' in data:
        await ctx.send(f"No definition found for '{word}'.")
        return

    # Create an embed message with the definitions
    embed = discord.Embed(title=f"Definition of {word}", color=0x7289da)
    for meaning in data[0]['meanings']:
        part_of_speech = meaning['partOfSpeech']
        definitions = [definition['definition'] for definition in meaning['definitions']]
        definitions_text = '\n'.join(definitions)
        
        # Truncate if the definitions text is too long
        if len(definitions_text) > 1024:
            definitions_text = definitions_text[:1021] + '...'
        
        embed.add_field(name=part_of_speech, value=definitions_text, inline=False)
        embed.set_footer(text=f"🤓")
    
    await ctx.send(embed=embed)

CRIC_API_KEY = 'cc606201-1050-492e-ac30-e638468ddc69'  # Replace with your CricAPI key

@bot.command(aliases=['lc', 'live'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def livecricket(ctx):
    url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}&offset=0"
    response = requests.get(url)
    
    if response.status_code != 200:
        await ctx.send("Could not fetch live cricket scores. Please try again later.")
        return

    data = response.json()
    matches = data.get('data', [])
    
    if not matches:
        await ctx.send("No live matches found.")
        return

    embed = discord.Embed(title="Live Cricket Scores", color=0x11806a)
    
    for match in matches:
        if match.get('matchStarted') and not match.get('matchEnded'):
            team1 = match['teams'][0]
            team2 = match['teams'][1]
            score = "\n".join([f"{s['inning']}: {s['r']}/{s['w']} in {s['o']} overs" for s in match.get('score', [])])
            status = match.get('status', 'Status not available')
            embed.add_field(name=f"{team1} vs {team2}", value=f"Score:\n{score}\nStatus: {status}", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(aliases=['urban'])
@commands.cooldown(1, 5, commands.BucketType.user)
async def urbandictionary(ctx, *, term: str):
    url = f"https://api.urbandictionary.com/v0/define?term={term}"
    response = requests.get(url)
    
    if response.status_code != 200:
        await ctx.send(f"No definition found for '{term}'.")
        return

    data = response.json()
    if not data or not data['list']:
        await ctx.send(f"No definition found for '{term}'.")
        return

    embed = discord.Embed(title=f"Urban Dictionary: {term}", color=0x7289da)
    for i, definition in enumerate(data['list'][:5], 1):
        def_text = definition['definition']
        example_text = definition['example']
    
        if len(def_text) > 1024:
            def_text = def_text[:1021] + '...'
        if len(example_text) > 1024:
            example_text = example_text[:1021] + '...'
    
        embed.add_field(name=f"Definition {i}", value=def_text, inline=False)
        embed.add_field(name="Example", value=example_text, inline=False)
        embed.set_footer(text="If this shows something offensive, it's not my fault. Blame Urban Dictionary.")

    await ctx.send(embed=embed)

@bot.command(aliases=['8ball'])
async def _8ball(ctx, *, question):
    responses = [
        discord.Embed(title="Absolutely, but only if you dance first.", color = discord.Colour.random(),),
        discord.Embed(title="It's a yes, but I'd double-check with a cat.", color = discord.Colour.random()),
        discord.Embed(title="No doubt... unless you're born in October.", color = discord.Colour.random()),
        discord.Embed(title="Perchance.", color = discord.Colour.random()),
        discord.Embed(title="Yeah, sure. Why not?", color = discord.Colour.random()),
        discord.Embed(title="Most likely, but don't quote me on that.", color = discord.Colour.random()),
        discord.Embed(title="Outlook good, but I've been wrong before.", color = discord.Colour.random()),
        discord.Embed(title="Yes, but only if you bring snacks.", color = discord.Colour.random()),
        discord.Embed(title="SIUUUU", color = discord.Colour.random()),
        discord.Embed(title="Ask me later, I'm watching the Talk Tuah podcast.", color = discord.Colour.random()),
        discord.Embed(title="Hmm... I forgot. Ask again.", color = discord.Colour.random()),
        discord.Embed(title="Better not. Trust me, it's for your own good.", color = discord.Colour.random()),
        discord.Embed(title="I could tell you, but then I'd have to delete you.", color = discord.Colour.random()),
        discord.Embed(title="Cannot predict now... I need coffee first.", color = discord.Colour.random()),
        discord.Embed(title="Focus... and maybe stop scrolling Instagram reels.", color = discord.Colour.random()),
        discord.Embed(title="Don't count on it. Seriously, don't.", color = discord.Colour.random()),
        discord.Embed(title="Nope. My magic 8-ball says nah.", color = discord.Colour.random()),
        discord.Embed(title="My sources? They say no. And they're rarely wrong.", color = discord.Colour.random()),
        discord.Embed(title="Outlook not so good... Did you try rebooting?", color = discord.Colour.random()),
        discord.Embed(title="Very doubtful, but I love your optimism!", color = discord.Colour.random())
    ]
    
    response = random.choice(responses)
    await ctx.send(content=f'**Question:** {question}\n**Answer:**', embed=response)

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(question="The question you want to ask the magic 8-ball")
async def _8ball(interaction: discord.Interaction, question: str):
    responses = [
        discord.Embed(title="Absolutely, but only if you dance first.", color=discord.Colour.random()),
        discord.Embed(title="It's a yes, but I'd double-check with a cat.", color=discord.Colour.random()),
        discord.Embed(title="No doubt... unless you're born in October.", color=discord.Colour.random()),
        discord.Embed(title="Perchance.", color=discord.Colour.random()),
        discord.Embed(title="Yeah, sure. Why not?", color=discord.Colour.random()),
        discord.Embed(title="Most likely, but don't quote me on that.", color=discord.Colour.random()),
        discord.Embed(title="Outlook good, but I've been wrong before.", color=discord.Colour.random()),
        discord.Embed(title="Yes, but only if you bring snacks.", color=discord.Colour.random()),
        discord.Embed(title="SIUUUU", color=discord.Colour.random()),
        discord.Embed(title="Ask me later, I'm watching the Talk Tuah podcast.", color=discord.Colour.random()),
        discord.Embed(title="Hmm... I forgot. Ask again.", color=discord.Colour.random()),
        discord.Embed(title="Better not. Trust me, it's for your own good.", color=discord.Colour.random()),
        discord.Embed(title="I could tell you, but then I'd have to delete you.", color=discord.Colour.random()),
        discord.Embed(title="Cannot predict now... I need coffee first.", color=discord.Colour.random()),
        discord.Embed(title="Focus... and maybe stop scrolling Instagram reels.", color=discord.Colour.random()),
        discord.Embed(title="Don't count on it. Seriously, don't.", color=discord.Colour.random()),
        discord.Embed(title="Nope. My magic 8-ball says nah.", color=discord.Colour.random()),
        discord.Embed(title="My sources? They say no. And they're rarely wrong.", color=discord.Colour.random()),
        discord.Embed(title="Outlook not so good... Did you try rebooting?", color=discord.Colour.random()),
        discord.Embed(title="Very doubtful, but I love your optimism!", color=discord.Colour.random())
    ]
    
    response = random.choice(responses)
    await interaction.response.send_message(content=f'**Question:** {question}\n**Answer:**', embed=response)

@bot.command(aliases=['play'])
@commands.cooldown(1, 30, commands.BucketType.user)
async def playcricket(ctx):
    user_score = 0
    bot_score = 0
    options = [1, 2, 3, 4, 6]

    await ctx.send("First Half: You are batting. Type a number (1, 2, 3, 4, 6) to play your shot.")

    # First Half: User is batting
    while True:
        try:
            user_message = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and int(m.content) in options, timeout=30.0)
            user_choice = int(user_message.content)
            bot_choice = random.choice(options)
            await ctx.send(f"You chose {user_choice}, Bot chose {bot_choice}")

            if user_choice == bot_choice:
                await ctx.send(f"Out! Your score: {user_score}")
                break
            else:
                user_score += user_choice
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Game over.")
            return

    await ctx.send("Second Half: Bot is batting. Type a number (1, 2, 3, 4, 6) to bowl.")

    # Second Half: Bot is batting
    while bot_score <= user_score:
        try:
            user_message = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and int(m.content) in options, timeout=30.0)
            user_choice = int(user_message.content)
            bot_choice = random.choice(options)
            await ctx.send(f"You chose {user_choice}, Bot chose {bot_choice}")

            if user_choice == bot_choice:
                await ctx.send(f"Out! Bot's score: {bot_score}")
                break
            else:
                bot_score += bot_choice
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Game over.")
            return

    # Determine the result
    if bot_score > user_score:
        result_message = f"Bot wins!\n**Final scores**\nYou: {user_score}\nBot: {bot_score}"
    else:
        result_message = f"You win!\n**Final scores**\nYou: {user_score}\nBot: {bot_score}"

    await ctx.send(result_message)

@bot.tree.command(name="playcricket", description="Play a game of classic hand cricket")
@app_commands.checks.cooldown(1, 30, key=lambda i:(i.user.id))
async def playcricket(interaction: discord.Interaction):
    await interaction.response.send_message("**Please use `;playcricket` to play this game.**\nDue to rate-limit issues /playcricket has been removed. Sorry for the inconvenience.", ephemeral=True)

truth_questions = [
    "What is your biggest fear?",
    "What is your most embarrassing moment?",
    "Have you ever lied to your best friend?",
    "What is the biggest secret you've kept from your parents?",
    "What is your guilty pleasure?",
    "Have you ever broken someone's trust?",
    "What’s the most awkward date you’ve ever been on?",
    "Who is the last person you stalked on social media?",
    "What’s the worst lie you’ve ever told?",
    "If you had to delete one social media app forever, which one would it be?",
    "What’s your worst habit?",
    "What’s the most childish thing you still do?",
    "What’s the weirdest food you’ve ever eaten?",
    "Who was your first crush?",
    "What’s the biggest mistake you’ve ever made in a relationship?",
    "Have you ever cheated on a test?",
    "What’s something you’ve done that you still feel guilty about?",
    "What’s the meanest thing you’ve ever said to someone?",
    "Have you ever been in love?",
    "What is the most spontaneous thing you’ve ever done?",
    "What is your biggest insecurity?",
    "Have you ever had a crush on a teacher?",
    "What’s the weirdest dream you’ve ever had?",
    "What’s the longest you’ve ever gone without showering?",
    "Have you ever pretended to like something just to fit in?",
    "Have you ever had a wardrobe malfunction in public?",
    "If you could change one thing about your body, what would it be?",
    "What’s a secret you’ve never told anyone?",
    "Who is your celebrity crush?",
    "Have you ever spread a rumor?",
    "What’s something you wish you could tell your younger self?",
    "What’s the most expensive thing you’ve ever stolen?",
    "Have you ever been caught cheating on anything?",
    "If you could swap lives with someone for a day, who would it be?",
    "What’s the most embarrassing thing you’ve said or done in front of a crush?",
    "Have you ever been caught lying?",
    "What’s the longest lie you’ve ever kept going?",
    "If you could erase one memory, what would it be?",
    "Do you have any strange phobias?",
    "What’s the worst thing you’ve ever done to someone to get back at them?",
    "Have you ever lied to get out of trouble?",
    "What is something you’re proud of but would never post online?",
    "Have you ever been caught doing something embarrassing in public?",
    "What’s the most embarrassing thing in your search history?",
    "Have you ever cried during a movie? If so, which one?",
    "What’s the most childish thing you still do?",
    "Have you ever been in trouble with the law?",
    "What’s the worst thing you’ve ever eaten just to be polite?",
    "Have you ever ghosted someone?",
    "What’s the weirdest thing you’ve done when you were alone?",
    "Who in this room would you switch lives with for a day?",
    "Have you ever pretended to be sick to get out of something?",
    "What’s something you’ve never told anyone?",
    "What is something you’ve done that you wish you could undo?",
    "Have you ever broken the law?",
    "What’s the most embarrassing thing you’ve posted on social media?",
    "If you had to give up one of your five senses, which would it be?",
    "What’s a secret you’ve kept from your best friend?",
    "What’s your worst breakup story?",
    "If you had to delete one friend from your life, who would it be?",
    "Have you ever kissed someone you didn’t like?",
    "What’s the grossest thing you’ve ever done?",
    "What’s your guilty pleasure TV show?",
    "What’s the longest you’ve gone without brushing your teeth?",
    "What’s the most ridiculous thing you’ve been in trouble for?",
    "Have you ever been jealous of a friend?",
    "If you could only eat one food for the rest of your life, what would it be?",
    "Who’s the person you regret dating the most?",
    "Have you ever lied about your age?",
    "What’s the weirdest thing you’ve ever said to a stranger?",
    "What’s the strangest talent you have?",
    "Have you ever blamed someone else for something you did?",
    "What’s the most embarrassing nickname you’ve ever had?",
    "Have you ever lied to your parents?",
    "What’s the most embarrassing thing that’s ever happened to you?",
    "Have you ever been caught sneaking out?",
    "If you could be any fictional character, who would you be?",
    "Have you ever pretended to be someone else?",
    "What’s something you’ve done that would shock your parents?",
    "What’s your least favorite thing about yourself?",
    "What’s the dumbest thing you’ve done to impress someone?",
    "Have you ever lied to get something you wanted?",
    "Who is the last person you lied to?",
    "What’s the meanest thing you’ve ever done?",
    "Have you ever had a crush on a friend’s sibling?",
    "What’s something you’re embarrassed to admit you like?",
    "Have you ever lied in this game?",
    "What’s the most embarrassing picture of you?",
    "Have you ever broken a bone? If so, how?",
    "Have you ever stolen anything from a friend?",
    "What’s the worst date you’ve ever been on?",
    "Have you ever kissed someone you weren’t supposed to?",
    "What’s the last lie you told?",
    "Have you ever embarrassed yourself in front of a crush?",
    "If you could change one thing about your personality, what would it be?",
    "Have you ever had a crush on someone you shouldn’t have?",
    "What’s the worst trouble you’ve ever gotten into?",
    "What’s the most embarrassing thing you’ve ever worn?",
    "Have you ever accidentally said “I love you” to someone?",
    "Have you ever been caught doing something you weren’t supposed to?",
    "Have you ever kissed someone and regretted it?",
    "What’s the silliest fear you have?",
    "What’s the most awkward conversation you’ve ever had?",
    "What’s the last thing you searched for on your phone?",
    "Have you ever been caught eavesdropping?",
    "What’s the dumbest lie you’ve ever told?",
    "What’s your biggest regret?",
    "What’s the weirdest habit you have?",
    "What’s something you’re really bad at but wish you were good at?",
    "What’s the last thing you do before going to bed?",
    "Have you ever lied to get out of a date?",
    "What’s the weirdest dream you’ve ever had?",
    "What’s the grossest thing you’ve ever done?",
    "What’s the most embarrassing thing that’s ever happened to you?",
    "Have you ever been rejected?",
    "Have you ever accidentally sent a text to the wrong person?",
    "What’s the most awkward thing you’ve ever overheard?",
    "What’s the most embarrassing thing you’ve done while drunk?",
    "Have you ever been caught talking about someone behind their back?",
    "Have you ever lied about where you were?",
    "What’s something you wish you hadn’t done?",
    "What’s the most embarrassing thing you’ve done in front of a crowd?",
    "Have you ever been jealous of a friend?",
    "What’s the worst gift you’ve ever received?",
    "Have you ever been caught sneaking out?",
    "What’s something you’ve done that you wish you could take back?",
    "Have you ever lied to avoid hanging out with someone?",
    "What’s the weirdest thing you’ve ever eaten?",
    "What’s something you’ve done that you hope no one ever finds out?",
    "Have you ever accidentally insulted someone?",
    "What’s the worst thing you’ve ever said to someone?",
    "What’s the biggest risk you’ve ever taken?",
    "What’s the dumbest thing you’ve ever done in front of a crowd?",
    "Have you ever been caught lying?",
    "What’s something you’ve done that you’d never tell your parents about?",
    "What’s the most embarrassing thing you’ve ever done at a party?",
    "Have you ever lied in this game?",
    "What’s the worst job you’ve ever had?",
    "What’s the weirdest thing you’ve ever done to impress someone?",
    "Have you ever faked being sick?",
    "What’s the most embarrassing thing you’ve ever worn?",
    "Have you ever been caught in a lie?",
    "What’s the worst date you’ve ever been on?",
    "What’s the weirdest talent you have?",
    "What’s the strangest thing you’ve ever done for love?",
    "Have you ever had a crush on a teacher?",
    "What’s the most awkward thing you’ve done on a date?",
    "What’s the dumbest thing you’ve done to impress someone?",
    "What’s the weirdest thing you’ve done in your sleep?",
    "Have you ever pretended to like someone just to be nice?",
    "What’s the strangest thing you’ve ever done to make money?",
    "What’s the most embarrassing thing you’ve done at a wedding?",
    "What’s the most awkward thing you’ve ever said to someone?",
    "What’s something you’ve done that you wish no one knew about?",
    "Have you ever been caught doing something embarrassing in public?",
    "What’s the most embarrassing thing you’ve done to impress someone?",
    "What’s the weirdest thing you’ve ever done in front of a mirror?",
    "What’s the worst thing you’ve ever said in a job interview?",
    "What’s the most awkward thing you’ve ever done at a party?",
    "What’s the weirdest thing you’ve ever done to get someone’s attention?",
    "What’s the most awkward thing you’ve done in front of a crush?",
    "What’s the weirdest thing you’ve ever done in public?",
    "What’s the most embarrassing thing you’ve ever posted online?",
    "What’s the weirdest thing you’ve ever done to avoid someone?",
    "What’s the most awkward thing you’ve done in front of a stranger?",
    "What’s the dumbest thing you’ve done on a dare?",
    "What’s the weirdest thing you’ve ever done on social media?",
    "What’s the most embarrassing thing you’ve ever done in school?",
    "What’s the strangest thing you’ve ever done to make someone laugh?",
    "What’s the most awkward thing you’ve done at work?",
    "What’s the weirdest thing you’ve ever done to make someone like you?",
    "What’s the most awkward thing you’ve ever done at a family gathering?",
    "What’s the weirdest thing you’ve ever done to impress a friend?",
    "What’s the most embarrassing thing you’ve done at a family event?",
    "What’s the strangest thing you’ve ever done to avoid someone’s attention?",
    "What’s the most awkward thing you’ve done in front of a family member?",
    "What’s the most embarrassing thing you’ve ever said to a stranger?",
    "What’s the weirdest thing you’ve ever done in public just to see what would happen?"
]

dare_questions = [
    "Do 20 pushups.",
    "Sing a song chosen by the group.",
    "Let someone write a word on your forehead with a marker.",
    "Eat a spoonful of mustard.",
    "Imitate a celebrity until someone can guess who you are.",
    "Do a dance without any music for 2 minutes.",
    "Wear your socks on your hands for the next 10 minutes.",
    "Speak in a British accent for the next 5 turns.",
    "Let someone give you a new hairstyle.",
    "Wear a blindfold and let someone feed you a mystery food.",
    "Do your best impression of a famous person.",
    "Hold your breath for as long as you can.",
    "Spin around 10 times and try to walk in a straight line.",
    "Post an embarrassing photo on social media.",
    "Let the person next to you text anyone from your phone.",
    "Try to juggle three items of the group’s choosing.",
    "Do an impression of someone in the room until someone guesses who you are.",
    "Try to lick your elbow.",
    "Do your best chicken dance outside on the street.",
    "Let someone else redo your hair in a crazy style.",
    "Do the worm dance.",
    "Run around the outside of the house three times.",
    "Talk in a high-pitched voice for the next 10 minutes.",
    "Do 10 squats while holding something over your head.",
    "Hold an ice cube in your hand until it melts.",
    "Let someone draw on your face with a pen.",
    "Go outside and yell as loud as you can.",
    "Let the person next to you redo your makeup.",
    "Do 30 jumping jacks.",
    "Try to drink a glass of water while standing on your head.",
    "Hold your breath for 20 seconds.",
    "Speak in a robot voice for the next 5 minutes.",
    "Pretend to be a waiter and take snack orders from everyone in the room.",
    "Do the moonwalk across the room.",
    "Try to make the group laugh as quickly as possible.",
    "Walk across the room with your eyes closed.",
    "Give the person to your left a piggyback ride.",
    "Imitate a celebrity chosen by the group.",
    "Let someone tickle you for 30 seconds.",
    "Do 20 sit-ups.",
    "Imitate your favorite animal for 1 minute.",
    "Talk without opening your mouth for the next 3 rounds.",
    "Let someone pour ice water down your shirt.",
    "Balance a spoon on your nose for 10 seconds.",
    "Jump on one leg for the next three rounds.",
    "Imitate a superhero of the group’s choosing.",
    "Do a cartwheel.",
    "Speak in an accent for the next 10 minutes.",
    "Do 15 pushups in a row.",
    "Wear your shoes on your hands for the next five minutes.",
    "Let someone choose your profile picture on social media.",
    "Post the first picture in your phone gallery to social media.",
    "Dance with no music for 1 minute.",
    "Try to do a split.",
    "Let someone prank call one of your friends.",
    "Walk backward everywhere you go for the next 10 minutes.",
    "Do 25 jumping jacks.",
    "Hold a plank for one minute.",
    "Let someone give you a new nickname and call you that for the rest of the game.",
    "Talk like a baby for the next 5 minutes.",
    "Eat a raw onion slice.",
    "Let someone paint your nails any color they want.",
    "Eat a spoonful of hot sauce.",
    "Pretend to be a statue for the next 3 minutes.",
    "Do your best breakdance moves.",
    "Do your best celebrity impression for 2 minutes.",
    "Pretend you are swimming underwater for the next 2 minutes.",
    "Wear socks on your hands until your next turn.",
    "Do your best opera singing.",
    "Talk in a whisper for the next 5 rounds.",
    "Pretend to be a monkey for the next 3 minutes.",
    "Sing everything you say for the next 10 minutes.",
    "Speak in a pirate voice for the next 5 rounds.",
    "Let someone else redo your makeup.",
    "Try to balance a book on your head for 1 minute.",
    "Hop on one foot until your next turn.",
    "Let the person to your right tickle you for 20 seconds.",
    "Let the group give you a new hairstyle.",
    "Let the group pick a song for you to sing.",
    "Pretend to be the person to your right for the next 3 minutes.",
    "Sing a nursery rhyme in a dramatic voice.",
    "Do your best robot dance.",
    "Try to juggle three random objects.",
    "Eat a spoonful of hot sauce.",
    "Let someone blindfold you and feed you something.",
    "Do 20 jumping jacks in 1 minute.",
    "Walk on your knees until your next turn.",
    "Do your best animal impersonation for 2 minutes.",
    "Let someone tickle you for 20 seconds.",
    "Let someone draw on your arm with a pen.",
    "Act like a cat for the next 2 minutes.",
    "Do the floss dance for 30 seconds.",
    "Do your best model walk.",
    "Do 10 pushups in a row.",
    "Pretend to be a robot for the next 5 rounds.",
    "Talk in a different accent for the next 5 minutes.",
    "Eat a raw garlic clove.",
    "Pretend to be a chicken for the next 2 minutes.",
    "Try to do 20 pushups.",
    "Try to spin a hula hoop for 1 minute.",
    "Let someone tickle you for 15 seconds.",
    "Let the group give you a new hairstyle.",
    "Try to balance a spoon on your nose for 30 seconds.",
    "Imitate a famous person for the next 5 minutes.",
    "Do 20 squats while singing.",
    "Try to do a handstand.",
    "Do 30 jumping jacks in 1 minute.",
    "Do your best ballet moves.",
    "Talk like a robot for the next 5 minutes.",
    "Act like a monkey until your next turn.",
    "Do a silly dance for 30 seconds.",
    "Walk backward everywhere you go for the next 5 minutes.",
    "Let someone prank call a friend of yours.",
    "Eat a spoonful of mustard.",
    "Imitate a celebrity until someone can guess who you are.",
    "Hold an ice cube until it melts.",
    "Let the person next to you text anyone from your phone.",
    "Try to juggle three objects for 30 seconds.",
    "Do your best impression of a celebrity.",
    "Balance a spoon on your nose for 10 seconds.",
    "Do the moonwalk across the room.",
    "Let someone prank call one of your friends.",
    "Do a dance without any music for 2 minutes.",
    "Wear your socks on your hands for the next 10 minutes.",
    "Imitate a celebrity until someone can guess who you are.",
    "Try to drink a glass of water while standing on your head.",
    "Speak in a pirate accent for the next 10 minutes.",
    "Walk like a crab until your next turn.",
    "Let the group make a funny video of you and post it online.",
    "Try to do a cartwheel.",
    "Hold your breath for as long as you can.",
    "Spin around 10 times and try to walk in a straight line.",
    "Let the group come up with a nickname for you and call you that for the next 3 rounds.",
    "Try to lick your elbow.",
    "Do a freestyle rap about your day.",
    "Imitate a famous person until someone guesses who you are.",
    "Let someone draw on your face with a marker.",
    "Try to do a split.",
    "Pretend to be the person to your left for the next 5 minutes.",
    "Walk on your knees until your next turn.",
    "Wear your shoes on your hands for the next 10 minutes.",
    "Let the group pick a new hairstyle for you.",
    "Do a handstand or try to do one.",
    "Speak in a robot voice for the next 5 minutes.",
    "Try to walk on your knees until your next turn.",
    "Let the group tickle you for 30 seconds.",
    "Post an embarrassing photo of yourself on social media.",
    "Let someone blindfold you and feed you something.",
    "Try to drink a glass of water without using your hands.",
    "Post the first photo in your camera roll on social media.",
    "Pretend to be a waiter and take snack orders from everyone in the room.",
    "Imitate your favorite cartoon character.",
    "Talk in a high-pitched voice for the next 5 minutes.",
    "Do your best impression of a celebrity."
]

class NextButton(Button):
    def __init__(self):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.send_random_question(interaction)

class TruthOrDareView(View):
    def __init__(self):
        super().__init__(timeout=120)  # 2 minutes timeout
        self.add_item(NextButton())

    async def send_random_question(self, interaction: discord.Interaction):
        question_type = random.choice(["truth", "dare"])
        if question_type == "truth":
            question = random.choice(truth_questions)
        else:
            question = random.choice(dare_questions)

        embed = discord.Embed(title="Truth or Dare", description=question, color=discord.Color.random())
        embed.set_footer(text=f"Type: {question_type.capitalize()}")
        await interaction.response.send_message(embed=embed, view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

@bot.command(aliases=['tod'])
@commands.cooldown(1, 30, commands.BucketType.user)
async def truthordare(ctx):
    view = TruthOrDareView()
    question_type = random.choice(["truth", "dare"])
    if question_type == "truth":
        question = random.choice(truth_questions)
    else:
        question = random.choice(dare_questions)

    embed = discord.Embed(title="Truth or Dare", description=question, color=discord.Color.random())
    embed.set_footer(text=f"Type: {question_type.capitalize()}")
    view.message = await ctx.send(embed=embed, view=view)

@bot.tree.command(name="truthordare", description="Play a game of Truth or Dare")
@app_commands.checks.cooldown(1, 30, key=lambda i:(i.user.id))
async def truthordare(interaction: discord.Interaction):
    view = TruthOrDareView()
    question_type = random.choice(["truth", "dare"])
    if question_type == "truth":
        question = random.choice(truth_questions)
    else:
        question = random.choice(dare_questions)

    embed = discord.Embed(title="Truth or Dare", description=question, color=discord.Color.random())
    embed.set_footer(text=f"Type: {question_type.capitalize()}")
    view.message = await interaction.response.send_message(embed=embed, view=view)

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def race(ctx, opponent: discord.Member):
    embedinstruction = discord.Embed(title="Instructions", description="Type the words in `backticks` as fast as you can!", color=discord.Color.red())
    await ctx.send(embed=embedinstruction)
    countdown_message = await ctx.send(f"Get ready to race {ctx.author.mention} and {opponent.mention}! (5 seconds)")
    for i in range(5, 0, -1):
        await countdown_message.edit(content=f"Get ready to race {ctx.author.mention} and {opponent.mention}! ({i} seconds)")
        await asyncio.sleep(1)
    await ctx.send("The race has started! `Go`!")

    start_time = discord.utils.utcnow()
    user1_responses = 0
    user2_responses = 0

    def check(m):
        return m.channel == ctx.channel and m.author in [ctx.author, opponent]

    # Track "go" responses
    try:
        response = await bot.wait_for('message', timeout=5.0, check=check)
        if response.content.lower() == "go":
            if response.author == ctx.author:
                user1_responses += 1
            else:
                user2_responses += 1
    except asyncio.TimeoutError:
        pass

    events = [
        ("There's a `right` turn coming up!", "right"),
        ("There's a `left` turn coming up!", "left"),
        ("Your opponent is catching up to you! `Accelerate` right now!", "accelerate")
    ]

    for i in range(5):
        await asyncio.sleep(5)
        event, correct_response = random.choice(events)
        await ctx.send(event)
        try:
            response = await bot.wait_for('message', timeout=3.0, check=check)
            if response.content.lower() == correct_response:
                if response.author == ctx.author:
                    user1_responses += 1
                else:
                    user2_responses += 1
        except asyncio.TimeoutError:
            continue

    await ctx.send("It's the final stretch! `Speed up` to win the race!")
    try:
        response = await bot.wait_for('message', timeout=5.0, check=check)
        if response.content.lower() == "speed up":
            if response.author == ctx.author:
                user1_responses += 1
            else:
                user2_responses += 1
    except asyncio.TimeoutError:
        pass

    await asyncio.sleep(5)

    if user1_responses > user2_responses:
        winner = ctx.author
    elif user2_responses > user1_responses:
        winner = opponent
    else:
        winner = None

    result_embed = discord.Embed(title="Race Results", color=discord.Color.random())
    if winner:
        result_embed.add_field(name="Winner", value=winner.mention)
    else:
        result_embed.add_field(name="Result", value="It's a tie!")
    result_embed.add_field(name=f"{ctx.author.display_name}'s Responses", value=str(user1_responses))
    result_embed.add_field(name=f"{opponent.display_name}'s Responses", value=str(user2_responses))

    await ctx.send(embed=result_embed)

start_time = datetime.datetime.now(datetime.timezone.utc)

@bot.command(aliases=['info', 'bot'])
async def botinfo(ctx):
    # Calculate the bot's uptime
    current_time = datetime.datetime.now(datetime.timezone.utc)
    uptime = current_time - start_time
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds

    # Get the number of servers and total number of users
    num_servers = len(bot.guilds)
    num_shards = len(bot.shards)

    # Create the embed
    embed = discord.Embed(title="Bot Information", color=discord.Color.dark_embed())
    embed.set_thumbnail(url=bot.user.avatar)
    embed.add_field(name="Servers and Shards", value=f"{num_servers} Servers, {num_shards} Shards", inline=True)
    embed.add_field(name="Bot Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Invite Link", value="[Invite the Bot](https://discord.com/oauth2/authorize?client_id=1285070559087951974&permissions=563914173967424&integration_type=0&scope=bot)", inline=False)
    embed.add_field(name="Support Server", value="[Join Support Server](https://discord.gg/3UpnJhjkKZ)", inline=False)
    embed.add_field(name="Top.gg Page", value="[Vote for the Bot](https://top.gg/bot/1285070559087951974/vote)", inline=False)
    embed.set_footer(text=f"Uptime: {uptime_str}")

    # Send the embed
    await ctx.send(embed=embed)

@bot.tree.command(name="botinfo", description="Get information about the bot")
async def botinfo(interaction: discord.Interaction):
    # Calculate the bot's uptime
    current_time = datetime.datetime.now(datetime.timezone.utc)
    uptime = current_time - start_time
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds

    # Get the number of servers and total number of users
    num_servers = len(bot.guilds)
    num_shards = len(bot.shards)

    # Create the embed
    embed = discord.Embed(title="Bot Information", color=discord.Color.dark_embed())
    embed.set_thumbnail(url=bot.user.avatar)
    embed.add_field(name="Servers and Shards", value=f"{num_servers} Servers, {num_shards} Shards", inline=True)
    embed.add_field(name="Bot Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Invite Link", value="[Invite the Bot](https://discord.com/oauth2/authorize?client_id=1285070559087951974&permissions=563914173967424&integration_type=0&scope=bot)", inline=False)
    embed.add_field(name="Support Server", value="[Join Support Server](https://discord.gg/3UpnJhjkKZ)", inline=False)
    embed.add_field(name="Top.gg Page", value="[Vote for the Bot](https://top.gg/bot/1285070559087951974/vote)", inline=False)
    embed.set_footer(text=f"Uptime: {uptime_str}")

    # Send the embed
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_close():
    conn.close()

riddles = [
    {"question": "What has keys but can't open locks?", "answer": "piano"},
    {"question": "What has a head, a tail, is brown, and has no legs?", "answer": "penny"},
    {"question": "What comes once in a minute, twice in a moment, but never in a thousand years?", "answer": "m"},
    {"question": "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "answer": "echo"},
    {"question": "I have branches, but no fruit, trunk or leaves. What am I?", "answer": "bank"},
    {"question": "The more you take, the more you leave behind. What am I?", "answer": "footsteps"},
    {"question": "What can travel around the world while staying in one corner?", "answer": "stamp"},
    {"question": "What has to be broken before you can use it?", "answer": "egg"},
    {"question": "What has an eye but cannot see?", "answer": "needle"},
    {"question": "I’m tall when I’m young, and I’m short when I’m old. What am I?", "answer": "candle"},
    {"question": "What gets wetter as it dries?", "answer": "towel"},
    {"question": "I shave every day, but my beard stays the same. What am I?", "answer": "barber"},
    {"question": "The more you have of me, the less you see. What am I?", "answer": "darkness"},
    {"question": "What has one eye but can’t see?", "answer": "needle"},
    {"question": "I’m light as a feather, yet the strongest man can’t hold me for much longer. What am I?", "answer": "breath"},
    {"question": "What runs but never walks, has a mouth but never talks, has a bed but never sleeps?", "answer": "river"},
    {"question": "I’m always in front of you but never seen. What am I?", "answer": "future"},
    {"question": "What has many needles but doesn’t sew?", "answer": "pine tree"},
    {"question": "What can you catch but not throw?", "answer": "cold"},
    {"question": "The more of this there is, the less you see. What is it?", "answer": "darkness"},
    {"question": "What comes down but never goes up?", "answer": "rain"},
    {"question": "What is always in front of you but can’t be seen?", "answer": "future"},
    {"question": "What gets bigger when more is taken away?", "answer": "hole"},
    {"question": "What can fill a room but takes up no space?", "answer": "light"},
    {"question": "What has a heart that doesn’t beat?", "answer": "artichoke"},
    {"question": "Forward I am heavy, but backward I am not. What am I?", "answer": "ton"},
    {"question": "What goes up but never comes down?", "answer": "age"},
    {"question": "What can’t talk but will reply when spoken to?", "answer": "echo"},
    {"question": "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?", "answer": "map"},
    {"question": "What has hands but can’t clap?", "answer": "clock"},
    {"question": "What has to be broken before you can use it?", "answer": "egg"},
    {"question": "What can you hold in your right hand but not in your left?", "answer": "left hand"},
    {"question": "What is so fragile that saying its name breaks it?", "answer": "silence"},
    {"question": "What has legs but doesn’t walk?", "answer": "table"},
    {"question": "What has a head, a tail, but no body?", "answer": "coin"},
    {"question": "What flies without wings?", "answer": "time"},
    {"question": "I am taken from a mine, and shut up in a wooden case, from which I am never released, and yet I am used by almost every person. What am I?", "answer": "pencil lead"},
    {"question": "What has 88 keys but can’t open a single door?", "answer": "piano"},
    {"question": "What can run but never walks, has a mouth but never talks, has a head but never weeps, has a bed but never sleeps?", "answer": "river"},
    {"question": "What comes down but never goes up?", "answer": "rain"},
    {"question": "What begins with T, ends with T, and has T in it?", "answer": "teapot"},
    {"question": "What has a thumb and four fingers but is not alive?", "answer": "glove"},
    {"question": "What starts with 'e' and ends with 'e' but only has one letter in it?", "answer": "envelope"},
    {"question": "The more of this there is, the less you see. What is it?", "answer": "darkness"},
    {"question": "What can travel around the world while staying in the same spot?", "answer": "stamp"},
    {"question": "What word is spelled incorrectly in every dictionary?", "answer": "incorrectly"},
    {"question": "What runs around the whole yard without moving?", "answer": "fence"},
    {"question": "What starts with a P, ends with an E, and has thousands of letters?", "answer": "post office"},
    {"question": "What is so delicate that saying its name breaks it?", "answer": "silence"},
    {"question": "What invention lets you look right through a wall?", "answer": "window"},
    {"question": "What has to be broken before you can use it?", "answer": "egg"},
    {"question": "I’m tall when I’m young, and I’m short when I’m old. What am I?", "answer": "candle"},
    {"question": "What can’t talk but will reply when spoken to?", "answer": "echo"},
    {"question": "The more you take, the more you leave behind. What am I?", "answer": "footsteps"},
    {"question": "What has one eye, but can’t see?", "answer": "needle"},
    {"question": "What goes up but never comes down?", "answer": "age"},
    {"question": "What can you catch, but not throw?", "answer": "cold"},
    {"question": "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?", "answer": "map"},
    {"question": "What has many keys but can’t open a single lock?", "answer": "piano"},
    {"question": "What can run but never walks, has a mouth but never talks, has a head but never weeps, has a bed but never sleeps?", "answer": "river"},
    {"question": "What can travel around the world while staying in one corner?", "answer": "stamp"},
    {"question": "What gets wetter as it dries?", "answer": "towel"},
    {"question": "The more you take, the more you leave behind. What am I?", "answer": "footsteps"},
    {"question": "I’m tall when I’m young, and I’m short when I’m old. What am I?", "answer": "candle"},
    {"question": "What has a head, a tail, but no body?", "answer": "coin"},
    {"question": "What is full of holes but still holds water?", "answer": "sponge"},
    {"question": "What can you catch, but not throw?", "answer": "cold"},
    {"question": "What has teeth but cannot bite?", "answer": "comb"},
    {"question": "What is so light that even the strongest man cannot hold it for more than a few minutes?", "answer": "breath"},
    {"question": "What can fill a room but takes up no space?", "answer": "light"},
    {"question": "What is full of holes but still holds water?", "answer": "sponge"},
    {"question": "What is always running but never gets anywhere?", "answer": "clock"},
    {"question": "What has four fingers and a thumb but is not alive?", "answer": "glove"},
    {"question": "What has cities, but no houses; forests, but no trees; and rivers, but no water?", "answer": "map"},
    {"question": "What comes up but never goes down?", "answer": "age"},
    {"question": "What has words, but never speaks?", "answer": "book"},
    {"question": "The more you take, the more you leave behind. What am I?", "answer": "footsteps"},
    {"question": "I have keys but no locks. I have a space but no room. You can enter, but you can’t go outside. What am I?", "answer": "keyboard"},
    {"question": "What kind of coat is always wet when you put it on?", "answer": "paint"},
    {"question": "What has a neck but no head?", "answer": "bottle"},
    {"question": "What belongs to you but is used more by others?", "answer": "name"},
    {"question": "What has an end but no beginning, a home but no family, and a space but no room?", "answer": "keyboard"},
    {"question": "What is so fragile that even saying its name can break it?", "answer": "silence"},
    {"question": "What is so heavy that you can see it but can never lift it?", "answer": "mountain"},
    {"question": "What comes down but never goes up?", "answer": "rain"},
    {"question": "What can be cracked, made, told, and played?", "answer": "joke"},
    {"question": "What has a bottom at the top?", "answer": "legs"},
    {"question": "What has an eye but cannot see?", "answer": "storm"},
    {"question": "What is so fragile that even just mentioning it can break it?", "answer": "silence"},
    {"question": "What five-letter word becomes shorter when you add two letters to it?", "answer": "short"},
    {"question": "What has a bark, but no bite?", "answer": "tree"},
    {"question": "What has wheels and flies, but is not an aircraft?", "answer": "garbage truck"},
    {"question": "What is easy to get into, but hard to get out of?", "answer": "trouble"},
    {"question": "What can be broken, even if no one touches it?", "answer": "promise"},
    {"question": "What can you hold without ever touching?", "answer": "conversation"},
    {"question": "What has one head, one foot, and four legs?", "answer": "bed"},
    {"question": "What tastes better than it smells?", "answer": "tongue"},
    {"question": "What has keys that open no locks, with space but no room, and you can enter but you can’t go outside?", "answer": "keyboard"},
    {"question": "What can be seen once in a second, twice in a decade, but never in a lifetime?", "answer": "e"},
    {"question": "What has a thumb and four fingers but isn’t alive?", "answer": "glove"},
    {"question": "What has an eye but cannot see?", "answer": "needle"},
    {"question": "What is black and white and read all over?", "answer": "newspaper"},
    {"question": "What can be cracked, made, told, and played?", "answer": "joke"},
    {"question": "What can go up a chimney down, but not down a chimney up?", "answer": "umbrella"},
    {"question": "What is always coming, but never arrives?", "answer": "tomorrow"},
    {"question": "What is often returned but never borrowed?", "answer": "thanks"},
    {"question": "What gets bigger the more you take away?", "answer": "hole"},
    {"question": "What can fill a room but take up no space?", "answer": "light"},
    {"question": "What grows when it eats, but dies when it drinks?", "answer": "fire"},
    {"question": "What is lighter than a feather but the strongest person can’t hold for long?", "answer": "breath"},
    {"question": "What has to be broken before you can use it?", "answer": "egg"},
    {"question": "What is hard to see but easy to recognize once noticed?", "answer": "pattern"},
    {"question": "What has a neck but no head?", "answer": "bottle"},
    {"question": "What is always in front of you but can’t be seen?", "answer": "future"},
    {"question": "What has no doors, but can be entered?", "answer": "keyboard"},
    {"question": "What comes up but never comes down?", "answer": "age"},
    {"question": "What has keys but can’t open locks?", "answer": "keyboard"},
    {"question": "What runs around a house but doesn’t move?", "answer": "fence"},
    {"question": "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "answer": "echo"},
    {"question": "What has a face and two hands but no arms or legs?", "answer": "clock"},
    {"question": "What has no life but can die?", "answer": "battery"},
    {"question": "I am not alive, but I grow. I don’t have lungs, but I need air. What am I?", "answer": "fire"},
    {"question": "What can go up but never come down?", "answer": "age"},
    {"question": "What has ears but cannot hear?", "answer": "corn"},
    {"question": "I have a spine but no bones. What am I?", "answer": "book"},
    {"question": "What is so light, even the strongest person in the world can’t hold it?", "answer": "bubble"},
    {"question": "What is always hungry and must be fed but never eats?", "answer": "fire"},
    {"question": "What can run but cannot walk?", "answer": "river"},
    {"question": "What is black when you buy it, red when you use it, and gray when you throw it away?", "answer": "charcoal"},
    {"question": "What has a neck but no head?", "answer": "bottle"},
    {"question": "What has many teeth but cannot bite?", "answer": "comb"},
    {"question": "What is always in front of you but can’t be seen?", "answer": "future"},
    {"question": "What gets sharper the more you use it?", "answer": "brain"},
    {"question": "What goes up but never comes down?", "answer": "age"},
    {"question": "What has one head, one foot, and four legs?", "answer": "bed"},
    {"question": "What can be broken but is never held?", "answer": "promise"},
    {"question": "What gets wetter the more it dries?", "answer": "towel"},
    {"question": "What goes through cities and fields but never moves?", "answer": "road"},
    {"question": "What can be cracked, made, told, and played?", "answer": "joke"},
    {"question": "What has many keys but can’t open a lock?", "answer": "piano"},
    {"question": "What flies without wings?", "answer": "time"},
    {"question": "What runs but never walks?", "answer": "river"},
    {"question": "What is full of holes but still holds water?", "answer": "sponge"},
    {"question": "What has words but never speaks?", "answer": "book"},
    {"question": "What has 13 hearts, but no other organs?", "answer": "deck of cards"},
    {"question": "What comes down but never goes up?", "answer": "rain"},
    {"question": "What word is always spelled incorrectly?", "answer": "incorrectly"},
    {"question": "What gets bigger the more you take away?", "answer": "hole"},
    {"question": "I’m not alive, but I can grow. I don’t have lungs, but I need air. What am I?", "answer": "fire"},
    {"question": "What has 88 keys but can’t open a single door?", "answer": "piano"},
    {"question": "What has hands but cannot clap?", "answer": "clock"},
    {"question": "What is tall when it’s young and short when it’s old?", "answer": "candle"},
    {"question": "What has a heart that doesn’t beat?", "answer": "artichoke"},
    {"question": "What can be touched but cannot be seen?", "answer": "thoughts"},
    {"question": "What has roots nobody sees and is taller than trees?", "answer": "mountain"},
    {"question": "What can you catch but not throw?", "answer": "cold"},
    {"question": "What can fill a room but takes up no space?", "answer": "light"},
    {"question": "What has many rings but no fingers?", "answer": "tree"},
    {"question": "What has many faces, but no one looks?", "answer": "die"},
    {"question": "What is always running but never gets tired?", "answer": "clock"},
    {"question": "I’m taken from a mine and shut up in a wooden case, from which I am never released, and yet I am used by almost everyone. What am I?", "answer": "pencil lead"},
    {"question": "What is easy to get into but hard to get out of?", "answer": "trouble"},
    {"question": "What comes down but never goes up?", "answer": "rain"},
    {"question": "What has a bottom at the top?", "answer": "legs"},
    {"question": "What has four legs, but can't walk?", "answer": "hair"},
    {"question": "What is harder to catch the faster you run?", "answer": "breath"},
    {"question": "What has keys but no locks, space but no room, and you can enter but not go outside?", "answer": "keyboard"},
    {"question": "I’m lighter than air, but a hundred people can’t lift me. What am I?", "answer": "bubble"},
    {"question": "What has a bed but never sleeps, can run but never walks?", "answer": "river"},
    {"question": "What has to be broken before you can use it?", "answer": "egg"},
    {"question": "What can run, but never walks; has a mouth, but never talks?", "answer": "river"},
    {"question": "What has a ring but no finger?", "answer": "telephone"},
    {"question": "I am always hungry, I must always be fed. The finger I touch, will soon turn red. What am I?", "answer": "fire"}
]

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def riddle(ctx):
    riddle = random.choice(riddles)
    question = riddle["question"]
    answer = riddle["answer"]

    embed = discord.Embed(title="Riddle Time!", description=question, color=discord.Color.blue())
    embed.set_footer(text="You have 2 minutes to answer.")
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        user_message = await bot.wait_for('message', check=check, timeout=120.0)
        user_answer = user_message.content.strip().lower()

        if user_answer == answer:
            await ctx.send("Correct! Well done!")
        else:
            await ctx.send(f"Incorrect! The correct answer was: {answer}")
    except asyncio.TimeoutError:
        await ctx.send(f"Time's up! The correct answer was: {answer}")

@bot.tree.command(name="riddle", description="Solve a riddle")
@app_commands.checks.cooldown(1, 10, key=lambda i:(i.user.id))
async def riddle(interaction: discord.Interaction):
    riddle = random.choice(riddles)
    question = riddle["question"]
    answer = riddle["answer"]

    embed = discord.Embed(title="Riddle Time!", description=question, color=discord.Color.blue())
    embed.set_footer(text="You have 2 minutes to answer.")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        user_message = await bot.wait_for('message', check=check, timeout=120.0)
        user_answer = user_message.content.strip().lower()

        if user_answer == answer:
            await interaction.followup.send("Correct! Well done!")
        else:
            await interaction.followup.send(f"Incorrect! The correct answer was: {answer}")
    except asyncio.TimeoutError:
        await interaction.followup.send(f"Time's up! The correct answer was: {answer}")

@bot.command()
async def server_info(ctx):
    if ctx.author.id == 678908396845400074:
        for guild in bot.guilds:
            print(guild.name) # prints all server's names
    else:
        await ctx.send("You do not have permission to use this command.")

class FirstMoveSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Attack First", description="Choose to attack first"),
            discord.SelectOption(label="Defend First", description="Choose to defend first"),
            discord.SelectOption(label="Forfeit", description="Quit the fight before it starts"),
        ]
        super().__init__(placeholder="Choose your first move...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.turn:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if self.values[0] == "Forfeit":
            embed = discord.Embed(
                title="Game Over",
                description=f"{interaction.user.mention} has forfeited the fight.",
                color=discord.Color.red()
            )
            # Send the forfeit message without setting view=None, then stop the view
            await interaction.response.send_message(embed=embed)
            view.stop()  # Stop the view to prevent further interactions
            return

        if self.values[0] == "Attack First":
            view.attacker = view.turn
            view.defender = view.user2 if view.turn == view.user1 else view.user1
        elif self.values[0] == "Defend First":
            view.defender = view.turn
            view.attacker = view.user2 if view.turn == view.user1 else view.user1

        view.turn = view.attacker  # Ensure the attacker goes first
        await view.start_game(interaction)

class FightView(View):
    def __init__(self, user1, user2):
        super().__init__(timeout=60.0)  # Set a 60-second timeout
        self.user1 = user1
        self.user2 = user2
        self.hp = {user1: 100, user2: 100}
        self.crash_out_used = {user1: False, user2: False}
        self.round = 1
        self.turn = random.choice([user1, user2])
        self.attacker = None
        self.defender = None
        self.last_action = ""
        self.attack_move = None
        self.phase = "attack"  # Start with attack phase
        self.add_item(FirstMoveSelect())

    # Method to start the game
    async def start_game(self, interaction):
        self.clear_items()
        self.add_item(AttackButton())
        self.add_item(HeavyAttackButton())
        self.add_item(CrashOutButton())
        self.add_item(DodgeButton())
        self.add_item(ParryButton())
        self.disable_defense_buttons()
        self.turn = self.attacker  # Ensure the attacker goes first
        await self.update_embed(interaction)

    # Embed update method
    async def update_embed(self, interaction):
        embed = discord.Embed(title="Fight!", description=f"It's {self.turn.mention}'s turn!")
        embed.add_field(name=f"{self.user1.name}'s HP", value=self.hp[self.user1], inline=True)
        embed.add_field(name=f"{self.user2.name}'s HP", value=self.hp[self.user2], inline=True)
        embed.add_field(name="Round", value=self.round, inline=True)
        embed.add_field(name="Last Action", value=self.last_action, inline=False)
        
        ACTION_GIFS = {
            "Light Attack": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExcjZ4bXYzbmtlamtmMDZhMndob2NrY2YwZ29lODRqZWc1Y2JiZTExNSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/AT9t5MK37Bzt90r3Wv/giphy.gif",
            "Heavy Attack": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGN0aG8yZHYyenFzaTJwaXdtdGRkNzVrNGw3aTRqNno2Z2w0MDc1MSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3ohc1292yKn6Z1saGs/giphy.gif",
            "Crash Out": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExamtud2F0NXhpem80d2V4ZjV3aXVmbjc0Z2Y5YXN4cDg4cDlxZnBpcSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ixYRj3H9HOzWE/giphy.gif",
            "Dodge Success": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Zncmx2cnRoNGh3czVnZnEybTZ5Z2ZtMDRpM2Zrand2MHlnOTRwZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5TSxsJJuSXahO/giphy.gif",
            "Dodge Fail": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExMzluYWF2cmVpMjc2dDdqNXNrMWY4b2c0a3J1am52eHdrMXF6MDVtZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/kQiVNXM7Uehr82dfcZ/giphy.gif",
            "Parry Success": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExd2duN255dTJndDJpaHFkZDJuaDFsYTJmMjAxZXkzanNsdGF3YTl6byZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/QUvYmUKMfoUhuAoyhx/giphy.gif",
            "Parry Fail": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExNmw0M25pM3dxeGt2OWtyNWFzMjFmdGxybzlvOHkwbzBjcnh5NHRtYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/XGP2jgGMR7lEgWnJ50/giphy.gif",
            "Forfeit": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExc29zbGs5bnR3NzJvNzl0dXBuOWJhYTE4YW01eGo2c3J4emZod3hwNSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3ohs4kOJi0cKYTz8Hu/giphy.gif"
        }

        gif_url = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExZHN6bTcwOWRsbmFqcjdiZnh6Y3pqbDgzaHJhcDljajBzeHRtZnRmMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8tYqTxolfDB1tFmQ8L/giphy.gif"
        if "Light Attack" in self.last_action:
            gif_url = ACTION_GIFS["Light Attack"]
        elif "Heavy Attack" in self.last_action:
            gif_url = ACTION_GIFS["Heavy Attack"]
        elif "Crash Out" in self.last_action:
            gif_url = ACTION_GIFS["Crash Out"]
        elif "dodged" in self.last_action:
            gif_url = ACTION_GIFS["Dodge Fail"] if "failed" in self.last_action else ACTION_GIFS["Dodge Success"]
        elif "parried" in self.last_action:
            gif_url = ACTION_GIFS["Parry Fail"] if "failed" in self.last_action else ACTION_GIFS["Parry Success"]
        elif "forfeited" in self.last_action:
            gif_url = ACTION_GIFS["Forfeit"]

        embed.set_image(url=gif_url)
        await interaction.response.edit_message(embed=embed, view=self)

    # Method to end the game
    async def end_game(self, interaction, winner):
        embed = discord.Embed(title="Game Over", description=f"{winner.mention} wins!")
        embed.add_field(name=f"{self.user1.name}'s HP", value=self.hp[self.user1], inline=True)
        embed.add_field(name=f"{self.user2.name}'s HP", value=self.hp[self.user2], inline=True)
        await interaction.response.edit_message(embed=embed, view=None)
        update_score(winner.id, str(winner), 1, 'fight')  # Add 1 point for the winner
        self.stop()  # Stop the view to end the game

    # Method to handle timeout
    async def on_timeout(self):
        # Notify players that the game has ended due to inactivity
        await self.user1.send("The fight has ended due to inactivity.")
        await self.user2.send("The fight has ended due to inactivity.")
        self.stop()  # End the game

    async def next_turn(self, interaction, skip_defense=False):
        # Check for end of game
        if self.hp[self.user1] <= 0:
            await self.end_game(interaction, self.user2)
            return
        elif self.hp[self.user2] <= 0:
            await self.end_game(interaction, self.user1)
            return

        if self.phase == "attack":
            if skip_defense:
                # Apply damage directly if needed
                damage = self.attack_move.get("damage", 0)
                if self.attack_move.get("self_damage"):
                    self.hp[self.attacker] -= damage
                    self.last_action = f"{self.attacker.mention} dealt {damage} damage to themselves with a Crash Out!"
                else:
                    self.hp[self.defender] -= damage
                    self.last_action = f"{self.attacker.mention} dealt {damage} damage to {self.defender.mention}."

                # Swap roles and proceed to the next round
                self.phase = "attack"  # Continue in attack phase
                self.attacker, self.defender = self.defender, self.attacker
                self.turn = self.attacker
                self.round += 1
                self.enable_attack_buttons()
                self.disable_defense_buttons()
            else:
                # Proceed to defense phase
                self.phase = "defense"
                self.turn = self.defender
                self.enable_defense_buttons()
                self.disable_attack_buttons()
        else:
            # After defense, swap roles and continue the attack phase
            self.phase = "attack"
            self.attacker, self.defender = self.defender, self.attacker
            self.turn = self.attacker
            self.round += 1
            self.enable_attack_buttons()
            self.disable_defense_buttons()

        # Update the embed with the new round, action, and possibly the GIF
        await self.update_embed(interaction)

    def enable_attack_buttons(self):
        for item in self.children:
            if isinstance(item, (AttackButton, HeavyAttackButton, CrashOutButton)):
                item.disabled = False

    def disable_attack_buttons(self):
        for item in self.children:
            if isinstance(item, (AttackButton, HeavyAttackButton, CrashOutButton)):
                item.disabled = True

    def enable_defense_buttons(self):
        for item in self.children:
            if isinstance(item, (DodgeButton, ParryButton)):
                item.disabled = False

    def disable_defense_buttons(self):
        for item in self.children:
            if isinstance(item, (DodgeButton, ParryButton)):
                item.disabled = True

    async def process_defense(self, interaction, defense_move):
        if defense_move == "Dodge":
            if random.random() < 0.6:
                self.last_action = f"{interaction.user.mention} dodged the attack from {self.attacker.mention}."
            else:
                damage = self.attack_move["damage"]
                self.hp[interaction.user] -= damage
                self.last_action = f"{interaction.user.mention} failed to dodge and took {damage} damage from {self.attacker.mention}."
        elif defense_move == "Parry":
            if random.random() < 0.7:
                damage = self.attack_move["damage"]
                self.hp[interaction.user] -= damage
                self.last_action = f"{interaction.user.mention} failed to parry and took {damage} damage from {self.attacker.mention}."
            else:
                damage = self.attack_move["counter_damage"]
                self.hp[self.attacker] -= damage
                self.last_action = f"{interaction.user.mention} successfully parried and dealt {damage} damage to {self.attacker.mention}."

        await self.next_turn(interaction)

class CrashOutButton(Button):
    def __init__(self):
        super().__init__(label="Crash Out", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.turn or view.phase != "attack":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if view.crash_out_used[interaction.user]:
            await interaction.response.send_message("You can only use Crash Out once per game!", ephemeral=True)
            return

        view.crash_out_used[interaction.user] = True
        if random.random() < 0.5:
            damage = 60
            view.attack_move = {"damage": damage}
            view.last_action = f"{interaction.user.mention} did a Crash Out and dealt {damage} damage to {view.defender.mention}."
        else:
            damage = 60
            view.attack_move = {"damage": damage, "self_damage": True}
            view.last_action = f"{interaction.user.mention} did a Crash Out and dealt {damage} damage to themselves."
        await view.next_turn(interaction, skip_defense=True)  # Skip defense

class AttackButton(Button):
    def __init__(self):
        super().__init__(label="Light Attack", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.turn or view.phase != "attack":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        view.attack_move = {"damage": random.randint(5, 15), "counter_damage": random.randint(5, 15)}
        view.last_action = f"{interaction.user.mention} did a Light Attack."
        await view.next_turn(interaction)

class HeavyAttackButton(Button):
    def __init__(self):
        super().__init__(label="Heavy Attack", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.turn or view.phase != "attack":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if random.random() < 0.2:
            view.attack_move = {"damage": 0}
            view.last_action = f"{interaction.user.mention} tried a Heavy Attack but missed!"
            await view.next_turn(interaction, skip_defense=True)  # Skip defense
        else:
            damage = random.randint(25, 30)
            view.attack_move = {"damage": damage, "counter_damage": random.randint(25, 30)}
            view.last_action = f"{interaction.user.mention} did a Heavy Attack."
            await view.next_turn(interaction)

class DodgeButton(Button):
    def __init__(self):
        super().__init__(label="Dodge", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.turn or view.phase != "defense":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        await view.process_defense(interaction, "Dodge")

class ParryButton(Button):
    def __init__(self):
        super().__init__(label="Parry", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.turn or view.phase != "defense":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        await view.process_defense(interaction, "Parry")

@bot.command()
@commands.cooldown(1, 40, commands.BucketType.user)
async def fight(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("You can't fight yourself!")
        return
    if opponent.bot:
        await ctx.send("You cannot play against a bot!")
        return

    await ctx.send(f"{opponent.mention}, {ctx.author.mention} has challenged you to a fight!")
    await ctx.send("https://tenor.com/view/cj-sekiro-gif-23480678")
    instructionsembed = discord.Embed(title="Instructions", description="Light attack: 5-15 damage, doesn't miss\nHeavy attack: 25-30 damage, 20 percent chance of missing\nCrash Out: 60 damage, 50/50 chance of hitting either users\nDodge: 60 percent success rate\nParry: 30 percent success rate, does counter-damage if successful", color=discord.Color.red())
    await ctx.send(embed=instructionsembed)
    view = FightView(ctx.author, opponent)
    await ctx.send(f"{view.turn.mention}, choose your first move:", view=view)

@bot.tree.command(name="fight", description="Challenge another user to a fight")
@app_commands.describe(opponent="The member you want to challenge")
@app_commands.checks.cooldown(1, 40, key=lambda i: i.user.id)
async def fight(interaction: discord.Interaction, opponent: discord.Member):
    if opponent == interaction.user:
        await interaction.response.send_message("You can't fight yourself!", ephemeral=True)
        return
    elif opponent.bot:
        await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
        return

    await interaction.response.send_message(f"{opponent.mention}, {interaction.user.mention} has challenged you to a fight!")
    await interaction.followup.send("https://tenor.com/view/cj-sekiro-gif-23480678")
    instructionsembed = discord.Embed(
        title="Instructions",
        description="Light attack: 5-15 damage, doesn't miss\nHeavy attack: 25-30 damage, 20 percent chance of missing\nCrash Out: 60 damage, 50/50 chance of hitting either users\nDodge: 60 percent success rate\nParry: 30 percent success rate, does counter-damage if successful",
        color=discord.Color.red()
    )
    await interaction.followup.send(embed=instructionsembed)
    view = FightView(interaction.user, opponent)
    await interaction.followup.send(f"{view.turn.mention}, choose your first move:", view=view)

EMPTY_SLOT = "⚪"
PLAYER1_PIECE = "🔴"
PLAYER2_PIECE = "🟡"
ROWS = 6
COLUMNS = 7

# Initialize the board
def initialize_board():
    return [[EMPTY_SLOT for _ in range(COLUMNS)] for _ in range(ROWS)]

# Generate the embed for commands.Context
def generate_embed(board, current_player, ctx):
    description = "\n".join(["".join(row) for row in board])
    color = discord.Color.red() if current_player == ctx.author else discord.Color.yellow()
    embed = discord.Embed(title="Connect 4", description=description, color=color)
    embed.add_field(name="Current Turn", value=f"{current_player.mention} ({PLAYER1_PIECE if current_player == ctx.author else PLAYER2_PIECE})")
    return embed

# Generate the embed for discord.Interaction
def generate_embed_for_interaction(board, current_player, interaction):
    description = "\n".join(["".join(row) for row in board])
    color = discord.Color.red() if current_player == interaction.user else discord.Color.yellow()
    embed = discord.Embed(title="Connect 4", description=description, color=color)
    embed.add_field(name="Current Turn", value=f"{current_player.mention} ({PLAYER1_PIECE if current_player == interaction.user else PLAYER2_PIECE})")
    return embed

# Create buttons
def create_buttons():
    view = View()
    for col in range(COLUMNS):
        button = Button(label=f"Column {col+1}", custom_id=str(col), style=discord.ButtonStyle.primary)
        view.add_item(button)
    return view

# Check for win conditions
def check_win(board, piece):
    # Check horizontal, vertical, and diagonal win conditions
    for row in range(ROWS):
        for col in range(COLUMNS - 3):
            if all(board[row][col + i] == piece for i in range(4)):
                return True
    for row in range(ROWS - 3):
        for col in range(COLUMNS):
            if all(board[row + i][col] == piece for i in range(4)):
                return True
    for row in range(ROWS - 3):
        for col in range(COLUMNS - 3):
            if all(board[row + i][col + i] == piece for i in range(4)):
                return True
    for row in range(3, ROWS):
        for col in range(COLUMNS - 3):
            if all(board[row - i][col + i] == piece for i in range(4)):
                return True
    return False

def check_tie(board):
    return all(board[row][col] != EMPTY_SLOT for row in range(ROWS) for col in range(COLUMNS))

@bot.command(aliases=["c4"])
@commands.cooldown(1, 60, commands.BucketType.user)
async def connect4(ctx, opponent: discord.Member):
    if opponent.bot:
        await ctx.send("You cannot play against a bot!")
        return
    
    await start_connect4_game(ctx, ctx.author, opponent)

@bot.tree.command(name="connect4", description="Play a game of Connect 4")
@app_commands.describe(opponent="The member you want to play against")
@app_commands.checks.cooldown(1, 60, key=lambda i:(i.user.id))
async def connect4(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.bot:
        await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
        return
    
    await start_connect4_game(interaction, interaction.user, opponent)

async def start_connect4_game(source, current_player, opponent_player):
    if current_player == opponent_player:
        await (source.send("You cannot play a game with yourself!") if isinstance(source, commands.Context) else source.response.send_message("You cannot play a game with yourself!", ephemeral=True))
        return
    
    board = initialize_board()
    embed = generate_embed(board, current_player, source)
    view = create_buttons()
    
    # Set a 60-second timeout for the view
    view.timeout = 60.0

    if isinstance(source, commands.Context):
        message = await source.send(embed=embed, view=view)
    else:
        message = await source.response.send_message(embed=embed, view=view)

    async def button_callback(interaction):
        nonlocal current_player
        if interaction.user != current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        
        col = int(interaction.data["custom_id"])
        
        # Check if the column is full before placing a piece
        if board[0][col] != EMPTY_SLOT:
            await interaction.response.send_message("This column is full! Choose another column.", ephemeral=True)
            return

        # Place the piece in the lowest empty slot in the column
        for row in reversed(range(ROWS)):
            if board[row][col] == EMPTY_SLOT:
                board[row][col] = PLAYER1_PIECE if current_player == (source.author if isinstance(source, commands.Context) else source.user) else PLAYER2_PIECE
                break

        # Check if the move resulted in a win
        if check_win(board, PLAYER1_PIECE if current_player == (source.author if isinstance(source, commands.Context) else source.user) else PLAYER2_PIECE):
            embed = generate_embed(board, current_player, source)
            embed.set_footer(text=f"{current_player} wins! 🎉")
            await interaction.response.edit_message(embed=embed, view=None)
            # Add 1 point for the winner
            update_score(current_player.id, str(current_player), 1, 'connect4')
            view.stop()  # Stop the view to end the game
            return

        # Check if the board is now full (tie)
        if check_tie(board):
            embed = generate_embed(board, current_player, source)
            embed.set_footer(text="It's a tie! 😐")
            await interaction.response.edit_message(embed=embed, view=None)
            view.stop()  # Stop the view to end the game
            return

        # Update the button to disable it if the column is now full
        if board[0][col] != EMPTY_SLOT:
            for item in view.children:
                if item.custom_id == str(col):
                    item.disabled = True

        # Switch turns
        current_player = opponent_player if current_player == (source.author if isinstance(source, commands.Context) else source.user) else (source.author if isinstance(source, commands.Context) else source.user)
        embed = generate_embed(board, current_player, source)
        await interaction.response.edit_message(embed=embed, view=view)

    # Set the callback for each button
    for item in view.children:
        item.callback = button_callback

    async def on_timeout():
        # Notify players that the game has ended due to inactivity
        await message.channel.send("Time's up! The Connect 4 game has ended due to inactivity.")
        view.stop()  # Stop the view to end the game

    view.on_timeout = on_timeout

def generate_embed(board, current_player, source):
    description = "\n".join(["".join(row) for row in board])
    color = discord.Color.red() if current_player == (source.author if isinstance(source, commands.Context) else source.user) else discord.Color.yellow()
    embed = discord.Embed(title="Connect 4", description=description, color=color)
    embed.add_field(name="Current Turn", value=f"{current_player.mention} ({PLAYER1_PIECE if current_player == (source.author if isinstance(source, commands.Context) else source.user) else PLAYER2_PIECE})")
    return embed


TOP_GG_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEyODUwNzA1NTkwODc5NTE5NzQiLCJib3QiOnRydWUsImlhdCI6MTcyOTg1MTU5Nn0.yunYOfgRwyVFNUttCWt9-P1X2ObF7hTccLv5VW_QW0c'

class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.token = TOP_GG_TOKEN 
        self.topggpy = topgg.DBLClient(self.bot, self.token)

        self.update_stats.start()

    @tasks.loop(minutes=60)
    async def update_stats(self):
        try:
            await self.topggpy.post_guild_count()
            print(f"Posted server count: {len(self.bot.guilds)}")
        except Exception as e:
            print(f"Failed to post server count: {e}")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.update_stats()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.update_stats()

bot.run('MTI4NTA3MDU1OTA4Nzk1MTk3NA.GUGGCw.xMr8_BGGJyP1FycyFuklB66wx8k0Mufsk-DMPk')