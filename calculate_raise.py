import csv
import sys

from argparse import ArgumentParser
from queue import PriorityQueue

idx_polarity = 0
idx_marginal_percent = 1
idx_current_salary = 2
idx_level_salary = 3
idx_employee = 4


def parse_salary_data(file):
    salaries = {}
    reader = csv.DictReader(file, delimiter='\t')
    for row in reader:
        salaries[row['name']] = {'name': row['name'], 'current_salary': float(row['current_salary']),
                                 'level': float(row['level']), 'manager': row['manager']}
    return salaries, reader.fieldnames


def parse_salary_bands(file):
    band_data = {}
    reader = csv.DictReader(file, delimiter='\t')
    for row in reader:
        band_data[int(row['level'])] = {'min': float(row['minimum_salary']), 'max': float(row['maximum_salary'])}
    return band_data


def calculate_raise_budget(raise_percent, salaries):
    total = 0.0
    for eid in salaries:
        employee = salaries[eid]
        total += employee['current_salary']
    return total, total * (raise_percent / 100.0)


def _calculate_score_for_overpaid(curr_salary, level_salary):
    """
    Spread dollars out equally among people paid above their level. Higher scores get raise dollars first
    :param curr_salary:
    :param level_salary:
    :return:
    """
    return -(curr_salary - level_salary)


def _calculate_score_for_underpaid(curr_salary, level_salary):
    """
    Maximize how much each dollar reduces percent diff from level salary. Higher scores get raise dollars first
    :param curr_salary:
    :param level_salary:
    :return:
    """
    absolute_diff = curr_salary - level_salary
    percent_diff = curr_salary / level_salary
    if absolute_diff != 0:
        marginal_percentage = percent_diff / absolute_diff
    else:
        marginal_percentage = 0
    return marginal_percentage


def _calculate_sort_params(curr_salary, level_salary):
    """
    Use to sort employees so that we prioritize employees where a marginal dollar will have a huge impact on their
    salary deficit
    """

    absolute_diff = curr_salary - level_salary
    polarity = 1 if absolute_diff >= 0 else -1
    percent_diff = curr_salary / level_salary

    if polarity == 1:
        marginal_percentage = _calculate_score_for_overpaid(curr_salary, level_salary)
    else:
        marginal_percentage = _calculate_score_for_underpaid(curr_salary=curr_salary, level_salary=level_salary)

    # it's a min heap so have to negate marginal_percentage
    return polarity, -marginal_percentage, absolute_diff, percent_diff


def _salary_for_level(salary_bands, level):
    band = int(level)
    if band not in salary_bands:
        raise Exception("Missing salary band in salary band inout data: {}".format(band))
    band_fraction = float(level) - band
    return salary_bands[band]['min'] + ((salary_bands[band]['max'] - salary_bands[band]['min']) * band_fraction)


def _create_optimization_data(salaries, salary_bands, minimum_raise_percent, raise_budget):
    remaining_budget = raise_budget
    raise_data = []
    for eid in salaries:
        employee = salaries[eid]
        target_salary = _salary_for_level(salary_bands=salary_bands, level=employee['level'])

        # apply minimum raise
        salary_raise = min(remaining_budget, (minimum_raise_percent / 100.0) * employee['current_salary'])
        curr_salary = salary_raise + employee['current_salary']
        remaining_budget -= salary_raise

        polarity, marginal_percentage, _, _ = _calculate_sort_params(curr_salary=curr_salary,
                                                                     level_salary=target_salary)

        raise_data.append(
            [polarity, marginal_percentage, curr_salary, target_salary,
             eid])
    return raise_data, remaining_budget


def _apply_budget_greedily(optimization_data, remaining_budget, raise_increment):
    marginal_percentage_increase = PriorityQueue()

    for item in optimization_data:
        marginal_percentage_increase.put(item)

    # optimally apply the budget
    while remaining_budget > 0 and marginal_percentage_increase.qsize() > 0:
        item = marginal_percentage_increase.get()

        item[idx_current_salary] += raise_increment

        polarity, marginal_percentage, diff, pdiff = _calculate_sort_params(
            curr_salary=item[idx_current_salary], level_salary=item[idx_level_salary])

        item[idx_polarity] = polarity
        item[idx_marginal_percent] = marginal_percentage

        marginal_percentage_increase.put(item)

        remaining_budget -= raise_increment

    # Calculate final stats
    items = []
    while marginal_percentage_increase.qsize() > 0:
        items.append(marginal_percentage_increase.get())

    return items


def optimally_assign_dollars(raise_budget, salaries, salary_bands, raise_increment=1.0, minimum_raise_percent=0.0,
                             debug=False):
    """
    Apply dollars such that they maximally reduce the percentage deficit between target level salary and actual salary
    :param raise_budget:
    :param salaries:
    :param salary_bands:
    :param raise_increment:
    :param minimum_raise_percent:
    :param debug:
    :return:
    """

    optimization_data, remaining_budget = _create_optimization_data(salaries=salaries, salary_bands=salary_bands,
                                                                    minimum_raise_percent=minimum_raise_percent,
                                                                    raise_budget=raise_budget)

    if debug:
        for item in sorted(list(optimization_data)):
            print(item, file=sys.stderr)

    # Calculate final stats
    items = _apply_budget_greedily(optimization_data=optimization_data, remaining_budget=remaining_budget,
                                   raise_increment=raise_increment)

    optimization_data = _calculate_raise_stats(items=items, employee_salary_data=salaries, salary_bands=salary_bands)
    return optimization_data


def _calculate_raise_stats(items, employee_salary_data, salary_bands):
    raise_stats = {}
    for item in items:
        employee_raise_stats = {}
        employee = employee_salary_data[item[idx_employee]]
        target_salary = _salary_for_level(salary_bands=salary_bands, level=employee['level'])

        employee_raise_stats['diff'] = employee['current_salary'] - target_salary
        employee_raise_stats['percent_diff'] = _calculate_percent_deficit(
            curr_salary=employee['current_salary'], level_salary=target_salary)

        employee_raise_stats['post_raise_salary'] = item[idx_current_salary]
        employee_raise_stats['raise'] = item[idx_current_salary] - employee['current_salary']
        employee_raise_stats['raise_percent'] = item[idx_current_salary] / employee['current_salary'] - 1.0
        employee_raise_stats['post_raise_diff'] = item[idx_current_salary] - target_salary
        employee_raise_stats['post_raise_percent_diff'] = _calculate_percent_deficit(
            curr_salary=item[idx_current_salary], level_salary=target_salary)
        employee_raise_stats['post_raise_percent_change'] = employee_raise_stats['post_raise_percent_diff'] - \
                                                           employee_raise_stats['percent_diff']
        raise_stats[employee['name']] = employee_raise_stats
    return raise_stats


def _calculate_percent_deficit(curr_salary, level_salary):
    post_raise_diff = curr_salary - level_salary
    if post_raise_diff < 0:
        post_raise_percent_diff = -1 * ((level_salary / curr_salary) - 1)
    else:
        post_raise_percent_diff = 0  # (curr_salary/level_salary)
    return post_raise_percent_diff


def print_salaries(salaries, salary_bands, raise_data):
    writer = csv.DictWriter(sys.stdout,
                            delimiter='\t',
                            fieldnames=['name', 'manager', 'level', 'current_salary', 'level_salary', 'diff',
                                        'percent_diff',
                                        'post_raise_salary', 'raise', 'raise_percent', 'post_raise_diff',
                                        'post_raise_percent_diff', 'post_raise_percent_change'])
    writer.writeheader()
    for eid in salaries:
        em = salaries[eid]
        target_salary = _salary_for_level(salary_bands=salary_bands, level=em['level'])
        em['level_salary'] = target_salary

        all_data = {}
        all_data.update(em)
        all_data.update(raise_data[em['name']])
        writer.writerow(all_data)


def main():
    parser = ArgumentParser()
    parser.add_argument('file', help='TSV containing input salary data')
    parser.add_argument('salary_bands', help='TSV with min and max of salary ranges for levels')
    parser.add_argument('raise_percent', type=float, help='Percent Raise for the org (0-100)')
    parser.add_argument('--raise_budget', '-b', type=float, help='Override raise percent with this budget')
    parser.add_argument('--raise_increment', '-i', type=float, help='Calculate using this raise increment', default=1.0)
    parser.add_argument('--minimum_raise_percent', '-m', type=float, help='Minimum raise percent for all employees',
                        default=0)
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()

    with open(args.file) as f:
        salaries, header = parse_salary_data(f)

    with open(args.salary_bands) as f:
        salary_bands = parse_salary_bands(f)

    total_salaries, raise_budget = calculate_raise_budget(raise_percent=args.raise_percent,
                                                          salaries=salaries)

    raise_percent = args.raise_percent
    if args.raise_budget:
        raise_budget = args.raise_budget
        raise_percent = ((total_salaries + raise_percent) / total_salaries - 1) * 100

    raise_data = optimally_assign_dollars(raise_budget=raise_budget, salaries=salaries,
                                          raise_increment=args.raise_increment,
                                          minimum_raise_percent=min(raise_percent, args.minimum_raise_percent),
                                          salary_bands=salary_bands,
                                          debug=args.debug)

    print("Total salaries: {}".format(total_salaries), file=sys.stderr)
    print("Total raise budget: {}".format(raise_budget), file=sys.stderr)

    print_salaries(salaries=salaries, salary_bands=salary_bands, raise_data=raise_data)


if __name__ == '__main__':
    main()
