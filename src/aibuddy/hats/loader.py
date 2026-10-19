"""Load hat packs from plain files, validate them, and fall back to the default hat (US3, FR-005/006)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..core.events import EVENT_TYPES, URGENCY_LEVELS

SUPPORTED_FORMAT = 1
STATES = ("idle", "working", "waiting", "done", "error", "disconnected")
MAX_IMAGE_BYTES = 256 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
KNOWN_KEYS = {"format", "name", "priority", "persona", "voice", "reactions"}
KNOWN_REACTION_KEYS = {"when", "say", "face", "speak", "urgency_min"}


@dataclass(frozen=True)
class Reaction:
    when: str
    say: str = ""
    face: str | None = None
    speak: bool = False
    urgency_min: str = "low"


@dataclass(frozen=True)
class Hat:
    id: str
    name: str
    priority: int = 0
    persona: str = ""
    voice: dict = field(default_factory=dict)
    reactions: tuple[Reaction, ...] = ()
    faces: dict[str, Path] = field(default_factory=dict, hash=False, compare=False)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class HatProblem:
    hat_id: str
    message: str


@dataclass
class HatLibrary:
    hats: dict[str, Hat]
    default: Hat
    problems: list[HatProblem]

    def get(self, hat_id: str) -> Hat:
        return self.hats.get(hat_id, self.default)

    def face_path(self, hat: Hat, state: str) -> Path | None:
        """The hat's own face for ``state``, else the default hat's, else None (text-only)."""
        return hat.faces.get(state) or self.default.faces.get(state)


def builtin_default() -> Hat:
    return Hat(id="default", name="Buddy")


def load_hats(root: Path) -> HatLibrary:
    hats: dict[str, Hat] = {}
    problems: list[HatProblem] = []
    if root.is_dir():
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            try:
                hat = _load_one(folder, problems)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                problems.append(HatProblem(folder.name, f"could not load: {exc}"))
                continue
            if hat is not None:
                hats[hat.id] = hat
    default = hats.get("default", builtin_default())
    return HatLibrary(hats=hats, default=default, problems=problems)


def _load_one(folder: Path, problems: list[HatProblem]) -> Hat | None:
    hat_id = folder.name
    manifest_path = folder / "hat.yaml"
    if not manifest_path.exists():
        problems.append(HatProblem(hat_id, "missing hat.yaml"))
        return None
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        problems.append(HatProblem(hat_id, "hat.yaml must contain a mapping"))
        return None
    fmt = manifest.get("format")
    if fmt != SUPPORTED_FORMAT:
        problems.append(HatProblem(hat_id, f"unsupported format {fmt!r}; this version reads format {SUPPORTED_FORMAT}"))
        return None

    warnings = [f"unknown key {key!r} ignored" for key in manifest if key not in KNOWN_KEYS]
    reactions = _reactions(manifest.get("reactions") or [], hat_id, warnings)
    persona = _persona(folder, manifest.get("persona"), hat_id, problems)
    faces = _faces(folder, hat_id, problems)
    priority = manifest.get("priority", 0)
    if not isinstance(priority, int):
        warnings.append("priority must be a whole number; using 0")
        priority = 0
    voice = manifest.get("voice") or {}
    return Hat(id=hat_id, name=str(manifest.get("name") or hat_id), priority=priority, persona=persona,
               voice=voice if isinstance(voice, dict) else {}, reactions=tuple(reactions),
               faces=faces, warnings=tuple(warnings))


def _reactions(raw: Any, hat_id: str, warnings: list[str]) -> list[Reaction]:
    if not isinstance(raw, list):
        warnings.append("reactions must be a list; ignored")
        return []
    out: list[Reaction] = []
    for entry in raw:
        if not isinstance(entry, dict):
            warnings.append("reaction is not a mapping; dropped")
            continue
        for key in entry:
            if key not in KNOWN_REACTION_KEYS:
                warnings.append(f"unknown reaction key {key!r} ignored")
        when = str(entry.get("when", ""))
        if when not in EVENT_TYPES:
            warnings.append(f"reaction trigger {when!r} is not a known event; dropped")
            continue
        urgency = str(entry.get("urgency_min", "low"))
        if urgency not in URGENCY_LEVELS:
            warnings.append(f"reaction urgency {urgency!r} is not known; using low")
            urgency = "low"
        out.append(Reaction(when=when, say=str(entry.get("say", "")), face=entry.get("face"),
                            speak=bool(entry.get("speak", False)), urgency_min=urgency))
    return out


def _persona(folder: Path, name: Any, hat_id: str, problems: list[HatProblem]) -> str:
    if not name:
        return ""
    path = folder / str(name)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        problems.append(HatProblem(hat_id, f"persona file {name!r} is missing"))
        return ""


def _faces(folder: Path, hat_id: str, problems: list[HatProblem]) -> dict[str, Path]:
    faces: dict[str, Path] = {}
    for state in STATES:
        path = folder / "faces" / f"{state}.png"
        if not path.exists():
            continue
        if path.stat().st_size > MAX_IMAGE_BYTES:
            problems.append(HatProblem(hat_id, f"face {state!r} is larger than 256 KiB; not used"))
            continue
        if path.read_bytes()[:8] != PNG_MAGIC:
            problems.append(HatProblem(hat_id, f"face {state!r} is not a PNG; not used"))
            continue
        faces[state] = path
    return faces
