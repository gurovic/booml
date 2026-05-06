from __future__ import annotations

import textwrap

from django.db import migrations


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


def _problem_files(problem_id: int) -> dict[str, str]:
    return {
        "train_file": f"problem_data/{problem_id}/train/train.csv",
        "test_file": f"problem_data/{problem_id}/test/test.csv",
        "sample_submission_file": f"problem_data/{problem_id}/sample_submission/sample_submission.csv",
        "answer_file": f"problem_data/{problem_id}/answer/answer.csv",
    }


DESCRIPTOR_VALUES = {
    4: {
        "id_column": "person",
        "target_column": "label",
        "metric": "jaccard_at_k",
        "id_type": "str",
        "target_type": "int",
        "check_order": False,
        "metric_name": "jaccard_at_k",
        "metric_code": JACCARD_AT_K_CODE,
        "score_curve_p": None,
        "score_direction": "maximize",
        "score_ideal_metric": 1.0,
        "score_reference_metric": None,
    },
    8: {
        "id_column": "id",
        "target_column": "counts",
        "metric": "Adapted accuracy",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "adapted accuracy",
        "metric_code": ADAPTED_ACCURACY_CODE,
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    9: {
        "id_column": "id",
        "target_column": "coef",
        "metric": "accuracy",
        "id_type": "int",
        "target_type": "float",
        "check_order": False,
        "metric_name": "accuracy",
        "metric_code": COEF_ACCURACY_CODE,
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    10: {
        "id_column": "id",
        "target_column": "alien_communication_prob",
        "metric": "rmse",
        "id_type": "int",
        "target_type": "float",
        "check_order": False,
        "metric_name": "rmse",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    11: {
        "id_column": "id",
        "target_column": "alien_contact_prob",
        "metric": "",
        "id_type": "int",
        "target_type": "float",
        "check_order": False,
        "metric_name": "rmse",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    12: {
        "id_column": "id",
        "target_column": "ufo_mystery_score",
        "metric": "rmse",
        "id_type": "int",
        "target_type": "float",
        "check_order": False,
        "metric_name": "rmse",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    13: {
        "id_column": "id",
        "target_column": "is_poisonous",
        "metric": "accuracy",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "accuracy",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    14: {
        "id_column": "id",
        "target_column": "is_dangerous",
        "metric": "accuracy",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "accuracy",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    15: {
        "id_column": "id",
        "target_column": "is_dangerous",
        "metric": "f1",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "f1",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    16: {
        "id_column": "id",
        "target_column": "broke_chair",
        "metric": "f1",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "f1",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    17: {
        "id_column": "id",
        "target_column": "broke_chair",
        "metric": "f1",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "f1",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    18: {
        "id_column": "id",
        "target_column": "will_explode",
        "metric": "f1",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "f1",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    19: {
        "id_column": "id",
        "target_column": "will_eat_bun",
        "metric": "f1",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "f1",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    20: {
        "id_column": "id",
        "target_column": "cat_run",
        "metric": "f1",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "f1",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
    21: {
        "id_column": "id",
        "target_column": "persona_class",
        "metric": "accuracy",
        "id_type": "int",
        "target_type": "int",
        "check_order": False,
        "metric_name": "accuracy",
        "metric_code": "",
        "score_curve_p": None,
        "score_direction": "",
        "score_ideal_metric": None,
        "score_reference_metric": None,
    },
}


TARGET_PROBLEM_IDS = tuple(sorted(DESCRIPTOR_VALUES))


def apply_problem_task_repairs(apps, schema_editor):
    Problem = apps.get_model("runner", "Problem")
    ProblemData = apps.get_model("runner", "ProblemData")
    ProblemDescriptor = apps.get_model("runner", "ProblemDescriptor")

    for problem_id in TARGET_PROBLEM_IDS:
        if not Problem.objects.filter(id=problem_id).exists():
            continue

        ProblemData.objects.update_or_create(
            problem_id=problem_id,
            defaults=_problem_files(problem_id),
        )
        ProblemDescriptor.objects.update_or_create(
            problem_id=problem_id,
            defaults=DESCRIPTOR_VALUES[problem_id],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0034_notebookfolder_parent_and_more"),
    ]

    operations = [
        migrations.RunPython(apply_problem_task_repairs, migrations.RunPython.noop),
    ]
