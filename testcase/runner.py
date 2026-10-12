class TestRunner:

    def __init__(self, logger=None):
        self.logger = logger
        self.results = []

    def run_test(self, test):

        result = test.run()

        self.results.append(result)

        if result.passed:
            print(
                f"[PASS] {result.test_id} "
                f"{result.name}"
            )
        else:
            print(
                f"[FAIL] {result.test_id} "
                f"{result.name}"
            )

        print(
            f"       {result.message}"
        )

        return result

    def print_summary(self):

        print()
        print("================================")
        print(" Test Summary")
        print("================================")

        passed = 0
        failed = 0

        for result in self.results:

            print(
                f"{result.test_id:<6} "
                f"{result.status:<5} "
                f"{result.name}"
            )

            if result.passed:
                passed += 1
            else:
                failed += 1

        print("--------------------------------")
        print(f"Total : {len(self.results)}")
        print(f"Pass  : {passed}")
        print(f"Fail  : {failed}")
        print("================================")

        return failed == 0
