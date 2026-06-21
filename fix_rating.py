"""一键将存档中所有天的评级设置为 0（全对/最佳）"""

import json
from pathlib import Path

SAVE_PATH = Path.home() / r"AppData\LocalLow\IceLemonTea Studio\ThankYouForYourApplication\Save\game_00000000-0000-0000-0000-000000000000.json"


def main():
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    histories = data["settlementHistories"]["$values"]
    changed = 0
    for entry in histories:
        if entry.get("rating", 0) != 0:
            entry["rating"] = 0
            changed += 1

    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"共 {len(histories)} 天，修改了 {changed} 天的评级为 0")


if __name__ == "__main__":
    main()
