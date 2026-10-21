import operator
import math


class RuleEngine:

    OPERATORS = {
        ">=": operator.ge,
        "<=": operator.le,
        ">": operator.gt,
        "<": operator.lt,
        "==": operator.eq,
        "!=": operator.ne,
    }

    @classmethod
    def evaluate(cls, value, operator_symbol, threshold):

        result = {
            "passed": False,
            "actual": value,
            "operator": operator_symbol,
            "threshold": threshold,
            "error": None,
        }

        if operator_symbol not in cls.OPERATORS:
            result["error"] = (
                f"Unsupported operator: {operator_symbol}"
            )
            return result

        if value is None or threshold is None:
            result["error"] = "Missing actual value or threshold"
            return result

        # Avoid treating True/False as numeric values.
        if isinstance(value, bool) or isinstance(threshold, bool):
            result["error"] = "Boolean values are not supported"
            return result

        # Reject NaN and Infinity.
        for item in (value, threshold):
            if isinstance(item, float) and not math.isfinite(item):
                result["error"] = "Non-finite numeric value"
                return result

        try:
            result["passed"] = cls.OPERATORS[
                operator_symbol
            ](value, threshold)

        except (TypeError, ValueError) as e:
            result["error"] = f"Rule evaluation failed: {e}"

        return result
