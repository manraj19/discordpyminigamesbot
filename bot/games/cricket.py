"""Pure cricket simulation logic. No discord imports.

Skill model: a team is batting-order 0..10. Positions 0-5 are specialist
batsmen (they score more and get out less, openers strongest); positions 6-10
are the bowlers/tail (weaker with the bat, but they take most of the wickets
when bowling). The simulator emits a stream of commentary "events" with the
running score so the cog can replay an innings live, ball by ball."""

import random

from bot.core import emojis

OUTCOMES = ["dot", "single", "double", "triple", "four", "six", "wicket"]
BASE_WEIGHTS = {
    "dot": 0.30,
    "single": 0.40,
    "double": 0.10,
    "triple": 0.05,
    "four": 0.10,
    "six": 0.05,
    "wicket": 0.10,
}
RUNS = {"dot": 0, "single": 1, "double": 2, "triple": 3, "four": 4, "six": 6}


def _batting_weights(position):
    """Outcome weights tuned by batting position (0 = opener, 10 = #11)."""
    w = dict(BASE_WEIGHTS)
    if position < 6:  # specialist batsman, stronger the higher up
        tier = 6 - position  # 6..1
        w["four"] *= 1 + 0.18 * tier
        w["six"] *= 1 + 0.15 * tier
        w["single"] *= 1.05
        w["dot"] *= 0.9
        w["wicket"] *= max(0.35, 1 - 0.12 * tier)
    else:  # tail-ender / bowler with the bat
        tier = position - 5  # 1..5
        w["wicket"] *= 1 + 0.35 * tier
        w["four"] *= max(0.30, 1 - 0.15 * tier)
        w["six"] *= max(0.25, 1 - 0.18 * tier)
        w["dot"] *= 1 + 0.10 * tier
    return [w[o] for o in OUTCOMES]


def _bowling_weight(position):
    """How likely a fielder at this batting position is to be the bowler who
    takes a wicket. Specialist bowlers (6-10) take the vast majority."""
    return 5.0 if position >= 6 else 0.6


def _overs_str(balls):
    return f"{balls // 6}.{balls % 6}"


def simulate_innings(batting_team, bowling_team, overs, max_overs_per_bowler, target=None):
    runs = 0
    wickets = 0
    balls_faced = {player: 0 for player in batting_team}
    player_scores = {player: 0 for player in batting_team}
    player_wickets = {player: 0 for player in bowling_team}
    bowler_overs = {player: 0 for player in bowling_team}
    events = []
    fifty_highlighted = set()
    hundred_highlighted = set()
    balls_bowled = 0
    chased = False

    # Two batsmen at the crease: striker faces, non-striker waits at the other
    # end. These are batting-order positions, so the skill weights stay tied to
    # where a player bats. next_in is the next man to walk out after a wicket.
    striker, non_striker, next_in = 0, 1, 2

    def emit(text, kind):
        events.append({"text": text, "runs": runs, "wickets": wickets, "overs": _overs_str(balls_bowled), "kind": kind})

    def pick_bowler(last):
        # One bowler bowls a whole over, can't bowl two in a row, and is capped
        # at overs/5. With 11 possible bowlers the cap is always satisfiable, so
        # the fallbacks below are just crash-insurance for pathological rosters.
        candidates = [
            (b, i) for i, b in enumerate(bowling_team) if bowler_overs[b] < max_overs_per_bowler and b != last
        ]
        if not candidates:
            candidates = [(b, i) for i, b in enumerate(bowling_team) if b != last]
        if not candidates:
            candidates = [(b, i) for i, b in enumerate(bowling_team)]
        weights = [_bowling_weight(i) for _, i in candidates]
        return random.choices(candidates, weights=weights)[0][0]

    last_bowler = None
    for _over in range(overs):
        if wickets >= 10:
            break
        bowler = pick_bowler(last_bowler)
        last_bowler = bowler
        bowler_overs[bowler] += 1

        for _ball in range(6):
            if wickets >= 10:
                break
            balls_bowled += 1
            batsman = batting_team[striker]
            balls_faced[batsman] += 1
            outcome = random.choices(OUTCOMES, weights=_batting_weights(striker))[0]

            if outcome == "wicket":
                dismissal = random.choice(["bowled", "caught", "run out"])
                if dismissal == "run out":
                    fielder = random.choice(bowling_team)
                    emit(
                        f"{emojis.WICKET} WICKET! {batsman} run out by {fielder} for {player_scores[batsman]}.",
                        "wicket",
                    )
                else:
                    player_wickets[bowler] += 1
                    if dismissal == "bowled":
                        emit(
                            f"{emojis.WICKET} WICKET! {bowler} bowls {batsman} for {player_scores[batsman]}!", "wicket"
                        )
                    else:
                        fielder = random.choice(bowling_team)
                        emit(
                            f"{emojis.WICKET} WICKET! {batsman} c {fielder} b {bowler} for {player_scores[batsman]}.",
                            "wicket",
                        )
                wickets += 1
                # ponytail: the striker is always the one dismissed (incl. run-outs);
                # modelling who's at the danger end isn't worth it for a sim.
                if next_in <= 10:
                    striker = next_in
                    next_in += 1
            else:
                scored = RUNS[outcome]
                runs += scored
                player_scores[batsman] += scored
                if outcome == "four":
                    emit(f"🏏 FOUR! {batsman} finds the boundary.", "boundary")
                elif outcome == "six":
                    emit(f"💥 SIX! {batsman} goes big!", "boundary")
                if 50 <= player_scores[batsman] < 100 and batsman not in fifty_highlighted:
                    emit(f"⭐ FIFTY! {batsman} brings up his 50.", "milestone")
                    fifty_highlighted.add(batsman)
                elif player_scores[batsman] >= 100 and batsman not in hundred_highlighted:
                    emit(f"🌟 CENTURY! {batsman} reaches 100!", "milestone")
                    hundred_highlighted.add(batsman)
                if scored in (1, 3):  # odd run: batsmen cross, strike changes
                    striker, non_striker = non_striker, striker

            if target is not None and runs > target:
                chased = True
                emit(f"🎉 Chased down! {runs}/{wickets}.", "milestone")
                overs_played = balls_bowled // 6 + (balls_bowled % 6) / 10
                return (
                    runs,
                    wickets,
                    player_scores,
                    player_wickets,
                    events,
                    chased,
                    overs_played,
                    balls_faced,
                    bowler_overs,
                )

        striker, non_striker = non_striker, striker  # end of the over: strike rotates
        if wickets < 10:
            emit(f"End of over {balls_bowled // 6}: {runs}/{wickets}.", "over")

    overs_played = balls_bowled // 6 + (balls_bowled % 6) / 10
    return runs, wickets, player_scores, player_wickets, events, chased, overs_played, balls_faced, bowler_overs


def get_top_performers(player_scores, player_wickets, balls_faced):
    top_batsmen = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)[:4]
    top_bowlers = sorted(player_wickets.items(), key=lambda x: x[1], reverse=True)[:4]
    top_batsmen_with_sr = [
        (player, runs, balls_faced[player], (runs / balls_faced[player]) * 100 if balls_faced[player] > 0 else 0)
        for player, runs in top_batsmen
    ]
    return top_batsmen_with_sr, top_bowlers
