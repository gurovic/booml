from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from runner.models import Problem, ProblemData


KIND_TO_FIELD = {
    "train": "train_file",
    "test": "test_file",
    "sample_submission": "sample_submission_file",
    "answer": "answer_file",
}
KIND_ORDER = ("train", "test", "sample_submission", "answer")
SAFE_SUFFIXES = {".csv", ".zip", ".rar", ".parquet", ".parq"}
DEFAULT_KEYWORDS = {
    "train": ("train",),
    "test": ("test",),
    "sample_submission": ("sample", "submission", "template"),
    "answer": ("answer",),
}
DEFAULT_EXACT_NAMES = {
    "train": ("train.csv",),
    "test": ("test.csv",),
    "sample_submission": ("sample_submission.csv", "sample.csv", "predictions_template.csv"),
    "answer": ("answer.csv",),
}
CANONICAL_NAMES = {
    "train": "train.csv",
    "test": "test.csv",
    "sample_submission": "sample_submission.csv",
    "answer": "answer.csv",
}


@dataclass(frozen=True)
class FileCandidate:
    source: Path
    kind: str


def _normalize_rel(path: Path) -> str:
    return path.as_posix()


def _media_root() -> Path:
    return Path(settings.MEDIA_ROOT)


def _problem_roots() -> list[Path]:
    roots = [Path(settings.PROBLEM_DATA_ROOT), _media_root() / "problem_data"]
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(root)
    return unique


def _iter_kind_files(problem_id: int, kind: str) -> list[FileCandidate]:
    files: list[FileCandidate] = []
    seen_names: set[str] = set()
    for root in _problem_roots():
        kind_dir = root / str(problem_id) / kind
        if not kind_dir.exists() or not kind_dir.is_dir():
            continue
        for file_path in sorted(kind_dir.iterdir(), key=lambda p: (p.name.lower(), p.name)):
            if not file_path.is_file():
                continue
            if kind != "answer" and "answer" in file_path.name.lower():
                continue
            if file_path.name in seen_names:
                continue
            seen_names.add(file_path.name)
            files.append(FileCandidate(source=file_path, kind=kind))
    return files


def _choose_candidate(kind: str, candidates: list[FileCandidate]) -> FileCandidate | None:
    if not candidates:
        return None

    exact_names = tuple(name.lower() for name in DEFAULT_EXACT_NAMES.get(kind, ()))
    keywords = tuple(word.lower() for word in DEFAULT_KEYWORDS.get(kind, ()))

    def rank(candidate: FileCandidate):
        name = candidate.source.name.lower()
        suffix = candidate.source.suffix.lower()
        exact_score = 0 if name in exact_names else 1
        keyword_score = 0 if keywords and any(word in name for word in keywords) else 1
        suffix_score = 0 if suffix == ".csv" else (1 if suffix in SAFE_SUFFIXES else 2)
        return (exact_score, keyword_score, suffix_score, name)

    return sorted(candidates, key=rank)[0]


def _copy_to_media(problem_id: int, kind: str, source: Path, *, apply: bool) -> Path:
    canonical_name = CANONICAL_NAMES[kind]
    target = _media_root() / "problem_data" / str(problem_id) / kind / canonical_name
    if apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            if (not target.exists()) or target.stat().st_size != source.stat().st_size:
                shutil.copy2(source, target)
    return target


class Command(BaseCommand):
    help = (
        "Synchronize ProblemData file fields with files available on disk "
        "(PROBLEM_DATA_ROOT and MEDIA_ROOT/problem_data). "
        "By default runs in dry mode."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default: dry-run).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite already set ProblemData file fields.",
        )
        parser.add_argument(
            "--problem-id",
            action="append",
            type=int,
            help="Limit sync to specific problem id (can be provided multiple times).",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        force = bool(options.get("force"))
        selected_ids = set(options.get("problem_id") or [])

        roots = _problem_roots()
        self.stdout.write(f"sync_problem_data_files: apply={apply} force={force}")
        self.stdout.write(f"roots={', '.join(str(root) for root in roots)}")

        problems_qs = Problem.objects.all().order_by("id")
        if selected_ids:
            problems_qs = problems_qs.filter(id__in=selected_ids)

        updated = 0
        created = 0
        unresolved: list[tuple[int, str]] = []

        with transaction.atomic():
            for problem in problems_qs:
                pdata = ProblemData.objects.filter(problem=problem).first()
                if pdata is None and apply:
                    pdata = ProblemData.objects.create(problem=problem)
                    created += 1

                update_fields: list[str] = []
                problem_changes = 0
                has_any_source = False

                for kind in KIND_ORDER:
                    field_name = KIND_TO_FIELD[kind]
                    candidates = _iter_kind_files(problem.id, kind)
                    if candidates:
                        has_any_source = True
                    choice = _choose_candidate(kind, candidates)
                    if choice is None:
                        unresolved.append((problem.id, kind))
                        continue

                    target = _copy_to_media(problem.id, kind, choice.source, apply=apply)
                    target_rel = _normalize_rel(target.relative_to(_media_root()))

                    current_name = None
                    if pdata is not None:
                        current_file = getattr(pdata, field_name, None)
                        current_name = getattr(current_file, "name", None) if current_file else None

                    should_set = (
                        force
                        or current_name is None
                        or current_name == ""
                        or Path(current_name).name != target.name
                    )
                    if not should_set:
                        continue

                    self.stdout.write(
                        f"problem={problem.id} kind={kind} source={choice.source} target={target_rel}"
                    )
                    if apply:
                        assert pdata is not None
                        setattr(pdata, field_name, target_rel)
                        update_fields.append(field_name)
                    problem_changes += 1

                if apply and pdata is not None and update_fields:
                    pdata.save(update_fields=update_fields + ["updated_at"])
                    updated += 1

                if (not has_any_source) and (not selected_ids or problem.id in selected_ids):
                    self.stdout.write(self.style.WARNING(f"problem={problem.id}: no files found in roots"))
                elif problem_changes == 0:
                    self.stdout.write(f"problem={problem.id}: no changes")

            if not apply:
                transaction.set_rollback(True)

        unresolved_summary: dict[int, list[str]] = {}
        for problem_id, kind in unresolved:
            unresolved_summary.setdefault(problem_id, []).append(kind)

        self.stdout.write(self.style.SUCCESS(f"done: created={created} updated={updated}"))
        if unresolved_summary:
            self.stdout.write("missing by problem:")
            for problem_id in sorted(unresolved_summary):
                kinds = ",".join(sorted(set(unresolved_summary[problem_id]), key=KIND_ORDER.index))
                self.stdout.write(f"  {problem_id}: {kinds}")
