import csv
import sys
from os import environ, listdir
from os.path import isfile, join
from pprint import pprint
from census import Census
import numpy as np
import matplotlib.pyplot as plt

'''
Graph Past Due Court Costs vs Median Income By Zipcode

- Get income data from Census at tract level
- Group court cases by zipcode
- Get tracts (and income) for each zipcode
- Graph the results
'''

# Store court data csv files
path = sys.argv[1]
files = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

# Get income data for Virginia at tract level
c = Census(environ['CENSUS_API_KEY'])
response = c.acs5.state_county_tract('B07011_001E', 51, '*', '*')
income_data = {
    x['county'] + '_' + x['tract']: int(x['B07011_001E'])
    for x in response if x['B07011_001E'] is not None
}

# Read through court data. For each case, group by zipcode and
# note if the case had costs or fines and if they are paid or if they are past due.
cases = 0
cases_with_fines = 0
cases_past_due = 0
cases_paid = 0
costs_by_zipcodes = {}
for f in files:
    if not f.endswith('.csv'):
        continue
    print f
    with open(f) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cases += 1

            if row['FineCostsDue'] != '' or row['FineCostsPaid'] != '':
                zipcode = row['Address'].split(' ')[-1]
                if len(zipcode) != 5:
                    continue
                if zipcode not in costs_by_zipcodes:
                    costs_by_zipcodes[zipcode] = {
                        'count': 0,
                        'paid': 0,
                        'pastDue': 0,
                        'tracts': 0,
                        'outOfState': 0,
                        'noIncome': 0,
                        'incomes': []
                    }
                cases_with_fines += 1
                costs_by_zipcodes[zipcode]['count'] += 1
                if 'PAST DUE' in row['FineCostsDue']:
                    cases_past_due += 1
                    costs_by_zipcodes[zipcode]['pastDue'] += 1
                elif 'Paid' in row['FineCostsPaid']:
                    cases_paid += 1
                    costs_by_zipcodes[zipcode]['paid'] += 1

print 'Cases', cases
print 'With fines', int(float(cases_with_fines)/cases*100), '%'
print 'Paid', int(float(cases_paid)/cases_with_fines*100), '%'
print 'Past Due', int(float(cases_past_due)/cases_with_fines*100), '%'

# Use 2010 ZCTA to Census Tract Relationship File Layout (zcta_tract_rel_10.txt)
# from https://www.census.gov/geo/maps-data/data/zcta_rel_layout.html
# to get incomes for each zipcode 
good_zips = set()

with open('data/zcta_tract_rel_10.txt') as f:
    reader = csv.DictReader(f)
    for row in reader:
        good_zips.add(row['ZCTA5'])
        if row['ZCTA5'] in costs_by_zipcodes:
            zipcode = costs_by_zipcodes[row['ZCTA5']]
            zipcode['tracts'] += 1
            if row['STATE'] != '51':
                zipcode['outOfState'] += 1
            else:
                tract_key = row['COUNTY'] + '_' + row['TRACT']
                if tract_key in income_data:
                    zipcode['incomes'].append(income_data[tract_key])
                else:
                    zipcode['noIncome'] += 1

# Aggregate income data for each zipcode and take note of how many cases
# we won't be able to include in the final graph due to bad zipcodes or
# no income data
has_income = 0
no_income = 0
no_tracts = 0
out_of_state = 0
bad_zip = 0
bad_zips = []

costsVsIncomes = []
for key in costs_by_zipcodes:
    zipcode = costs_by_zipcodes[key]
    if len(zipcode['incomes']) > 0:
        zipcode['minIncome'] = np.min(zipcode['incomes'])
        zipcode['maxIncome'] = np.max(zipcode['incomes'])
        zipcode['meanIncome'] = np.mean(zipcode['incomes'])
        zipcode['pastDueRatio'] = float(zipcode['pastDue']) / zipcode['count'] * 100
        zipcode['paidRatio'] = float(zipcode['paid']) / zipcode['count'] * 100
        costsVsIncomes.append((zipcode['pastDueRatio'], zipcode['meanIncome']))
        has_income += zipcode['count']
    if key not in good_zips:
        bad_zip += zipcode['count']
        bad_zips.append(bad_zips)
    else:
        if zipcode['tracts'] == 0:
            no_tracts += zipcode['count']
        elif zipcode['tracts'] == zipcode['outOfState']:
            out_of_state += zipcode['count']
        elif zipcode['tracts'] == zipcode['noIncome']:
            no_income += zipcode['count']

print 'Has Income', int(float(has_income)/cases_past_due*100), '%'
print 'Out of state', int(float(out_of_state)/cases_past_due*100), '%'
print 'Bad zips', int(float(bad_zip)/cases_past_due*100), '%'

# Create graphs
costsVsIncomes.sort(key=lambda x: x[0])
plt.plot([x[0] for x in costsVsIncomes], [x[1] for x in costsVsIncomes], 'b.')
plt.xlabel('Percentage of Cases with Past Due Costs (excluding cases with no costs / fines)')
plt.ylabel('Median Income')
plt.title('Past Due Court Costs vs Median Income By Zipcode')
plt.show()
