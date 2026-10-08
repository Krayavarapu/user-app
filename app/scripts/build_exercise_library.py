"""Build ``app/data/exercise_library/exercises_v1.json`` from the curation table.

Developer tool, not run in production (production only runs the committed JSON through the
seeder). Output is deterministic for a given source snapshot, so re-running produces no diff.

    python -m app.scripts.build_exercise_library              # downloads the pinned snapshot
    python -m app.scripts.build_exercise_library --source /path/to/exercises.json
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from app.scripts.exercise_curation import PICKS, Pick
from app.services.exercise_library.seed import DATA_DIR, DEFAULT_EQUIPMENT_PATH
from app.services.exercise_library.tagging import (
    derive_contraindications,
    derive_default_tempo,
    derive_goal_tags,
    derive_impact_level,
)
from app.services.exercise_library.vocabulary import SOURCE_MUSCLE_MAP

SOURCE_REPO = "https://github.com/yuhonas/free-exercise-db"
SOURCE_COMMIT = "f00c92c7dcf1216a928a52c3706c7ce8e2f71ed5"
SOURCE_URL = (
    f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/{SOURCE_COMMIT}/dist/exercises.json"
)
OUTPUT_PATH = DATA_DIR / "exercises_v1.json"
LIBRARY_VERSION = "lib-v1"

BENCHES = ["flat_bench", "adjustable_bench"]
STEPS = ["plyo_box", "flat_bench", "adjustable_bench"]
LEVEL_TO_DIFFICULTY = {"beginner": 1, "intermediate": 2, "expert": 3}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().replace("'", "")).strip("_")
    return slug


def parse_equipment(spec: str) -> List[List[str]]:
    """Equipment DSL -> list of options (each a sorted list of equipment ids)."""
    if not spec.strip():
        return []
    options: List[List[str]] = []
    for alternative in spec.split("|"):
        groups = []
        for token in alternative.split("+"):
            token = token.strip()
            groups.append(BENCHES if token == "BENCH" else STEPS if token == "STEP" else [token])
        for combo in itertools.product(*groups):
            option = sorted(set(combo))
            if option not in options:
                options.append(option)
    return sorted(options)


def _map_muscles(values: Sequence[str]) -> List[str]:
    return [SOURCE_MUSCLE_MAP.get(v, v.replace(" ", "_")) for v in values]


def _modality(pick: Pick) -> str:
    if pick.modality:
        return pick.modality
    if pick.pattern == "conditioning":
        return "conditioning"
    if pick.pattern == "mobility":
        return "mobility"
    return "strength"


def build_exercise(pick: Pick, source_by_name: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if pick.source:
        src = source_by_name[pick.source]
        primary = _map_muscles(src["primaryMuscles"])
        secondary = [m for m in _map_muscles(src["secondaryMuscles"]) if m not in primary]
        difficulty = pick.difficulty or LEVEL_TO_DIFFICULTY[src["level"]]
        source = {"kind": "free-exercise-db", "ref": src["id"]}
    else:
        primary, secondary = list(pick.muscles), list(pick.secondary)
        difficulty = pick.difficulty or 1
        source = {"kind": "in_house", "ref": None}

    options = parse_equipment(pick.equipment)
    all_equipment = sorted({item for option in options for item in option})
    modality = _modality(pick)
    impact = pick.impact or derive_impact_level(pick.name)

    return {
        "exercise_id": slugify(pick.name),
        "name": pick.name,
        "movement_pattern": pick.pattern,
        "modality": modality,
        "laterality": pick.laterality,
        "measure": pick.measure,
        "difficulty": difficulty,
        "primary_muscles": primary,
        "secondary_muscles": secondary,
        "equipment_options": options,
        "contraindications": derive_contraindications(
            name=pick.name,
            pattern=pick.pattern,
            laterality=pick.laterality,
            equipment=all_equipment,
            impact_level=impact,
        ),
        "goal_tags": derive_goal_tags(
            pattern=pick.pattern,
            modality=modality,
            equipment=all_equipment,
            difficulty=difficulty,
            impact_level=impact,
        ),
        "impact_level": impact,
        "default_tempo": derive_default_tempo(
            name=pick.name, pattern=pick.pattern, modality=modality, measure=pick.measure
        ),
        "source": source,
    }


def build_library(source_exercises: List[Dict[str, Any]], source_sha256: str) -> Dict[str, Any]:
    source_by_name = {e["name"]: e for e in source_exercises}
    missing = [p.source for p in PICKS if p.source and p.source not in source_by_name]
    if missing:
        raise SystemExit(f"Curated source names not found in dataset: {missing}")

    exercises = [build_exercise(p, source_by_name) for p in PICKS]

    ids = [e["exercise_id"] for e in exercises]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SystemExit(f"Duplicate exercise ids: {duplicates}")

    catalog = {item["equipment_id"] for item in json.loads(DEFAULT_EQUIPMENT_PATH.read_text())["equipment"]}
    unknown = sorted(
        {i for e in exercises for option in e["equipment_options"] for i in option} - catalog
    )
    if unknown:
        raise SystemExit(f"Equipment ids not in the catalog: {unknown}")

    return {
        "library_version": LIBRARY_VERSION,
        "sources": [
            {
                "name": "free-exercise-db",
                "url": SOURCE_REPO,
                "commit": SOURCE_COMMIT,
                "license": "Unlicense (public domain)",
                "dataset_sha256": source_sha256,
                "used": "facts only: names, muscles, difficulty level, equipment. "
                "Instruction text and images are not used.",
            },
            {"name": "in_house", "license": "proprietary", "used": "authored for coverage gaps"},
        ],
        "exercises": exercises,
    }


def _load_source(path: Optional[str]) -> bytes:
    if path:
        return Path(path).read_bytes()
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:  # noqa: S310 (pinned https URL)
        return response.read()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="local copy of free-exercise-db dist/exercises.json")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args(argv)

    raw = _load_source(args.source)
    library = build_library(json.loads(raw), hashlib.sha256(raw).hexdigest())
    Path(args.output).write_text(json.dumps(library, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(library['exercises'])} exercises to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
