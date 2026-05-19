# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'src'

# Literal mojibake strings as they appear in corrupted files (UTF-8 decoded Latin-1)
REPLACEMENTS = [
    ('\xf0\x9f\x8c\xb1'.decode('latin-1') if False else 'ðŸŒ±', '\U0001f331'),
]

# Use explicit: the four-character mojibake sequence
MOJI = [
    ('ðŸŒ±', '\U0001f331'),
    ('ðŸšš', ''),
    ('âš\xa0', '\u26a0'),
    ('âš ', '\u26a0 '),
    ('Â·', '\u00b7'),
    ('â€"', '\u2014'),
    ('â€¦', '\u2026'),
    ('â†’', '\u2192'),
    ('â†‘', '\u2191'),
    ('â–¸', '\u25b8'),
    ('â”€', '--'),
]

def fix_file(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    orig = text
    for bad, good in MOJI:
        text = text.replace(bad, good)
    if text != orig:
        path.write_text(text, encoding='utf-8')
        return True
    return False

def main():
    n = 0
    for ext in ('*.js', '*.jsx'):
        for path in ROOT.rglob(ext):
            if fix_file(path):
                print('fixed', path.relative_to(ROOT.parent))
                n += 1
    print('total', n)

if __name__ == '__main__':
    main()
