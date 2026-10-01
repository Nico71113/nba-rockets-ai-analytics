"""Download the pinned source files and create a checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from ingestion.config import (
    EXPECTED_SOURCE_LICENSE,
    MANIFEST_DIR,
    OPTIONAL_PLAY_BY_PLAY_FILE,
    RAW_DIR,
    REQUIRED_SOURCE_FILES,
    SOURCE_HANDLE,
    SOURCE_METADATA_URL,
    SOURCE_URL,
)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_source_metadata() -> dict[str, object]:
    request = Request(SOURCE_METADATA_URL, headers={"User-Agent": "nba-rockets-ai-analytics/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS endpoint
        metadata = json.load(response)

    actual_license = metadata.get("licenseName")
    if actual_license != EXPECTED_SOURCE_LICENSE:
        raise RuntimeError(
            f"Source license changed: expected {EXPECTED_SOURCE_LICENSE!r}, got {actual_license!r}"
        )
    return metadata


def download_files(output_dir: Path, *, force: bool, include_play_by_play: bool) -> list[Path]:
    try:
        import kagglehub
    except ImportError as exc:  # pragma: no cover - exercised by users without dependencies
        message = "Install project dependencies before downloading: pip install -e ."
        raise SystemExit(message) from exc

    names = list(REQUIRED_SOURCE_FILES)
    if include_play_by_play:
        names.append(OPTIONAL_PLAY_BY_PLAY_FILE)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in names:
        downloaded = kagglehub.dataset_download(
            SOURCE_HANDLE,
            path=name,
            force_download=force,
            output_dir=str(output_dir),
        )
        path = Path(downloaded)
        if not path.is_file():
            raise RuntimeError(f"Kaggle returned an unexpected path for {name}: {path}")
        paths.append(path)
    return paths


def build_manifest(metadata: dict[str, object], paths: list[Path]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dataset": SOURCE_HANDLE,
        "dataset_url": SOURCE_URL,
        "declared_license": metadata["licenseName"],
        "kaggle_version": metadata.get("currentVersionNumber"),
        "source_last_updated": metadata.get("lastUpdated"),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "files": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in sorted(paths)
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--force", action="store_true", help="Redownload existing files")
    parser.add_argument(
        "--include-play-by-play",
        action="store_true",
        help="Also download the optional ~1 GB play-by-play parquet file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = fetch_source_metadata()
    paths = download_files(
        args.output_dir,
        force=args.force,
        include_play_by_play=args.include_play_by_play,
    )
    manifest = build_manifest(metadata, paths)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    destination = MANIFEST_DIR / "source_snapshot.lock.json"
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded {len(paths)} files and wrote {destination}")


if __name__ == "__main__":
    main()
