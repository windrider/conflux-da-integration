#!/usr/bin/env python3
"""Sync DASigners / DAEntrance addresses from Hardhat deploy output into da-node configs."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDRESSES_JSON = Path(
    os.environ.get(
        "DEPLOYMENTS_JSON",
        ROOT / "da-contract" / "0g-da-contract" / "deployments" / "zg" / "da-addresses.json",
    )
)
DA_NODE_DIR = Path(os.environ.get("DA_NODE_DIR", ROOT / "da-node"))
CONFIG_NAMES = ("config.toml", "config2.toml", "config3.toml")


def main() -> int:
    if not ADDRESSES_JSON.is_file():
        print(f"Missing {ADDRESSES_JSON} — run contract deploy first.", file=sys.stderr)
        return 1

    data = json.loads(ADDRESSES_JSON.read_text())
    signers = data["DASigners"]
    entrance = data["DAEntrance"]

    for name in CONFIG_NAMES:
        path = DA_NODE_DIR / name
        if not path.is_file():
            print(f"Skip missing {path}")
            continue
        text = path.read_text()
        text = re.sub(
            r'^da_entrance_address = ".*"$',
            f'da_entrance_address = "{entrance}"',
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r'^da_signers_address = ".*"$',
            f'da_signers_address = "{signers}"',
            text,
            flags=re.MULTILINE,
        )
        path.write_text(text)
        print(f"Updated {path}")

    print(f"DASigners={signers}")
    print(f"DAEntrance={entrance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
