import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference
from .logos_versification import canonical_source_map

router = APIRouter(prefix="/ot-latin", tags=["Logos Clementine Vulgate"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "lat_vulgate_clementine"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
EXPECTED_SOURCE_COMMIT = "f257a3559025c3f873b48a75019f53a9354ed7de"
EXPECTED_SOURCE_BLOB = "c0e65106383658fd91471c1b849584cc476a7944df5"
