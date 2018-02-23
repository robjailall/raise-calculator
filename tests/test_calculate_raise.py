from unittest import TestCase

from calculate_raise import calculate_raise_budget
from calculate_raise import _apply_budget_greedily
from calculate_raise import _apply_minimum_raise
from calculate_raise import _calculate_percent_deficit
from calculate_raise import _calculate_score_for_overpaid
from calculate_raise import _calculate_score_for_underpaid
from calculate_raise import _calculate_sort_params
from calculate_raise import _create_optimization_data
from calculate_raise import _salary_for_level

sample_bands = {
    1: {'min': 100, 'max': 200},
    2: {'min': 200, 'max': 300},
}

sample_salaries = {
    'james': {'level': 1, 'current_salary': 100},
    'bob': {'level': 2, 'current_salary': 100},
}


class RaiseCalculatorTest(TestCase):

    def setUp(self):
        super(RaiseCalculatorTest, self).setUp()
        self.bands = sample_bands.copy()
        self.salaries = sample_salaries.copy()

    def test__calculate_percent_deficit(self):
        self.assertEqual(0, _calculate_percent_deficit(curr_salary=10000, level_salary=100))
        self.assertEqual(0, _calculate_percent_deficit(curr_salary=10000, level_salary=10000))
        self.assertEqual(-0.5, _calculate_percent_deficit(curr_salary=10000, level_salary=15000))
        self.assertEqual(-1.5, _calculate_percent_deficit(curr_salary=10000, level_salary=25000))

    def test__salary_for_level(self):
        bands = self.bands

        self.assertEqual(100, _salary_for_level(salary_bands=bands, level=1))
        self.assertAlmostEqual(200, _salary_for_level(salary_bands=bands, level=1.9999999999999))
        self.assertEqual(200, _salary_for_level(salary_bands=bands, level=2))
        with self.assertRaises(Exception):
            _salary_for_level(salary_bands=bands, level=0)
        with self.assertRaises(Exception):
            _salary_for_level(salary_bands=bands, level=3)

    def test_calculate_raise_budget(self):
        self.assertEqual((200.0, 6.0, 3.0), calculate_raise_budget(raise_percent=3, salaries=self.salaries))

        self.assertEqual((200.0, 0.0, 0.0),
                         calculate_raise_budget(raise_percent=3, salaries=self.salaries, force_raise_budget=0.0))

        self.assertEqual((200.0, 48.0, 24.0),
                         calculate_raise_budget(raise_percent=3, salaries=self.salaries, force_raise_budget=48.0))


class OptimizationTest(TestCase):

    def setUp(self):
        super(OptimizationTest, self).setUp()
        self.bands = sample_bands.copy()
        self.salaries = sample_salaries.copy()

    def _assert_optimization_lists_equal(self, expected, actual):
        """
        We don't care about the second parameter. That's tested in a test__calculate_sort_params
        :param expected:
        :param actual:
        :return:
        """

        self.assertListEqual([row[0] for row in expected],
                             [row[0] for row in actual])

        self.assertListEqual([row[2:] for row in expected],
                             [row[2:] for row in actual])

    def test_nominal(self):
        salaries = self.salaries
        salaries['joe'] = {'level': 2, 'current_salary': 150}
        optimization_data, remaining_budget = _create_optimization_data(salaries=salaries, salary_bands=self.bands,
                                                                        raise_budget=100)
        self.assertEqual(100, remaining_budget)
        expected_output = [
            [1, -1.0, 100.0, 100.0, 'james'],
            [-1, .005, 100.0, 200.0, 'bob'],
            [-1, .015, 150.0, 200.0, 'joe']
        ]
        self._assert_optimization_lists_equal(expected_output, optimization_data)

    def test_should_apply_min_raise_percentage(self):
        salaries = self.salaries
        optimization_data, remaining_budget = _create_optimization_data(salaries=salaries, salary_bands=self.bands,
                                                                        raise_budget=100)
        optimization_data, remaining_budget = _apply_minimum_raise(minimum_raise_percent=1,
                                                                   raise_data=optimization_data,
                                                                   raise_budget=remaining_budget)

        self.assertEqual(98, remaining_budget)
        expected_output = [
            [1, -0.9900990099009901, 101.0, 100.0, 'james'],
            [-1, 0.005101010101010101, 101.0, 200.0, 'bob']
        ]
        self._assert_optimization_lists_equal(expected_output, optimization_data)

    def test__calculate_sort_params(self):
        # sorted from high to low
        expected_output = [
            (1, 50, 50, 1.25),
            (1, 1, 1, 1.005),
            (1, 0, 0, 1.0),
            (-1, 0.015, -50, 0.75),
            (-1, 0.005, -100, 0.5)
        ]

        output = [
            _calculate_sort_params(current_salary=250, level_salary=200),
            _calculate_sort_params(current_salary=201, level_salary=200),
            _calculate_sort_params(current_salary=200, level_salary=200),
            _calculate_sort_params(current_salary=150, level_salary=200),
            _calculate_sort_params(current_salary=100, level_salary=200)
        ]

        # sort from high to low to matched expected
        output.sort()
        output.reverse()

        self.assertListEqual(expected_output, output)

    def test__apply_budget_greedily(self):
        salaries = {
            'james': {'level': 1, 'current_salary': 100},
            'bob': {'level': 2, 'current_salary': 150},
        }
        optimization_data, remaining_budget = _create_optimization_data(salaries=salaries, salary_bands=self.bands,
                                                                        raise_budget=100)

        raises = _apply_budget_greedily(optimization_data=optimization_data, remaining_budget=remaining_budget,
                                        raise_increment=1)

        expected_output = [
            [1, 25.0, 125.0, 100.0, 'james'],
            [1, 25.0, 225.0, 200.0, 'bob']
        ]

        self._assert_optimization_lists_equal(expected_output, raises)

    def test__calculate_score_for_overpaid(self):
        # higher score gets raised more
        self.assertEqual(0.0, _calculate_score_for_overpaid(current_salary=130.0, level_salary=130.0))
        self.assertEqual(-1.0, _calculate_score_for_overpaid(current_salary=131.0, level_salary=130.0))
        self.assertEqual(-20.0, _calculate_score_for_overpaid(current_salary=150.0, level_salary=130.0))
        with self.assertRaises(Exception):
            _calculate_score_for_overpaid(current_salary=0.0, level_salary=130.0)

    def test__calculate_score_for_underpaid(self):
        # higher score gets raised more
        self.assertEqual(0.0, _calculate_score_for_underpaid(current_salary=0.0, level_salary=130.0))
        self.assertEqual(-0.004807692307692308, _calculate_score_for_underpaid(current_salary=50.0, level_salary=130.0))
        self.assertEqual(-0.9923076923076923, _calculate_score_for_underpaid(current_salary=129.0, level_salary=130.0))
        self.assertEqual(-1.0, _calculate_score_for_underpaid(current_salary=130.0, level_salary=130.0))
        with self.assertRaises(Exception):
            _calculate_score_for_underpaid(current_salary=131.0, level_salary=130.0)
