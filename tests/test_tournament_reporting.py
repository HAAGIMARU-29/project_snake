import json

from scripts.practice import placement_for_match
from scripts.tournament_report import aggregate, svg_chart


def test_four_snake_placement_uses_latest_elimination_as_second_place():
    deaths = {
        "Opponent1": {"cause": "body", "turn": 4},
        "Opponent2": {"cause": "hazard", "turn": 9},
        "Opponent3": {"cause": "health", "turn": 7},
    }
    result = {"winnerName": "TournamentBot"}
    assert placement_for_match(deaths, result) == {
        "TournamentBot": 1, "Opponent2": 2, "Opponent3": 3, "Opponent1": 4
    }


def test_aggregate_reports_wins_losses_points_and_positions():
    summary = {"matches": [{
        "result": {"winnerName": "TournamentBot"},
        "deaths": {
            "Opponent1": {"turn": 1}, "Opponent2": {"turn": 2}, "Opponent3": {"turn": 3}
        },
        "mode": "standard", "size": 11,
    }]}
    report = aggregate(summary)
    bot = report["standings"][0]
    assert bot["player"] == "TournamentBot"
    assert bot["wins"] == 1 and bot["losses"] == 0
    assert bot["points"] == 4 and bot["positions"] == {"1": 1}
    assert "standard-11" in report["by_format"]
    assert "<svg" in svg_chart(report)
