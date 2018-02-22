# Raise Calculator

This script calculates raises for employees given a raise budget, employee levels, their current salary, and salary bands that map employee levels to salary.

## Assumptions

This script assumes several prerequisites:

- Some sort of performance review has already taken place, taking into account an employee's performance most recently, and employee levels have already been changed to reflect that performance review. The final level represents what the employee is worth to the company and, hence, what they should be paid.
- Salary bands are up-to-date and presumably have been adjusted to match the current market.
- **Finance** has set a raise budget, either in terms of percent of current employee payroll or a dollar amount.

## Philosophy

Employees view pay as fair if their pay is close to their market rate, the rate determined by their employee level and _up-to-date_ pay bands (let's take the leap and say that employee level accurately represents and employee's marketable skills). The farther their pay is below market rate in percentage terms, the more unhappy they will be. An employee getting paid $100,000 when they should be getting paid $110,000 is going to be more unhappy than an employee getting paid $200,000 who should be getting paid $210,000.

Thus, given a limited raise budget, the most fair raise allocation minimizes the percentage deficit between what employees are getting paid and what they should be paid. So, this script allocates each raise dollar to make the maximum reduction in this percentage deficit across all employees.

Common raise schemes such as increasing everyone's salary by a fixed percentage (or a fixed percentage by performance review rating) do not take into account how underpaid someone is already. Furthermore, it makes it much harder for lowly-paid (junior) employees to catch up to their market rate, especially since employees tend to move through the lower levels more quickly than the upper levels.

In the rare case when there is enough raise budget to bring everyone up to market rate, this script spreads the remaining budget across employees equally in dollar terms. (In this case, a similar philosophy applies because of the diminishing marginal return of happiness: someone getting paid $100,000 is going to be much happier to get $1000 extra dollars versus someone who is getting paid $200,000 who gets an extra $2000.)

## Usage

This script requires python3

    python3 calculate_raise.py -h
    usage: calculate_raise.py [-h] [--raise_budget RAISE_BUDGET]
                              [--raise_increment RAISE_INCREMENT]
                              [--minimum_raise_percent MINIMUM_RAISE_PERCENT]
                              [--debug]
                              salary_info salary_bands raise_percent
    
    positional arguments:
      salary_info           TSV containing input salary data
      salary_bands          TSV with min and max of salary ranges for levels
      raise_percent         Percent Raise for the org (0-100)
    
    optional arguments:
      -h, --help            show this help message and exit
      --raise_budget RAISE_BUDGET, -b RAISE_BUDGET
                            Override raise percent with this budget
      --raise_increment RAISE_INCREMENT, -i RAISE_INCREMENT
                            Calculate using this raise increment
      --minimum_raise_percent MINIMUM_RAISE_PERCENT, -m MINIMUM_RAISE_PERCENT
                            Minimum raise percent for all employees
      --debug


### Examples

To optimally assign a 4.2% raise to the people in `sample_salary_input.tsv` using $1 increments and salary bands in `sample_salary_band_input.tsv`:

    python3 calculate_raise.py sample_salary_input.tsv sample_salary_band_input.tsv 4.2 -i 1


To optimally assign a 4.2% raise to the people in `sample_salary_input.tsv` using $10 increments with a minimum 3% raise and salary bands in `sample_salary_band_input.tsv`:

    python3 calculate_raise.py sample_salary_input.tsv sample_salary_band_input.tsv 4.2 -i 10 -m 3


To optimally assign a $100,000 to the people in `sample_salary_input.tsv` using $10 increments, overriding/ignoring the 4.2%,  and salary bands in `sample_salary_band_input.tsv`:

    python3 calculate_raise.py sample_salary_input.tsv sample_salary_band_input.tsv 4.2 -i 10 -b 100000


## Data formats

The script takes in a tab-delimited file of salary information with columns in the following format:

    name    manager  level  current_salary
    Jane    Ellen    5.9    200000
    Jake    Ellen    6      200000
    Jerome  Steve    4.3    210000
    Jill    Judy     2      100000
    
It takes a tab-delimited file with salary band information:

    level  minimum_salary  maximum_salary
    0      75000           100000
    1      100000          125000
    2      125000          150000
    3      150000          175000
    4      175000          200000
    5      200000          225000

The script outputs tab-delimited data to standard out in the following format:

    name    manager  level  current_salary  level_salary  diff      percent_diff          post_raise_salary  raise    raise_percent          post_raise_diff  post_raise_percent_diff  post_raise_percent_change
    Jane    Ellen    5.9    200000.0        222500.0      -22500.0  -0.11250000000000004  210090.0           10090.0  0.050450000000000106   -12410.0         -0.0590699224142035      0.05343007758579654
    Jake    Ellen    6.0    200000.0        225000.0      -25000.0  -0.125                212582.0           12582.0  0.06291000000000002    -12418.0         -0.05841510570038855     0.06658489429961145
    Jerome  Steve    4.3    210000.0        182500.0      27500.0   0                     210000.0           0.0      0.0                    27500.0          0                        0
    Jill    Judy     2.0    100000.0        125000.0      -25000.0  -0.25                 113107.0           13107.0  0.13107000000000002    -11893.0         -0.10514822247959899     0.14485177752040101
    Jim     Judy     3.5    150000.0        162500.0      -12500.0  -0.08333333333333326  150341.0           341.0    0.0022733333333333494  -12159.0         -0.08087614157149403     0.002457191761839228

In these results, we see that employees who are getting underpaid the most get most of the raise budget -- Jill (`-25% -> -10.5%`), Jake (`-12.5% -> -5.8%`), and Jane (`-11.25% -> -5.9%`). Jerome is overpaid already, so he gets no raise. Jim is close to his market pay, so he gets a small raise.

### Output Explanation:

- `name`
- `manager`
- `level`
- `current_salary`
- `level_salary`
    - This salary is derived from the person's decimal level and the pay bands. 3.5 means they are in the middle of the level 3 pay band
- `diff`
    - This is the simple difference between the level_salary and current_salary
- `percent_diff`
    - This is the "percent" deficit between where someone's salary is and where it needs to be. This totals what the optimization aims to minimize
- `post_raise_salary`
- `raise`
- `raise_percent`
- `post_raise_diff`
    - Same as above but post-raise
- `post_raise_percent_diff`
    - Same as above but post-raise
- `post_raise_percent_change`
    - This is the difference between percent deficit and new percent deficit. The optimization by corrolary maximizes this

## Tests

To run tests:

    python -m unittest tests/test_calculate_raise.py