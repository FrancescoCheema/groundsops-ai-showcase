import re
import sys
from pathlib import Path

from PIL import Image

root = Path("docs/assets")
problems: list[str] = []
email = re.compile(rb"\b[A-Z0-9][A-Z0-9._%+-]*@[A-Z0-9][A-Z0-9-]*(?:\.[A-Z0-9-]+)*\.[A-Z]{2,}\b", re.I)
for path in root.rglob("*") if root.exists() else []:
    if not path.is_file():
        continue
    data = path.read_bytes()
    if email.search(data):
        problems.append(f"embedded email-like text: {path}")
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(path) as image:
                if image.getexif():
                    problems.append(f"EXIF metadata present: {path}")
        except OSError:
            problems.append(f"invalid image: {path}")
if problems:
    print("\n".join(problems), file=sys.stderr)
    raise SystemExit(1)
print("Public asset metadata scan passed. Manual visual review is still required.")
