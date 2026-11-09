"""Print a stretch of a normalized source text: peek.py SRC [start-text] [chars]"""
import sys
sys.argv, args = [sys.argv[0]], sys.argv[1:]
import build
text = build.source(args[0])
start = text.find(args[1]) if len(args) > 1 and args[1] else 0
n = int(args[2]) if len(args) > 2 else 4000
print(text[max(0, start):max(0, start) + n])
