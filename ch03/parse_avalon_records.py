from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path


WINNER_RE = re.compile(r"^[✨😈]\s*(好人|邪惡)陣營獲勝！\s*$")
ROLE_RE = re.compile(r"^(⚪|🔴)\s*(.+?)：\s*(.+?)\s*$")

COLUMN_LABELS = {
    "game_id": "場次編號",
    "player_count": "玩家人數",
    "player": "玩家",
    "role": "角色",
    "faction": "所屬陣營",
    "winning_faction": "獲勝陣營",
    "won": "是否獲勝",
}

PLAYER_ALIASES = {
    "小小狗子": "A",
    "b26415780": "B",
    "Teddy": "C",
    "nicole": "D",
    "球球": "E",
    "狗狗狗狗狗狗": "F",
    "hou": "G",
    "Ming": "H",
}

ROLE_ORDER = {
    role: order
    for order, role in enumerate(
        ["梅林", "派西維爾", "亞瑟的忠誠僕人", "刺客", "莫甘娜", "奧伯倫"]
    )
}


def parse_records(text: str) -> list[dict[str, object]]:
    """將阿瓦隆結算文字轉成「每位玩家一列」的長表格式。"""
    games: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    reading_roles = False

    def finish_game() -> None:
        nonlocal current, reading_roles
        if current is None:
            return

        players = current["players"]
        if not current["winning_faction"]:
            raise ValueError(f"第 {current['game_id']} 場找不到獲勝陣營")
        if not players:
            raise ValueError(f"第 {current['game_id']} 場找不到角色揭曉資料")

        current["player_count"] = len(players)
        games.append(current)
        current = None
        reading_roles = False

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()

        if line == "⚔️ 遊戲結束":
            finish_game()
            current = {
                "game_id": len(games) + 1,
                "winning_faction": "",
                "players": [],
            }
            continue

        if current is None:
            continue

        winner_match = WINNER_RE.match(line)
        if winner_match:
            current["winning_faction"] = winner_match.group(1)
            continue

        if line == "🔍 角色揭曉：":
            reading_roles = True
            continue

        if reading_roles:
            if not line:
                finish_game()
                continue

            role_match = ROLE_RE.match(line)
            if role_match:
                marker, player, role = role_match.groups()
                faction = "好人" if marker == "⚪" else "邪惡"
                current["players"].append(
                    {
                        "player": player,
                        "role": role,
                        "faction": faction,
                    }
                )
            elif line.startswith(("⚪", "🔴")):
                raise ValueError(f"第 {line_number} 行的角色資料格式無法辨識：{line}")

    finish_game()

    rows: list[dict[str, object]] = []
    for game in games:
        winning_faction = str(game["winning_faction"])
        for player in game["players"]:
            rows.append(
                {
                    "game_id": game["game_id"],
                    "player_count": game["player_count"],
                    "player": PLAYER_ALIASES.get(
                        str(player["player"]), str(player["player"])
                    ),
                    "role": player["role"],
                    "faction": player["faction"],
                    "winning_faction": winning_faction,
                    "won": player["faction"] == winning_faction,
                }
            )

    alias_order = {alias: order for order, alias in enumerate(PLAYER_ALIASES.values())}
    rows.sort(
        key=lambda row: (
            int(row["game_id"]),
            alias_order.get(str(row["player"]), len(alias_order)),
            str(row["player"]),
        )
    )
    return rows


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(COLUMN_LABELS.values())
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    label: ("是" if row[key] else "否") if key == "won" else row[key]
                    for key, label in COLUMN_LABELS.items()
                }
            )


def percentage(numerator: int, denominator: int) -> float | None:
    """回傳百分比；分母為零時回傳 None，輸出到 CSV 時會呈現空白。"""
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 2)


def calculate_player_summary(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["player"])].append(row)

    player_order = {
        alias: order for order, alias in enumerate(PLAYER_ALIASES.values())
    }
    summary: list[dict[str, object]] = []
    for player in sorted(
        grouped,
        key=lambda name: (player_order.get(name, len(player_order)), name),
    ):
        player_rows = grouped[player]
        total_games = len(player_rows)
        total_wins = sum(bool(row["won"]) for row in player_rows)
        good_rows = [row for row in player_rows if row["faction"] == "好人"]
        evil_rows = [row for row in player_rows if row["faction"] == "邪惡"]
        good_wins = sum(bool(row["won"]) for row in good_rows)
        evil_wins = sum(bool(row["won"]) for row in evil_rows)

        summary.append(
            {
                "玩家": player,
                "總場數": total_games,
                "總勝場": total_wins,
                "總勝率(%)": percentage(total_wins, total_games),
                "好人場數": len(good_rows),
                "好人勝場": good_wins,
                "好人勝率(%)": percentage(good_wins, len(good_rows)),
                "邪惡場數": len(evil_rows),
                "邪惡勝場": evil_wins,
                "邪惡勝率(%)": percentage(evil_wins, len(evil_rows)),
            }
        )

    return summary


def calculate_player_role_stats(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    total_games = Counter(str(row["player"]) for row in rows)
    grouped: defaultdict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["player"]), str(row["role"]))].append(row)

    player_order = {
        alias: order for order, alias in enumerate(PLAYER_ALIASES.values())
    }
    stats: list[dict[str, object]] = []
    for player, role in sorted(
        grouped,
        key=lambda item: (
            player_order.get(item[0], len(player_order)),
            ROLE_ORDER.get(item[1], len(ROLE_ORDER)),
            item[1],
        ),
    ):
        role_rows = grouped[(player, role)]
        appearances = len(role_rows)
        wins = sum(bool(row["won"]) for row in role_rows)
        stats.append(
            {
                "玩家": player,
                "角色": role,
                "玩家總場數": total_games[player],
                "角色出場數": appearances,
                "角色出場率(%)": percentage(appearances, total_games[player]),
                "角色勝場": wins,
                "角色勝率(%)": percentage(wins, appearances),
            }
        )

    return stats


def calculate_role_gap_stats(
    rows: list[dict[str, object]], large_gap_threshold: float = 20.0
) -> tuple[list[dict[str, object]], dict[str, float]]:
    """計算角色勝率相對於個人及同陣營全團勝率的百分點落差。"""
    player_rows: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    faction_rows: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    player_role_rows: defaultdict[
        tuple[str, str], list[dict[str, object]]
    ] = defaultdict(list)

    for row in rows:
        player = str(row["player"])
        role = str(row["role"])
        faction = str(row["faction"])
        player_rows[player].append(row)
        faction_rows[faction].append(row)
        player_role_rows[(player, role)].append(row)

    player_rates = {
        player: percentage(
            sum(bool(row["won"]) for row in grouped_rows), len(grouped_rows)
        )
        for player, grouped_rows in player_rows.items()
    }
    faction_rates = {
        faction: percentage(
            sum(bool(row["won"]) for row in grouped_rows), len(grouped_rows)
        )
        for faction, grouped_rows in faction_rows.items()
    }

    player_order = {
        alias: order for order, alias in enumerate(PLAYER_ALIASES.values())
    }
    results: list[dict[str, object]] = []
    for player, role in sorted(
        player_role_rows,
        key=lambda item: (
            player_order.get(item[0], len(player_order)),
            ROLE_ORDER.get(item[1], len(ROLE_ORDER)),
            item[1],
        ),
    ):
        grouped_rows = player_role_rows[(player, role)]
        factions = {str(row["faction"]) for row in grouped_rows}
        if len(factions) != 1:
            raise ValueError(f"角色 {role} 在資料中對應到多個陣營：{factions}")

        faction = factions.pop()
        role_wins = sum(bool(row["won"]) for row in grouped_rows)
        role_rate = percentage(role_wins, len(grouped_rows))
        player_rate = player_rates[player]
        faction_rate = faction_rates[faction]
        if role_rate is None or player_rate is None or faction_rate is None:
            raise ValueError("有出場紀錄的勝率不應為空值")

        personal_gap = round(role_rate - player_rate, 2)
        faction_gap = round(role_rate - faction_rate, 2)
        is_large = (
            abs(personal_gap) >= large_gap_threshold
            or abs(faction_gap) >= large_gap_threshold
        )

        if personal_gap > 0 and faction_gap > 0:
            interpretation = "雙正：超出個人與陣營基準"
        elif personal_gap < 0 and faction_gap < 0:
            interpretation = "雙負：可能尚未熟悉角色"
        else:
            interpretation = "混合或持平：兩項基準結論不一致"

        if len(grouped_rows) <= 2:
            sample_note = "樣本極少"
        elif len(grouped_rows) <= 4:
            sample_note = "樣本偏少"
        else:
            sample_note = ""

        results.append(
            {
                "玩家": player,
                "角色": role,
                "陣營": faction,
                "角色出場數": len(grouped_rows),
                "角色勝場": role_wins,
                "角色勝率(%)": role_rate,
                "個人總勝率(%)": player_rate,
                "角色勝率－個人勝率(百分點)": personal_gap,
                "全團同陣營勝率(%)": faction_rate,
                "角色勝率－陣營勝率(百分點)": faction_gap,
                "方向判讀": interpretation,
                "大落差標記": "是" if is_large else "",
                "樣本提醒": sample_note,
            }
        )

    return results, faction_rates


def poisson_binomial_distribution(probabilities: list[float]) -> list[float]:
    """以動態規劃計算不同單場機率下，總出現次數的完整機率分布。"""
    distribution = [1.0]
    for probability in probabilities:
        updated = [0.0] * (len(distribution) + 1)
        for count, mass in enumerate(distribution):
            updated[count] += mass * (1.0 - probability)
            updated[count + 1] += mass * probability
        distribution = updated
    return distribution


def calculate_role_draw_comparison(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """比較各玩家角色實際出場數與逐場配置推得的理論期望。"""
    games: defaultdict[int, list[dict[str, object]]] = defaultdict(list)
    player_rows: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        games[int(row["game_id"])].append(row)
        player_rows[str(row["player"])].append(row)

    player_order = {
        alias: order for order, alias in enumerate(PLAYER_ALIASES.values())
    }
    results: list[dict[str, object]] = []

    for player in sorted(
        player_rows,
        key=lambda name: (player_order.get(name, len(player_order)), name),
    ):
        participated_rows = player_rows[player]
        game_ids = sorted(int(row["game_id"]) for row in participated_rows)
        actual_counts = Counter(str(row["role"]) for row in participated_rows)
        possible_roles = {
            str(game_row["role"])
            for game_id in game_ids
            for game_row in games[game_id]
        }

        for role in sorted(
            possible_roles,
            key=lambda name: (ROLE_ORDER.get(name, len(ROLE_ORDER)), name),
        ):
            probabilities: list[float] = []
            for game_id in game_ids:
                game_rows = games[game_id]
                player_count = len(game_rows)
                role_copies = sum(
                    str(game_row["role"]) == role for game_row in game_rows
                )
                probabilities.append(role_copies / player_count)

            expected_count = sum(probabilities)
            variance = sum(p * (1.0 - p) for p in probabilities)
            observed_count = actual_counts[role]
            distribution = poisson_binomial_distribution(probabilities)
            lower_tail = sum(distribution[: observed_count + 1])
            upper_tail = sum(distribution[observed_count:])
            two_sided_p = min(1.0, 2.0 * min(lower_tail, upper_tail))
            z_score = (
                (observed_count - expected_count) / sqrt(variance)
                if variance > 0
                else None
            )

            if observed_count > expected_count:
                direction = "偏高"
            elif observed_count < expected_count:
                direction = "偏低"
            else:
                direction = "符合期望"

            if two_sided_p < 0.05:
                statistical_result = f"未校正下顯著{direction}"
            elif two_sided_p < 0.10:
                statistical_result = f"接近顯著：{direction}"
            else:
                statistical_result = "未達顯著"

            if z_score is not None and abs(z_score) >= 1.0:
                fun_flag = f"值得聊聊：{direction}"
            else:
                fun_flag = ""

            if total_games := len(game_ids):
                sample_note = "參與場數偏少" if total_games < 10 else ""

            results.append(
                {
                    "玩家": player,
                    "角色": role,
                    "參與場數": total_games,
                    "理論出場次數": round(expected_count, 2),
                    "實際出場次數": observed_count,
                    "次數落差": round(observed_count - expected_count, 2),
                    "理論平均機率(%)": round(expected_count / total_games * 100, 2),
                    "實際出場率(%)": round(observed_count / total_games * 100, 2),
                    "出場率落差(百分點)": round(
                        (observed_count - expected_count) / total_games * 100, 2
                    ),
                    "標準化落差(z)": round(z_score, 2) if z_score is not None else None,
                    "雙尾p值": round(two_sided_p, 4),
                    "方向": direction,
                    "統計判定": statistical_result,
                    "趣味標記": fun_flag,
                    "樣本提醒": sample_note,
                }
            )

    return results


def calculate_assignment_deviation(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """依玩家參與各場的實際角色配置，計算角色分配的理論期望與偏離。"""
    games: defaultdict[int, list[dict[str, object]]] = defaultdict(list)
    player_totals = Counter(str(row["player"]) for row in rows)
    actual_counts = Counter(
        (str(row["player"]), str(row["role"])) for row in rows
    )
    expected_counts: defaultdict[tuple[str, str], float] = defaultdict(float)

    for row in rows:
        games[int(row["game_id"])].append(row)

    for game_rows in games.values():
        role_counts = Counter(str(row["role"]) for row in game_rows)
        player_count = len(game_rows)
        role_probabilities = {
            role: count / player_count for role, count in role_counts.items()
        }
        for row in game_rows:
            player = str(row["player"])
            for role, probability in role_probabilities.items():
                expected_counts[(player, role)] += probability

    player_order = {
        alias: order for order, alias in enumerate(PLAYER_ALIASES.values())
    }
    results: list[dict[str, object]] = []
    for player, role in sorted(
        expected_counts,
        key=lambda item: (
            player_order.get(item[0], len(player_order)),
            ROLE_ORDER.get(item[1], len(ROLE_ORDER)),
            item[1],
        ),
    ):
        total = player_totals[player]
        actual = actual_counts[(player, role)]
        expected = expected_counts[(player, role)]
        actual_rate = actual / total * 100
        theoretical_rate = expected / total * 100
        results.append(
            {
                "玩家": player,
                "角色": role,
                "玩家總場數": total,
                "實際出現次數": actual,
                "理論期望次數": round(expected, 2),
                "實際出現率(%)": round(actual_rate, 2),
                "理論機率(%)": round(theoretical_rate, 2),
                "實際－理論偏離(百分點)": round(
                    actual_rate - theoretical_rate, 2
                ),
            }
        )

    return results


def calculate_player_report(
    player_summary: list[dict[str, object]],
    role_gap_stats: list[dict[str, object]],
    assignment_stats: list[dict[str, object]],
) -> list[dict[str, object]]:
    """建立使用者指定的每位玩家一列、角色資料逐行顯示的總表。"""
    gaps_by_player: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    assignments_by_player: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in role_gap_stats:
        gaps_by_player[str(row["玩家"])].append(row)
    for row in assignment_stats:
        assignments_by_player[str(row["玩家"])].append(row)

    report: list[dict[str, object]] = []
    for summary in player_summary:
        player = str(summary["玩家"])
        personal_gap_lines = [
            f'{row["角色"]}：{float(row["角色勝率－個人勝率(百分點)"]):+.2f} pp'
            f'（角色勝率 {float(row["角色勝率(%)"]):.2f}%）'
            for row in gaps_by_player[player]
        ]
        faction_gap_lines = [
            f'{row["角色"]}：{float(row["角色勝率－陣營勝率(百分點)"]):+.2f} pp'
            f'（{row["陣營"]}基準 {float(row["全團同陣營勝率(%)"]):.2f}%）'
            for row in gaps_by_player[player]
        ]
        assignment_lines = [
            f'{row["角色"]}：實際 {int(row["實際出現次數"])} 次／'
            f'理論 {float(row["理論期望次數"]):.2f} 次'
            f'（{float(row["實際－理論偏離(百分點)"]):+.2f} pp）'
            for row in assignments_by_player[player]
        ]
        report.append(
            {
                "玩家名稱": player,
                "總場數": int(summary["總場數"]),
                "總勝率": float(summary["總勝率(%)"]) / 100,
                "各角色勝率與自己整體勝率的落差": "\n".join(personal_gap_lines),
                "各角色勝率與全團陣營平均勝率的落差": "\n".join(faction_gap_lines),
                "各角色實際出現次數與理論機率的偏離程度": "\n".join(
                    assignment_lines
                ),
            }
        )

    return report


def write_records_csv(
    records: list[dict[str, object]], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0]) if records else []
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def validate_statistics(
    rows: list[dict[str, object]],
    player_summary: list[dict[str, object]],
    player_role_stats: list[dict[str, object]],
) -> None:
    """檢查分陣營與分角色統計能否完整回推逐場明細。"""
    row_counts = Counter(str(row["player"]) for row in rows)
    role_counts = Counter()
    for stat in player_role_stats:
        role_counts[str(stat["玩家"])] += int(stat["角色出場數"])

    for summary in player_summary:
        player = str(summary["玩家"])
        total_games = int(summary["總場數"])
        if int(summary["好人場數"]) + int(summary["邪惡場數"]) != total_games:
            raise ValueError(f"{player} 的分陣營場數無法加總為總場數")
        if row_counts[player] != total_games:
            raise ValueError(f"{player} 的總場數與逐場明細不一致")
        if role_counts[player] != total_games:
            raise ValueError(f"{player} 的分角色出場數無法加總為總場數")


def print_records(
    records: list[dict[str, object]], limit: int | None = None
) -> None:
    shown = records if limit is None else records[:limit]
    if not shown:
        print("（沒有資料）")
        return

    fieldnames = list(shown[0])
    display_rows = [
        {field: "—" if value is None else value for field, value in row.items()}
        for row in shown
    ]
    widths = {
        field: max(len(field), *(len(str(row[field])) for row in display_rows))
        for field in fieldnames
    }
    print(" | ".join(field.ljust(widths[field]) for field in fieldnames))
    print("-+-".join("-" * widths[field] for field in fieldnames))
    for row in display_rows:
        print(" | ".join(str(row[field]).ljust(widths[field]) for field in fieldnames))


def print_preview(rows: list[dict[str, object]], limit: int) -> None:
    fieldnames = list(COLUMN_LABELS.values())
    preview = [
        {
            label: ("是" if row[key] else "否") if key == "won" else row[key]
            for key, label in COLUMN_LABELS.items()
        }
        for row in rows[:limit]
    ]
    if not preview:
        print("（未要求預覽逐場明細）")
        return
    widths = {
        field: max(len(field), *(len(str(row[field])) for row in preview))
        for field in fieldnames
    }

    print(" | ".join(field.ljust(widths[field]) for field in fieldnames))
    print("-+-".join("-" * widths[field] for field in fieldnames))
    for row in preview:
        print(" | ".join(str(row[field]).ljust(widths[field]) for field in fieldnames))


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="解析阿瓦隆對局結算文字")
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / "阿瓦隆對局紀錄.txt",
        help="原始對局文字檔",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆對局結構化資料.csv",
        help="輸出的 CSV 檔",
    )
    parser.add_argument(
        "--player-output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆玩家勝率統計.csv",
        help="玩家整體與分陣營勝率 CSV",
    )
    parser.add_argument(
        "--role-output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆玩家角色統計.csv",
        help="玩家角色出場率與勝率 CSV",
    )
    parser.add_argument(
        "--gap-output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆玩家角色勝率落差.csv",
        help="角色勝率相對個人與陣營基準的落差 CSV",
    )
    parser.add_argument(
        "--draw-output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆玩家角色抽取機率比較.csv",
        help="角色實際出場次數與理論機率比較 CSV",
    )
    parser.add_argument(
        "--assignment-output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆角色分配偏離.csv",
        help="角色實際分配與理論機率偏離 CSV",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=script_dir.parent / "output" / "csv" / "阿瓦隆玩家綜合統計.csv",
        help="每位玩家一列的綜合統計 CSV",
    )
    parser.add_argument(
        "--large-gap-threshold",
        type=float,
        default=20.0,
        help="大落差標記門檻，單位為百分點",
    )
    parser.add_argument("--preview", type=int, default=10, help="預覽列數")
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8-sig")
    rows = parse_records(text)
    write_csv(rows, args.output)
    player_summary = calculate_player_summary(rows)
    player_role_stats = calculate_player_role_stats(rows)
    role_gap_stats, faction_rates = calculate_role_gap_stats(
        rows, large_gap_threshold=args.large_gap_threshold
    )
    role_draw_comparison = calculate_role_draw_comparison(rows)
    assignment_stats = calculate_assignment_deviation(rows)
    player_report = calculate_player_report(
        player_summary, role_gap_stats, assignment_stats
    )
    validate_statistics(rows, player_summary, player_role_stats)
    write_records_csv(player_summary, args.player_output)
    write_records_csv(player_role_stats, args.role_output)
    write_records_csv(role_gap_stats, args.gap_output)
    write_records_csv(role_draw_comparison, args.draw_output)
    write_records_csv(assignment_stats, args.assignment_output)
    write_records_csv(player_report, args.report_output)

    games_by_id = {
        int(row["game_id"]): int(row["player_count"])
        for row in rows
    }
    game_count = len(games_by_id)
    player_counts = Counter(games_by_id.values())
    print(f"解析完成：{game_count} 場、{len(rows)} 筆玩家紀錄")
    print(f"各人數場次：{dict(sorted(player_counts.items()))}")
    print("統計一致性檢查：通過")
    unmapped_players = sorted(
        {
            str(row["player"])
            for row in rows
            if str(row["player"]) not in PLAYER_ALIASES.values()
        }
    )
    if unmapped_players:
        print(f"未提供代號、保留原名：{', '.join(unmapped_players)}")
    print(f"逐場明細：{args.output.resolve()}")
    print(f"玩家勝率：{args.player_output.resolve()}")
    print(f"角色統計：{args.role_output.resolve()}")
    print(f"角色落差：{args.gap_output.resolve()}")
    print(f"角色抽取比較：{args.draw_output.resolve()}")
    print(f"角色分配偏離：{args.assignment_output.resolve()}")
    print(f"玩家綜合統計：{args.report_output.resolve()}")
    print(
        "全團陣營基準："
        + "、".join(
            f"{faction} {rate}%" for faction, rate in sorted(faction_rates.items())
        )
    )
    print()
    print("玩家整體與分陣營勝率：")
    print_records(player_summary)
    print()
    print("玩家角色統計（前 12 筆）：")
    print_records(player_role_stats, limit=12)
    print()
    print(
        f"大落差角色（任一落差絕對值達 {args.large_gap_threshold:g} 個百分點）："
    )
    print_records(
        [row for row in role_gap_stats if row["大落差標記"] == "是"]
    )
    print()
    print("角色抽取機率的趣味標記（未校正多重比較）：")
    print_records(
        [row for row in role_draw_comparison if row["趣味標記"]]
    )
    print()
    print("逐場明細預覽：")
    print_preview(rows, args.preview)


if __name__ == "__main__":
    main()
