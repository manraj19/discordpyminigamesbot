import random
from tabulate import tabulate

def get_team_input():
    team_name = input("Enter the team name: ")
    print(f"Enter the names of the players for {team_name}:")
    team = [input(f"Player {i+1}: ") for i in range(11)]
    return team_name, team

def toss():
    return random.choice(["Team 1", "Team 2"])

def simulate_innings(batting_team, bowling_team, target=None):
    runs = 0
    wickets = 0
    overs = 20
    player_scores = {player: 0 for player in batting_team}
    player_wickets = {player: 0 for player in bowling_team}
    highlights = []
    fifty_highlighted = set()

    for over in range(overs):
        if wickets >= 10:
            break
        for ball in range(6):
            if wickets >= 10:
                break
            outcome = random.choices(
                ["dot", "single", "double", "triple", "four", "six", "wicket"],
                [0.3, 0.4, 0.1, 0.05, 0.1, 0.05, 0.1]
            )[0]
            if outcome == "wicket":
                bowler = random.choice(bowling_team)
                player_wickets[bowler] += 1
                batsman = batting_team[wickets]
                batsman_score = player_scores[batsman]
                highlights.append(f"Wicket! {batsman} is out for {batsman_score} runs! Bowled by {bowler}.")
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
                player_scores[batting_team[wickets]] += runs_scored
                if player_scores[batting_team[wickets]] >= 50 and player_scores[batting_team[wickets]] < 100:
                    if batting_team[wickets] not in fifty_highlighted:
                        highlights.append(f"50 for {batting_team[wickets]}!")
                        fifty_highlighted.add(batting_team[wickets])
                elif player_scores[batting_team[wickets]] >= 100:
                    highlights.append(f"100 for {batting_team[wickets]}!")

            if target and runs > target:
                return runs, wickets, player_scores, player_wickets, highlights, True

    return runs, wickets, player_scores, player_wickets, highlights, False

def get_top_performers(player_scores, player_wickets):
    top_batsmen = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)[:4]
    top_bowlers = sorted(player_wickets.items(), key=lambda x: x[1], reverse=True)[:4]
    return top_batsmen, top_bowlers

def main():
    team1_name, team1 = get_team_input()
    team2_name, team2 = get_team_input()

    toss_winner = toss()
    print(f"{toss_winner} won the toss and chose to bat first.")

    if toss_winner == "Team 1":
        batting_team, bowling_team = team1, team2
        batting_team_name, bowling_team_name = team1_name, team2_name
    else:
        batting_team, bowling_team = team2, team1
        batting_team_name, bowling_team_name = team2_name, team1_name

    runs1, wickets1, scores1, wickets_taken1, highlights1, _ = simulate_innings(batting_team, bowling_team)

    print("\nFirst Innings Highlights:")
    for highlight in highlights1:
        print(highlight)

    runs2, wickets2, scores2, wickets_taken2, highlights2, chased = simulate_innings(bowling_team, batting_team, target=runs1)

    print("\nSecond Innings Highlights:")
    for highlight in highlights2:
        print(highlight)

    if chased:
        print(f"\n{bowling_team_name} wins by {10 - wickets2} wickets!")
    elif runs1 > runs2:
        print(f"\n{batting_team_name} wins by {runs1 - runs2} runs!")
    else:
        print(f"\n{bowling_team_name} wins by {10 - wickets2} wickets!")

    top_batsmen1, top_bowlers1 = get_top_performers(scores1, wickets_taken1)
    top_batsmen2, top_bowlers2 = get_top_performers(scores2, wickets_taken2)

    print("\nTop Performers:")
    print(f"Top Batsmen from {team1_name}:")
    print(tabulate(top_batsmen1, headers=["Player", "Runs"], tablefmt="grid"))

    print(f"Top Bowlers from {team1_name}:")
    print(tabulate(top_bowlers1, headers=["Player", "Wickets"], tablefmt="grid"))

    print(f"Top Batsmen from {team2_name}:")
    print(tabulate(top_batsmen2, headers=["Player", "Runs"], tablefmt="grid"))

    print(f"Top Bowlers from {team2_name}:")
    print(tabulate(top_bowlers2, headers=["Player", "Wickets"], tablefmt="grid"))

    final_scores = [
        [team1_name, runs1, wickets1],
        [team2_name, runs2, wickets2]
    ]
    print(f"\nFinal Scores:")
    print(tabulate(final_scores, headers=["Team", "Runs", "Wickets"], tablefmt="grid"))

if __name__ == "__main__":
    main()