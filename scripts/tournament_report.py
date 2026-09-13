"""Summarize four-snake practice matches and create a dependency-free SVG chart."""
import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path


PLAYERS = ("TournamentBot", "Opponent1", "Opponent2", "Opponent3")


def placement_for_match(record):
    placements = record.get("placements")
    if placements:
        return placements
    result = record.get("result", {})
    winner = result.get("winnerName")
    deaths = record.get("deaths", {})
    ordered = [winner] if winner in PLAYERS else []
    ordered.extend(sorted(
        (name for name in PLAYERS if name != winner and name in deaths),
        key=lambda name: (deaths[name].get("turn", -1), name), reverse=True,
    ))
    ordered.extend(name for name in PLAYERS if name not in ordered)
    return {name: index + 1 for index, name in enumerate(ordered)}


def aggregate(summary, include_formats=True):
    rows = summary.get("matches", [])
    stats = {player: {"matches": 0, "wins": 0, "losses": 0,
                      "points": 0, "positions": Counter(),
                      "average_position": 0.0}
             for player in PLAYERS}
    for row in rows:
        placements = placement_for_match(row)
        winner = row.get("result", {}).get("winnerName")
        for player in PLAYERS:
            position = int(placements[player])
            item = stats[player]
            item["matches"] += 1
            item["wins"] += int(player == winner or position == 1)
            item["losses"] += int(position != 1)
            item["points"] += len(PLAYERS) - position + 1
            item["positions"][str(position)] += 1
    for item in stats.values():
        if item["matches"]:
            total = sum(int(pos) * count for pos, count in item["positions"].items())
            item["average_position"] = round(total / item["matches"], 3)
        item["positions"] = dict(sorted(item["positions"].items(), key=lambda pair: int(pair[0])))
    standings = sorted(stats.items(), key=lambda pair: (-pair[1]["points"], pair[1]["average_position"], pair[0]))
    return {
        "matches": len(rows),
        "standings": [dict(player=player, rank=index + 1, **values) for index, (player, values) in enumerate(standings)],
        "by_format": format_summary(rows) if include_formats else {},
    }


def format_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[f"{row.get('mode', 'unknown')}-{row.get('size', '?')}"] .append(row)
    result = {}
    for key, matches in sorted(grouped.items()):
        result[key] = aggregate({"matches": matches}, include_formats=False)["standings"]
    return result


def svg_chart(report):
    width, height = 1120, 680
    left, top, chart_w, chart_h = 90, 90, 970, 390
    standings = report["standings"]
    max_matches = max((item["matches"] for item in standings), default=1)
    max_value = max(max_matches, max((item["points"] for item in standings), default=1))
    colors = {"1": "#16a34a", "2": "#2563eb", "3": "#f59e0b", "4": "#dc2626"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#f8fafc"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#172033}.title{font-size:24px;font-weight:700}.label{font-size:14px}.small{font-size:12px}</style>',
             '<text x="90" y="42" class="title">Four-snake tournament results</text>',
             '<text x="90" y="66" class="small">Wins, points, and finishing positions across practice matches</text>']
    bar_w = chart_w / max(len(standings), 1) - 34
    for index, item in enumerate(standings):
        x = left + index * (chart_w / max(len(standings), 1)) + 18
        wins_h = item["wins"] / max_value * chart_h
        points_h = item["points"] / max_value * chart_h
        y_wins = top + chart_h - wins_h
        y_points = top + chart_h - points_h
        parts.append(f'<rect x="{x:.1f}" y="{y_points:.1f}" width="{bar_w/2:.1f}" height="{points_h:.1f}" fill="#7c3aed" opacity=".8"/>')
        parts.append(f'<rect x="{x+bar_w/2+4:.1f}" y="{y_wins:.1f}" width="{bar_w/2:.1f}" height="{wins_h:.1f}" fill="#16a34a"/>')
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{top+chart_h+24}" text-anchor="middle" class="label">{html.escape(item["player"])}</text>')
        parts.append(f'<text x="{x+bar_w/4:.1f}" y="{max(y_points-6, top+12):.1f}" text-anchor="middle" class="small">{item["points"]} pts</text>')
        parts.append(f'<text x="{x+bar_w*3/4+4:.1f}" y="{max(y_wins-6, top+12):.1f}" text-anchor="middle" class="small">{item["wins"]} W</text>')
        base_y = 570
        stack_x = x
        for position in ("1", "2", "3", "4"):
            count = item["positions"].get(position, 0)
            segment_w = bar_w * count / max(item["matches"], 1)
            if segment_w:
                parts.append(f'<rect x="{stack_x:.1f}" y="{base_y}" width="{segment_w:.1f}" height="22" fill="{colors[position]}"/>')
                stack_x += segment_w
    parts.append(f'<line x1="{left}" y1="{top+chart_h}" x2="{left+chart_w}" y2="{top+chart_h}" stroke="#64748b"/>')
    parts.append('<text x="90" y="535" class="label">Finishing-position distribution</text>')
    legend_x = 360
    for position in ("1", "2", "3", "4"):
        parts.append(f'<rect x="{legend_x}" y="522" width="14" height="14" fill="{colors[position]}"/>')
        parts.append(f'<text x="{legend_x+20}" y="534" class="small">{position}{"st" if position == "1" else "nd" if position == "2" else "rd" if position == "3" else "th"}</text>')
        legend_x += 58
    parts.append('<text x="90" y="630" class="small">Purple = tournament points (4/3/2/1); green = wins; stacked strip = placements.</text></svg>')
    return "\n".join(parts)


def markdown_report(report):
    lines = ["# Four-snake tournament report", "", f"Matches: **{report['matches']}**", "", "## Standings", "", "| Rank | Player | Wins | Losses | Points | Average position | 1st | 2nd | 3rd | 4th |", "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for item in report["standings"]:
        pos = item["positions"]
        lines.append(f"| {item['rank']} | {item['player']} | {item['wins']} | {item['losses']} | {item['points']} | {item['average_position']} | {pos.get('1', 0)} | {pos.get('2', 0)} | {pos.get('3', 0)} | {pos.get('4', 0)} |")
    lines += ["", "## Visual", "", "![Tournament chart](tournament-results.svg)", "", "Format-specific standings are included in `tournament-results.json`."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", help="practice summary.json")
    parser.add_argument("--output", default=None, help="directory for report files")
    args = parser.parse_args()
    summary_path = Path(args.summary)
    output = Path(args.output) if args.output else summary_path.parent
    output.mkdir(parents=True, exist_ok=True)
    report = aggregate(json.loads(summary_path.read_text()))
    (output / "tournament-results.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "tournament-results.md").write_text(markdown_report(report))
    (output / "tournament-results.svg").write_text(svg_chart(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
