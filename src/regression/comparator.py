from decimal import Decimal


ABS_TOL = Decimal("1")
REL_TOL = Decimal("0.001")


class RegressionComparator:

    def __init__(self):
        self.errors = []

    def compare_decimal(self, a: Decimal, b: Decimal, path: str):
        if a is None or b is None:
            if a != b:
                self.errors.append(f"{path}: {a} != {b}")
            return

        diff = abs(a - b)
        allowed = max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))

        if diff > allowed:
            self.errors.append(
                f"{path}: {a} vs {b} exceeds tolerance"
            )

    def compare_dict(self, expected: dict, actual: dict, prefix="root"):
        for key in expected:
            if key not in actual:
                self.errors.append(f"{prefix}.{key} missing in actual")
                continue

            exp_val = expected[key]
            act_val = actual[key]

            path = f"{prefix}.{key}"

            if isinstance(exp_val, Decimal):
                self.compare_decimal(exp_val, act_val, path)
            elif isinstance(exp_val, dict):
                self.compare_dict(exp_val, act_val, path)
            else:
                if exp_val != act_val:
                    self.errors.append(f"{path}: {exp_val} != {act_val}")
