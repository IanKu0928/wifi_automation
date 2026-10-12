class TestResult:

    def __init__(
        self,
        test_id,
        name,
        passed,
        message="",
        metrics=None
    ):
        self.test_id = test_id
        self.name = name
        self.passed = passed
        self.message = message
        self.metrics = metrics or {}

    @property
    def status(self):
        return "PASS" if self.passed else "FAIL"

    def __str__(self):
        return (
            f"{self.test_id} "
            f"{self.name}: "
            f"{self.status}"
        )
