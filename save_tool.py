#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pycryptodome"]
# ///
"""
ThankYouForYourApplication 存档工具

交互模式 (直接运行):
    python save_tool.py

命令行模式:
    python save_tool.py d2json  <输入文件或目录> [输出目录]
    python save_tool.py d2sav   <输入文件或目录> [输出目录]
    python save_tool.py peek    <.sav 文件>
"""

import sys
import os
import json
import glob
from pathlib import Path

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import pad, unpad
    except ImportError:
        print("错误: 需要安装 pycryptodome")
        print("  pip install pycryptodome")
        sys.exit(1)

# ─── 常量 (对应 GameSaveCrypt.cs) ───
AES_KEY = b"zhangsanwangba12"
AES_IV = b"zhangsanwangba12"
AES_MODE = AES.MODE_CBC

# ─── 默认存档目录 ───
DEFAULT_SAVE_DIR = (
    Path.home()
    / r"AppData\LocalLow\IceLemonTea Studio\ThankYouForYourApplication\Save"
)


# ═══════════════════════════════════════════
#  加解密
# ═══════════════════════════════════════════

def decrypt_sav(data: bytes) -> str:
    """解密 .sav 文件，返回 JSON 字符串"""
    cipher = AES.new(AES_KEY, AES_MODE, AES_IV)
    decrypted = unpad(cipher.decrypt(data), AES.block_size)
    return decrypted.decode("utf-8")


def encrypt_json(json_str: str) -> bytes:
    """将 JSON 字符串加密为 .sav 格式的 bytes"""
    raw = json_str.encode("utf-8")
    cipher = AES.new(AES_KEY, AES_MODE, AES_IV)
    return cipher.encrypt(pad(raw, AES.block_size))


# ═══════════════════════════════════════════
#  存档读写
# ═══════════════════════════════════════════

def load_save(path: Path) -> dict:
    """读取存档文件 (自动识别 .sav / .json)"""
    if path.suffix == ".sav":
        with open(path, "rb") as f:
            return json.loads(decrypt_sav(f.read()))
    else:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def save_save(path: Path, data: dict) -> None:
    """写回存档文件 (按原始格式)"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    if path.suffix == ".sav":
        with open(path, "wb") as f:
            f.write(encrypt_json(json_str))
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(json_str)


# ═══════════════════════════════════════════
#  功能：导出为 JSON
# ═══════════════════════════════════════════

def export_to_json(src: Path) -> None:
    """将存档导出为同目录下的 .json 文件"""
    data = load_save(src)
    out = src.with_suffix(".json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已导出: {out}")


# ═══════════════════════════════════════════
#  功能：一键全满分评级
# ═══════════════════════════════════════════

def fix_ratings(src: Path) -> None:
    """将存档中所有天的评级设置为 0（全对/最佳）"""
    data = load_save(src)
    histories = data["settlementHistories"]["$values"]
    changed = 0
    for entry in histories:
        if entry.get("rating", 0) != 0:
            entry["rating"] = 0
            changed += 1
    save_save(src, data)
    print(f"✓ 共 {len(histories)} 天，修改了 {changed} 天的评级为 0")


def max_money(src: Path) -> None:
    """将余额设为最大值 (2147483647)"""
    data = load_save(src)
    old = data.get("money", 0)
    data["money"] = 2147483647
    save_save(src, data)
    print(f"✓ 余额: {old} → 2147483647")


def clear_bi(src: Path) -> None:
    """清空当前崩溃值 (BI) 及所有历史记录"""
    data = load_save(src)
    old_bi = data.get("BI", 0)
    data["BI"] = 0
    bi_hist = data.get("BIHistories", {}).get("$values", [])
    cleared = 0
    for entry in bi_hist:
        if entry.get("BI", 0) != 0:
            entry["BI"] = 0
            cleared += 1
    save_save(src, data)
    print(f"✓ 当前 BI: {old_bi} → 0，历史记录已清零 {cleared} 条")


# ═══════════════════════════════════════════
#  CLI 子命令 (原 save_converter.py 功能)
# ═══════════════════════════════════════════

def find_files(path: str, ext: str) -> list[str]:
    """在目录中查找指定扩展名的文件"""
    if os.path.isfile(path):
        return [path]
    files = glob.glob(os.path.join(path, "**", f"*{ext}"), recursive=True)
    return sorted(files)


def resolve_output(input_path: str, input_base: str, output_dir: str | None) -> str | None:
    if output_dir is None:
        return None
    rel = os.path.relpath(input_path, input_base)
    return os.path.join(output_dir, rel)


def cmd_d2json(args: list[str]) -> None:
    if not args:
        print("用法: save_tool.py d2json <输入文件或目录> [输出目录]")
        sys.exit(1)
    input_path, output_dir = args[0], (args[1] if len(args) > 1 else None)
    files = find_files(input_path, ".sav")
    if not files:
        print(f"未找到 .sav 文件: {input_path}")
        sys.exit(1)
    print(f"找到 {len(files)} 个 .sav 文件")
    for f in files:
        out = resolve_output(f, input_path if os.path.isdir(input_path) else "", output_dir)
        if out is None:
            out = str(Path(f).with_suffix(".json"))
        try:
            with open(f, "rb") as fh:
                json_str = decrypt_sav(fh.read())
            obj = json.loads(json_str)
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(obj, fh, indent=2, ensure_ascii=False)
            print(f"  ✓ {f} → {out}")
        except Exception as e:
            print(f"  ✗ {f} — 错误: {e}")


def cmd_d2sav(args: list[str]) -> None:
    if not args:
        print("用法: save_tool.py d2sav <输入文件或目录> [输出目录]")
        sys.exit(1)
    input_path, output_dir = args[0], (args[1] if len(args) > 1 else None)
    files = find_files(input_path, ".json")
    if not files:
        print(f"未找到 .json 文件: {input_path}")
        sys.exit(1)
    print(f"找到 {len(files)} 个 .json 文件")
    for f in files:
        out = resolve_output(f, input_path if os.path.isdir(input_path) else "", output_dir)
        if out is None:
            out = str(Path(f).with_suffix(".sav"))
        try:
            with open(f, "r", encoding="utf-8") as fh:
                json_str = fh.read()
            json.loads(json_str)  # 验证合法性
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "wb") as fh:
                fh.write(encrypt_json(json_str))
            print(f"  ✓ {f} → {out}")
        except Exception as e:
            print(f"  ✗ {f} — 错误: {e}")


def cmd_peek(args: list[str]) -> None:
    if not args:
        print("用法: save_tool.py peek <.sav 文件>")
        sys.exit(1)
    with open(args[0], "rb") as f:
        json_str = decrypt_sav(f.read())
    try:
        print(json.dumps(json.loads(json_str), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(json_str)


# ═══════════════════════════════════════════
#  交互模式
# ═══════════════════════════════════════════

def interactive() -> None:
    # 1. 搜索存档
    if not DEFAULT_SAVE_DIR.is_dir():
        print(f"存档目录不存在: {DEFAULT_SAVE_DIR}")
        sys.exit(1)

    files: list[Path] = sorted(
        p for p in DEFAULT_SAVE_DIR.iterdir() if p.suffix in (".sav", ".json")
    )
    if not files:
        print("存档目录中未找到任何存档文件")
        sys.exit(1)

    # 2. 选择存档
    print(f"存档目录: {DEFAULT_SAVE_DIR}\n")
    print("请选择存档:")
    for i, f in enumerate(files, 1):
        print(f"  [{i}] {f.name}")

    while True:
        try:
            choice = int(input("\n输入编号: "))
            if 1 <= choice <= len(files):
                break
        except (ValueError, EOFError):
            pass
        print("无效输入，请重试")

    selected = files[choice - 1]
    print(f"\n已选择: {selected.name}\n")

    # 3. 选择操作
    ACTIONS = [
        ("导出为 JSON", export_to_json),
        ("一键修改全满分评级", fix_ratings),
        ("一键最大余额", max_money),
        ("一键清空崩溃值 (BI)", clear_bi),
    ]

    print("请选择操作:")
    for i, (label, _) in enumerate(ACTIONS, 1):
        print(f"  [{i}] {label}")
    print(f"  [0] 退出")

    while True:
        try:
            action = int(input("\n输入编号: "))
            if action == 0:
                print("已退出")
                return
            if 1 <= action <= len(ACTIONS):
                break
        except (ValueError, EOFError):
            pass
        print("无效输入，请重试")

    print()
    ACTIONS[action - 1][1](selected)


# ═══════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════

CLI_COMMANDS = {
    "d2json": cmd_d2json,
    "d2sav": cmd_d2sav,
    "peek": cmd_peek,
}


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        interactive()
        return

    cmd = sys.argv[1]
    if cmd in ("-h", "--help"):
        print(__doc__)
        return

    if cmd not in CLI_COMMANDS:
        print(f"未知命令: {cmd}")
        print(f"可用命令: {', '.join(CLI_COMMANDS.keys())}")
        sys.exit(1)

    CLI_COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
