"""
分享结果 — 生成 Wordle 风格的 emoji 网格
"""
from poketypes import GuessRecord


def format_share_result(
    guesses_with_hints: list[GuessRecord],
    max_guesses: int,
    target_name: str,
    target_name_en: str,
    target_id: int,
    won: bool,
    generation_label: str = "",
) -> str:
    guess_count = len(guesses_with_hints)
    if won:
        header = f"Pokémonle #{target_id} {guess_count}/{max_guesses}"
    else:
        header = f"Pokémonle #{target_id} X/{max_guesses}"

    all_labels: list[str] = []
    seen: set[str] = set()
    for _, hints in guesses_with_hints:
        for h in hints:
            label = h[0]
            if label not in seen:
                all_labels.append(label)
                seen.add(label)

    level_to_square = {
        "exact": "🟩",
        "close": "🟨",
        "partial": "🟨",
        "far": "⬛",
        "miss": "⬛",
    }

    rows: list[str] = []
    for _, hints in guesses_with_hints:
        hint_map = {}
        for h in hints:
            label = h[0]
            level = h[2]
            hint_map[label] = level
        row = " ".join(level_to_square.get(hint_map.get(l, ""), "⬜") for l in all_labels)
        rows.append(row)

    grid = "\n".join(rows)
    lines = [header, grid]
    if generation_label:
        lines.append(f"世代: {generation_label}")
    lines.append(f"答案: {target_name} ({target_name_en}) #{target_id:04d}")
    return "\n".join(lines)
