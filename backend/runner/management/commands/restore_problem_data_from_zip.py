from __future__ import annotations

import csv
import io
import os
import textwrap
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from runner.models import Problem, ProblemData, ProblemDescriptor


KIND_ORDER = ("train", "test", "sample_submission", "answer")
KIND_TO_FIELD = {
    "train": "train_file",
    "test": "test_file",
    "sample_submission": "sample_submission_file",
    "answer": "answer_file",
}
CANONICAL_FILENAMES = {
    "train": "train.csv",
    "test": "test.csv",
    "sample_submission": "sample_submission.csv",
    "answer": "answer.csv",
}
SKIPPED_EXISTING_PROBLEMS = (1, 2, 3, 5)
IGNORED_ZIP_ONLY_PROBLEMS = (22, 23, 24)


ADAPTED_ACCURACY_CODE = textwrap.dedent(
    """
    def compute_metric(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=np.float32).reshape(-1)
        y_pred = np.asarray(y_pred, dtype=np.float32).reshape(-1)
        if y_true.shape != y_pred.shape:
            raise ValueError("Target and prediction lengths do not match")
        if np.any(y_true == 0):
            raise ValueError("y_true contains zero values")

        error_rate = np.abs(y_pred - y_true) / y_true
        accuracy = 1.0 - np.minimum(1.0, error_rate)
        final_scores = np.zeros_like(accuracy)
        mask = accuracy <= 0.55
        final_scores[mask] = (accuracy[mask] - 0.55) / (1.0 - 0.55)
        return float(np.mean(final_scores))
    """
).strip()

COEF_ACCURACY_CODE = textwrap.dedent(
    """
    def compute_metric(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=np.float64).reshape(-1)
        y_pred = np.asarray(y_pred, dtype=np.float64).reshape(-1)
        if y_true.shape != y_pred.shape:
            raise ValueError("Target and prediction lengths do not match")
        if len(y_true) == 0:
            return 0.0
        return float(np.sum(y_true == y_pred) / len(y_true))
    """
).strip()

JACCARD_AT_K_CODE = textwrap.dedent(
    """
    def compute_metric(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=np.int64).reshape(-1)
        y_pred = np.asarray(y_pred, dtype=np.int64).reshape(-1)
        if y_true.shape != y_pred.shape:
            raise ValueError("Target and prediction lengths do not match")

        predicted_positive = y_pred == 1
        positive_count = int(np.sum(predicted_positive))
        if positive_count < 5 or positive_count > 15:
            return {"metric": 0.0, "jaccard_at_k": 0.0}

        true_positive = y_true == 1
        union = int(np.sum(np.logical_or(true_positive, predicted_positive)))
        score = 1.0 if union == 0 else float(np.sum(np.logical_and(true_positive, predicted_positive)) / union)
        return {"metric": score, "jaccard_at_k": score}
    """
).strip()


@dataclass(frozen=True)
class DescriptorSpec:
    id_column: str
    target_column: str
    id_type: str
    target_type: str
    metric_name: str
    metric: str = ""
    metric_code: str = ""
    check_order: bool = False
    score_direction: str = ""
    score_ideal_metric: float | None = None
    score_curve_p: float | None = None
    score_reference_metric: float | None = None

    def as_model_kwargs(self) -> dict[str, object]:
        return {
            "id_column": self.id_column,
            "target_column": self.target_column,
            "id_type": self.id_type,
            "target_type": self.target_type,
            "metric_name": self.metric_name,
            "metric": self.metric,
            "metric_code": self.metric_code,
            "check_order": self.check_order,
            "score_direction": self.score_direction,
            "score_ideal_metric": self.score_ideal_metric,
            "score_curve_p": self.score_curve_p,
            "score_reference_metric": self.score_reference_metric,
        }


@dataclass(frozen=True)
class ProblemRestoreSpec:
    problem_id: int
    expected_title: str
    files: dict[str, str]
    descriptor: DescriptorSpec | None = None
    descriptor_mode: str = "ensure"
    normalizers_by_kind: dict[str, tuple[str, ...]] = field(default_factory=dict)


def _zip_member(problem_id: int, kind: str, filename: str) -> str:
    return f"problem_data/{problem_id}/{kind}/{filename}"


def _spec(
    problem_id: int,
    title: str,
    *,
    train: str,
    test: str,
    sample_submission: str,
    answer: str,
    descriptor: DescriptorSpec | None,
    descriptor_mode: str = "ensure",
    normalizers_by_kind: dict[str, tuple[str, ...]] | None = None,
) -> ProblemRestoreSpec:
    return ProblemRestoreSpec(
        problem_id=problem_id,
        expected_title=title,
        files={
            "train": _zip_member(problem_id, "train", train),
            "test": _zip_member(problem_id, "test", test),
            "sample_submission": _zip_member(problem_id, "sample_submission", sample_submission),
            "answer": _zip_member(problem_id, "answer", answer),
        },
        descriptor=descriptor,
        descriptor_mode=descriptor_mode,
        normalizers_by_kind=normalizers_by_kind or {},
    )


RESTORE_SPECS = {
    4: _spec(
        4,
        "AH Insiders! (c дескриптором)",
        train="events_participants.csv",
        test="events_participants.csv",
        sample_submission="sample_submission_12.csv",
        answer="answer.csv",
        descriptor_mode="patch",
        descriptor=DescriptorSpec(
            id_column="person",
            target_column="label",
            id_type="str",
            target_type="int",
            metric_name="jaccard_at_k",
            metric="jaccard_at_k",
            metric_code=JACCARD_AT_K_CODE,
            score_direction="maximize",
            score_ideal_metric=1.0,
            score_curve_p=None,
            score_reference_metric=None,
        ),
    ),
    8: _spec(
        8,
        "Простые объекты (FAIO 2025 Qualification)",
        train="train_7.csv",
        test="submit_1.csv",
        sample_submission="submit_1.csv",
        answer="right_submit.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="counts",
            id_type="int",
            target_type="int",
            metric_name="adapted accuracy",
            metric="Adapted accuracy",
            metric_code=ADAPTED_ACCURACY_CODE,
        ),
    ),
    9: _spec(
        9,
        "Восстановление коэффициентов",
        train="sample_coefs.csv",
        test="sample_coefs.csv",
        sample_submission="sample_coefs.csv",
        answer="submit_coefs.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="coef",
            id_type="int",
            target_type="float",
            metric_name="accuracy",
            metric="accuracy",
            metric_code=COEF_ACCURACY_CODE,
        ),
    ),
    10: _spec(
        10,
        "[Доработка] Инопланетные контакты #1 [Линейная регрессия]",
        train="alliens_1_train.csv",
        test="allients_1_test.csv",
        sample_submission="sample_aliens_1.csv",
        answer="answer_aliens_1.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="alien_communication_prob",
            id_type="int",
            target_type="float",
            metric_name="rmse",
            metric="rmse",
        ),
        normalizers_by_kind={
            "sample_submission": ("rename_blank_first_header",),
            "answer": ("rename_blank_first_header",),
        },
    ),
    11: _spec(
        11,
        "[Доработка] Инопланетные контакты #2 [Линейная регрессия]",
        train="train_alien_2.csv",
        test="test_alien_2.csv",
        sample_submission="sample_submission_alien_2.csv",
        answer="answer_alien_2.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="alien_contact_prob",
            id_type="int",
            target_type="float",
            metric_name="rmse",
            metric="",
        ),
    ),
    12: _spec(
        12,
        "НЛО аномальность [Линейная регрессия]",
        train="train_alien_3.csv",
        test="test_alien_3.csv",
        sample_submission="sample_submission_alien_3.csv",
        answer="answer_alien_3.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="ufo_mystery_score",
            id_type="int",
            target_type="float",
            metric_name="rmse",
            metric="rmse",
        ),
    ),
    13: _spec(
        13,
        "Вонючие грибочки [Логистическая регрессия]",
        train="train_grib.csv",
        test="test_grib.csv",
        sample_submission="sample_submission_grib.csv",
        answer="answer_grib.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="is_poisonous",
            id_type="int",
            target_type="int",
            metric_name="accuracy",
            metric="accuracy",
        ),
        normalizers_by_kind={kind: ("dedupe_duplicate_columns",) for kind in KIND_ORDER},
    ),
    14: _spec(
        14,
        "Вонючие грибочки #2 [Логистическая регрессия]",
        train="train_grib_2_2.csv",
        test="test_grib_2_2.csv",
        sample_submission="sample_submission_grib_2_2.csv",
        answer="answer_grib_2_2.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="is_dangerous",
            id_type="int",
            target_type="int",
            metric_name="accuracy",
            metric="accuracy",
        ),
    ),
    15: _spec(
        15,
        "Вонючие грибочки #3 [Логистическая регрессия]",
        train="train_grib_3.csv",
        test="test_grib_3.csv",
        sample_submission="sample_submission_grib_3.csv",
        answer="answer_grib_3.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="is_dangerous",
            id_type="int",
            target_type="int",
            metric_name="f1",
            metric="f1",
        ),
    ),
    16: _spec(
        16,
        "Сломает ли стул в IKEA? [Decision stump]",
        train="train_chair.csv",
        test="test_chair.csv",
        sample_submission="sample_submission_chair.csv",
        answer="answer_chair.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="broke_chair",
            id_type="int",
            target_type="int",
            metric_name="f1",
            metric="f1",
        ),
    ),
    17: _spec(
        17,
        "Сломает ли стул в IKEA? #2 [Decision stump]",
        train="train_chair_2.csv",
        test="test_chair_2.csv",
        sample_submission="sample_submission_chair_2.csv",
        answer="answer_chair_2.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="broke_chair",
            id_type="int",
            target_type="int",
            metric_name="f1",
            metric="f1",
        ),
    ),
    18: _spec(
        18,
        "Сосиска VS Микроволновка [kNN]",
        train="train_mic.csv",
        test="test_mic.csv",
        sample_submission="sample_submission_mic.csv",
        answer="answer_mic.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="will_explode",
            id_type="int",
            target_type="int",
            metric_name="f1",
            metric="f1",
        ),
    ),
    19: _spec(
        19,
        "Голуби и булочки [SVM]",
        train="train_bun.csv",
        test="test_bun.csv",
        sample_submission="sample_submission_bun.csv",
        answer="answer_bun.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="will_eat_bun",
            id_type="int",
            target_type="int",
            metric_name="f1",
            metric="f1",
        ),
    ),
    20: _spec(
        20,
        "Убежит ли кот от пылесоса? [Decision Tree]",
        train="train_cat.csv",
        test="test_cat.csv",
        sample_submission="sample_submission_cat.csv",
        answer="answer_cat.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="cat_run",
            id_type="int",
            target_type="int",
            metric_name="f1",
            metric="f1",
        ),
    ),
    21: _spec(
        21,
        "Тип студента по активности [PCA]",
        train="train_pca.csv",
        test="test_pca.csv",
        sample_submission="sample_submission_pca.csv",
        answer="answer_pca.csv",
        descriptor=DescriptorSpec(
            id_column="id",
            target_column="persona_class",
            id_type="int",
            target_type="int",
            metric_name="accuracy",
            metric="accuracy",
        ),
    ),
}

TARGET_PROBLEM_IDS = tuple(sorted(RESTORE_SPECS))


def _zip_file_members(archive: zipfile.ZipFile) -> set[str]:
    members: set[str] = set()
    for info in archive.infolist():
        if info.is_dir():
            continue
        if info.filename.startswith("__MACOSX/"):
            continue
        members.add(info.filename)
    return members


def _normalize_csv_bytes(payload: bytes, rules: tuple[str, ...]) -> tuple[bytes, list[str]]:
    if not rules:
        return payload, []

    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    try:
        header = next(reader)
    except StopIteration:
        return payload, []

    actions: list[str] = []

    if "rename_blank_first_header" in rules and header and not (header[0] or "").strip():
        header[0] = "id"
        actions.append("renamed blank first header to id")

    keep_indices: list[int] | None = None
    if "dedupe_duplicate_columns" in rules:
        indices: list[int] = []
        seen: set[str] = set()
        dropped: list[str] = []
        for index, name in enumerate(header):
            key = (name or "").strip()
            if key in seen:
                dropped.append(key or f"column_{index + 1}")
                continue
            seen.add(key)
            indices.append(index)
        if len(indices) != len(header):
            header = [header[i] for i in indices]
            keep_indices = indices
            actions.append(f"dropped duplicate columns: {', '.join(dropped)}")

    if not actions:
        return payload, []

    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    for row in reader:
        if keep_indices is not None:
            row = [row[i] if i < len(row) else "" for i in keep_indices]
        writer.writerow(row)
    return out.getvalue().encode("utf-8"), actions


def _save_problem_file(problem_data: ProblemData, kind: str, payload: bytes) -> None:
    field_name = KIND_TO_FIELD[kind]
    canonical_name = CANONICAL_FILENAMES[kind]
    field_file = getattr(problem_data, field_name)
    storage = field_file.storage
    generated_name = field_file.field.generate_filename(problem_data, canonical_name)
    current_name = field_file.name or ""

    if isinstance(storage, FileSystemStorage):
        # Write to a temp file first so the old file survives if the write fails,
        # then atomically replace to avoid leaving the system in an inconsistent state.
        final_path = storage.path(generated_name)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        tmp_path = final_path + ".tmp"
        try:
            with open(tmp_path, "wb") as fh:
                fh.write(payload)
            os.replace(tmp_path, final_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        if current_name and current_name != generated_name:
            try:
                storage.delete(current_name)
            except Exception:
                pass
        field_file.name = generated_name
    else:
        # For other storage backends (e.g. object stores) writes are typically
        # idempotent/atomic. Delete old paths and save under the canonical name.
        for candidate in {generated_name, current_name}:
            if candidate:
                try:
                    storage.delete(candidate)
                except Exception:
                    pass
        field_file.save(canonical_name, ContentFile(payload), save=False)


def _sync_descriptor(problem: Problem, spec: ProblemRestoreSpec, *, apply: bool) -> str:
    descriptor_spec = spec.descriptor
    if descriptor_spec is None:
        return "skip"

    existing = ProblemDescriptor.objects.filter(problem=problem).first()
    desired = descriptor_spec.as_model_kwargs()

    if spec.descriptor_mode == "ensure" and existing is not None:
        return "keep existing"

    if existing is None:
        if apply:
            ProblemDescriptor.objects.create(problem=problem, **desired)
        return "create"

    changed_fields = [
        field_name
        for field_name, value in desired.items()
        if getattr(existing, field_name) != value
    ]
    if not changed_fields:
        return "unchanged"

    if apply:
        for field_name in changed_fields:
            setattr(existing, field_name, desired[field_name])
        existing.save(update_fields=changed_fields + ["updated_at"])
    return f"update ({', '.join(changed_fields)})"


class Command(BaseCommand):
    help = (
        "Restore BOOML ProblemData and missing ProblemDescriptor rows from an explicit "
        "manifest inside problem_data.zip. Dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--zip", required=True, help="Path to problem_data.zip")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write files and database changes. Without this flag the command is a dry-run.",
        )
        parser.add_argument(
            "--problem-id",
            action="append",
            type=int,
            help="Restore only the specified problem id. May be provided multiple times.",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        zip_path = Path(options["zip"]).expanduser()
        selected_ids = tuple(sorted(set(options.get("problem_id") or TARGET_PROBLEM_IDS)))

        if not zip_path.exists():
            raise CommandError(f"Zip archive not found: {zip_path}")

        unsupported = sorted(set(selected_ids) - set(TARGET_PROBLEM_IDS))
        if unsupported:
            raise CommandError(f"Unsupported problem ids: {', '.join(map(str, unsupported))}")

        problems = {
            problem.id: problem
            for problem in Problem.objects.filter(id__in=selected_ids).order_by("id")
        }
        missing_problem_ids = [problem_id for problem_id in selected_ids if problem_id not in problems]
        if missing_problem_ids:
            raise CommandError(
                "Problem rows are missing in the database: "
                + ", ".join(str(problem_id) for problem_id in missing_problem_ids)
            )

        with zipfile.ZipFile(zip_path) as archive:
            members = _zip_file_members(archive)
            missing_members: list[str] = []
            for problem_id in selected_ids:
                spec = RESTORE_SPECS[problem_id]
                for kind in KIND_ORDER:
                    member = spec.files[kind]
                    if member not in members:
                        missing_members.append(f"{problem_id}:{kind}:{member}")
            if missing_members:
                raise CommandError("Missing zip members:\n" + "\n".join(missing_members))

            self.stdout.write(
                f"restore_problem_data_from_zip: apply={apply} zip={zip_path}"
            )
            self.stdout.write(
                "selected problems: " + ", ".join(str(problem_id) for problem_id in selected_ids)
            )
            self.stdout.write(
                "skipped existing problems: " + ", ".join(str(problem_id) for problem_id in SKIPPED_EXISTING_PROBLEMS)
            )
            self.stdout.write(
                "ignored zip-only problems: " + ", ".join(str(problem_id) for problem_id in IGNORED_ZIP_ONLY_PROBLEMS)
            )

            with transaction.atomic():
                for problem_id in selected_ids:
                    spec = RESTORE_SPECS[problem_id]
                    problem = problems[problem_id]
                    problem_data = ProblemData.objects.filter(problem=problem).first()
                    problem_data_action = "create" if problem_data is None else "update"
                    title_suffix = ""
                    if problem.title != spec.expected_title:
                        title_suffix = f" [title mismatch: expected '{spec.expected_title}']"

                    self.stdout.write(
                        f"\nproblem {problem_id}: {problem.title}{title_suffix}"
                    )

                    if apply and problem_data is None:
                        problem_data = ProblemData.objects.create(problem=problem)

                    for kind in KIND_ORDER:
                        member = spec.files[kind]
                        raw_bytes = archive.read(member)
                        payload, actions = _normalize_csv_bytes(
                            raw_bytes, spec.normalizers_by_kind.get(kind, ())
                        )
                        action_label = "; ".join(actions) if actions else "as-is"
                        self.stdout.write(
                            f"  {kind}: {member} -> {CANONICAL_FILENAMES[kind]} [{action_label}]"
                        )
                        if apply:
                            assert problem_data is not None
                            _save_problem_file(problem_data, kind, payload)

                    if apply:
                        assert problem_data is not None
                        problem_data.save(update_fields=list(KIND_TO_FIELD.values()) + ["updated_at"])

                    descriptor_action = _sync_descriptor(problem, spec, apply=apply)
                    self.stdout.write(f"  problem_data: {problem_data_action}")
                    self.stdout.write(f"  descriptor: {descriptor_action}")

                if not apply:
                    transaction.set_rollback(True)

        mode = "applied" if apply else "dry-run completed"
        self.stdout.write(self.style.SUCCESS(mode))
