#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pycryptodome"]
# ///
"""
ResumePlease 游戏存档转换工具

存档格式: JSON → AES-CBC 加密 → .sav 二进制文件
密钥/IV: zhangsanwangba12 (16字节, 硬编码在 GameSaveCrypt.cs 中)

用法:
    sav 转 json:  python save_converter.py d2json <输入文件或目录> [输出目录]
    json 转 sav:  python save_converter.py d2sav  <输入文件或目录> [输出目录]
    查看存档:     python save_converter.py peek   <.sav文件>

示例:
    python save_converter.py d2json game_xxx.sav                  # 单文件转换
    python save_converter.py d2json ./Save/ ./json_output/        # 批量转换整个目录
    python save_converter.py d2sav  game_xxx.json                 # 单文件还原
    python save_converter.py d2sav  ./json_output/ ./restored/    # 批量还原目录
    python save_converter.py peek   game_xxx.sav                  # 快速查看存档内容
"""

import sys
import os
import json
import glob
import base64
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
AES_KEY = b"zhangsanwangba12"  # 16 bytes
AES_IV  = b"zhangsanwangba12"  # 16 bytes, 与 Key 相同
AES_MODE = AES.MODE_CBC

# 需要转换回 sav 时, 这些字段要从字符串转回 DateTime 对象
# Newtonsoft.Json + TypeNameHandling.All 序列化 DateTime 时用 ISO 格式字符串,
# 但还原时只需保证 JSON 结构一致即可, Python 的 json 模块能正确处理。


def decrypt_sav(data: bytes) -> str:
    """解密 .sav 文件, 返回 JSON 字符串"""
    cipher = AES.new(AES_KEY, AES_MODE, AES_IV)
    decrypted = unpad(cipher.decrypt(data), AES.block_size)
    return decrypted.decode("utf-8")


def encrypt_json(json_str: str) -> bytes:
    """将 JSON 字符串加密为 .sav 格式的 bytes"""
    raw = json_str.encode("utf-8")
    cipher = AES.new(AES_KEY, AES_MODE, AES_IV)
    return cipher.encrypt(pad(raw, AES.block_size))


def sav_to_json(input_path: str, output_path: str | None = None) -> str:
    """单个 .sav 文件转为 .json 文件, 返回输出路径"""
    with open(input_path, "rb") as f:
        data = f.read()

    json_str = decrypt_sav(data)

    # 尝试格式化 JSON
    try:
        obj = json.loads(json_str)
        formatted = json.dumps(obj, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # 有些 sav 可能不是标准 JSON, 直接保存原始解密文本
        formatted = json_str

    if output_path is None:
        output_path = str(Path(input_path).with_suffix(".json"))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatted)

    return output_path


def json_to_sav(input_path: str, output_path: str | None = None) -> str:
    """单个 .json 文件转回 .sav 格式, 返回输出路径"""
    with open(input_path, "r", encoding="utf-8") as f:
        json_str = f.read()

    # 验证 JSON 合法性
    json.loads(json_str)

    encrypted = encrypt_json(json_str)

    if output_path is None:
        output_path = str(Path(input_path).with_suffix(".sav"))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(encrypted)

    return output_path


def peek_sav(input_path: str) -> None:
    """查看 .sav 文件的 JSON 内容 (不写文件)"""
    with open(input_path, "rb") as f:
        data = f.read()

    json_str = decrypt_sav(data)
    try:
        obj = json.loads(json_str)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(json_str)


def find_sav_files(path: str) -> list[str]:
    """在目录中查找所有 .sav 文件"""
    if os.path.isfile(path):
        return [path]
    patterns = [os.path.join(path, "**", "*.sav")]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    return sorted(files)


def find_json_files(path: str) -> list[str]:
    """在目录中查找所有 .json 文件"""
    if os.path.isfile(path):
        return [path]
    patterns = [os.path.join(path, "**", "*.json")]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    return sorted(files)


def resolve_output(input_path: str, input_base: str, output_dir: str | None) -> str | None:
    """根据输入路径和输出目录计算输出路径"""
    if output_dir is None:
        return None  # 使用默认路径 (同目录)
    rel = os.path.relpath(input_path, input_base)
    return os.path.join(output_dir, rel)


def cmd_d2json(args: list[str]) -> None:
    """sav → json"""
    if not args:
        print("用法: save_converter.py d2json <输入文件或目录> [输出目录]")
        sys.exit(1)

    input_path = args[0]
    output_dir = args[1] if len(args) > 1 else None

    files = find_sav_files(input_path)
    if not files:
        print(f"未找到 .sav 文件: {input_path}")
        sys.exit(1)

    print(f"找到 {len(files)} 个 .sav 文件")
    for f in files:
        out = resolve_output(f, input_path if os.path.isdir(input_path) else "", output_dir)
        # 如果未指定输出目录且输入是目录, 保存到同目录
        if out is None:
            out = str(Path(f).with_suffix(".json"))
        try:
            result = sav_to_json(f, out)
            print(f"  ✓ {f} → {result}")
        except Exception as e:
            print(f"  ✗ {f} — 错误: {e}")


def cmd_d2sav(args: list[str]) -> None:
    """json → sav"""
    if not args:
        print("用法: save_converter.py d2sav <输入文件或目录> [输出目录]")
        sys.exit(1)

    input_path = args[0]
    output_dir = args[1] if len(args) > 1 else None

    files = find_json_files(input_path)
    if not files:
        print(f"未找到 .json 文件: {input_path}")
        sys.exit(1)

    print(f"找到 {len(files)} 个 .json 文件")
    for f in files:
        out = resolve_output(f, input_path if os.path.isdir(input_path) else "", output_dir)
        if out is None:
            out = str(Path(f).with_suffix(".sav"))
        try:
            result = json_to_sav(f, out)
            print(f"  ✓ {f} → {result}")
        except Exception as e:
            print(f"  ✗ {f} — 错误: {e}")


def cmd_peek(args: list[str]) -> None:
    """查看 sav 文件内容"""
    if not args:
        print("用法: save_converter.py peek <.sav文件>")
        sys.exit(1)

    peek_sav(args[0])


def cmd_help() -> None:
    print(__doc__)


COMMANDS = {
    "d2json": cmd_d2json,
    "d2sav":  cmd_d2sav,
    "peek":   cmd_peek,
    "help":   lambda _: cmd_help(),
}


def main():
    # Windows 终端 UTF-8 兼容
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        cmd_help()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"未知命令: {cmd}")
        print(f"可用命令: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
