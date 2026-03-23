from __future__ import annotations

from pathlib import Path


def load_block(skill_dir: Path, name: str) -> str:
    return (skill_dir / 'assets' / 'blocks' / f'{name}.html').read_text(encoding='utf-8-sig')
