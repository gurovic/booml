import unittest

from runner.services.custom_metric import MetricCodeExecutor, MetricExecutionError


class MetricCodeExecutorTests(unittest.TestCase):
    def test_executes_and_returns_dict(self):
        code = """
def compute_metric(y_true, y_pred):
    return {"metric": 0.5, "auc": 0.5}
"""
        executor = MetricCodeExecutor(code)
        result = executor.run([0, 1], [0, 1])
        self.assertIn("metric", result)
        self.assertEqual(result["auc"], 0.5)

    def test_tuple_return_converted_to_dict(self):
        code = """
def compute_metric(y_true, y_pred):
    return ("macro_f1", 0.42)
"""
        executor = MetricCodeExecutor(code)
        result = executor.run([0], [0])
        self.assertEqual(result["macro_f1"], 0.42)

    def test_numeric_return_wrapped(self):
        code = """
def compute_metric(y_true, y_pred):
    return 0.77
"""
        executor = MetricCodeExecutor(code)
        result = executor.run([1], [1])
        self.assertEqual(result["metric"], 0.77)

    def test_numpy_helpers_available(self):
        code = """
def compute_metric(y_true, y_pred):
    return {"metric": float(np.mean(y_true == y_pred))}
"""
        executor = MetricCodeExecutor(code)
        result = executor.run([1, 0], [1, 0])
        self.assertEqual(result["metric"], 1.0)

    def test_raises_on_missing_function(self):
        executor = MetricCodeExecutor("value = 1")
        with self.assertRaises(MetricExecutionError):
            executor.run([], [])

    def test_raises_on_invalid_return_type(self):
        code = """
def compute_metric(y_true, y_pred):
    return [1, 2, 3]
"""
        executor = MetricCodeExecutor(code)
        with self.assertRaises(MetricExecutionError):
            executor.run([], [])
