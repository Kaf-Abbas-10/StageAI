"""Runs only under the separately configured upstream inference interpreter."""
import sys
from pathlib import Path

repo=Path(__file__).resolve().parents[1]/"upstream/WorldBuilder"
sys.path.insert(0,str(repo))
from main import process_image

if __name__=="__main__":
    process_image(sys.argv[1],sys.argv[2],detector="qwen",quality=sys.argv[3])

