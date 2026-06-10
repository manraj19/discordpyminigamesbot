"""Pure cricket simulation logic. No discord imports."""

import random


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

    for _ in range(overs):
        if wickets >= 10:
            break
        for _ball in range(6):
            if wickets >= 10:
                break
            balls_bowled += 1
            outcome = random.choices(
                ["dot", "single", "double", "triple", "four", "six", "wicket"],
                [0.3, 0.4, 0.1, 0.05, 0.1, 0.05, 0.1],
            )[0]
            batsman = batting_team[wickets]
            balls_faced[batsman] += 1
            if outcome == "wicket":
                dismissal_type = random.choice(["bowled", "caught", "run out"])
                if dismissal_type == "bowled":
                    bowler = random.choice([b for b in bowling_team if bowler_overs[b] < max_overs_per_bowler])
                    player_wickets[bowler] += 1
                    bowler_overs[bowler] += 1
                    highlights.append(
                        f"Wicket! {batsman} is out for {player_scores[batsman]} runs! Bowled by {bowler}."
                    )
                elif dismissal_type == "caught":
                    bowler = random.choice([b for b in bowling_team if bowler_overs[b] < max_overs_per_bowler])
                    fielder = random.choice(bowling_team)
                    player_wickets[bowler] += 1
                    bowler_overs[bowler] += 1
                    highlights.append(
                        f"Wicket! {batsman} is out for {player_scores[batsman]} runs! Caught by {fielder}. Bowler: {bowler}."
                    )
                elif dismissal_type == "run out":
                    fielder = random.choice(bowling_team)
                    highlights.append(
                        f"Wicket! {batsman} is out for {player_scores[batsman]} runs! Run out by {fielder}."
                    )
                wickets += 1
            else:
                runs_scored = {"dot": 0, "single": 1, "double": 2, "triple": 3, "four": 4, "six": 6}[outcome]
                runs += runs_scored
                player_scores[batsman] += runs_scored
                if outcome == "four":
                    highlights.append(f"Four! {batsman} hits a boundary!")
                elif outcome == "six":
                    highlights.append(f"Six! {batsman} hits it out of the park!")
                if 50 <= player_scores[batsman] < 100:
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
    top_batsmen_with_sr = [
        (player, runs, balls_faced[player], (runs / balls_faced[player]) * 100 if balls_faced[player] > 0 else 0)
        for player, runs in top_batsmen
    ]
    return top_batsmen_with_sr, top_bowlers
