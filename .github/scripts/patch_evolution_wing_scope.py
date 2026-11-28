from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "src/main/java/com/kuku/heavenhell/client/render/RaceWingsLayer.java"
source = path.read_text(encoding="utf-8")
line = "        boolean transformed = status.isAwakened() || status.isEvolved();\n"
count = source.count(line)
if count > 2:
    raise SystemExit(f"Expected at most two Evolution transform declarations, found {count}")
if count == 2:
    first = source.find(line)
    second = source.find(line, first + len(line))
    source = source[:second] + source[second + len(line):]
    path.write_text(source, encoding="utf-8")
elif count == 1:
    pass
else:
    raise SystemExit("Expected an Evolution transform declaration in RaceWingsLayer")
if source.count(line) != 1:
    raise SystemExit("Evolution wing renderer still has duplicate transform declarations")
print("Fixed Evolution wing renderer variable scope.")
