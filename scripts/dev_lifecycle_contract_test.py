import unittest

from dev_lifecycle_contract import validate


class DevLifecycleContractTest(unittest.TestCase):
    def test_contract(self) -> None:
        validate()


if __name__ == "__main__":
    unittest.main()
