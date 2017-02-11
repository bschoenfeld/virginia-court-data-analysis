import csv
import sys
import re
import matplotlib.pyplot as plt
import numpy as np
from os import environ, listdir
from os.path import isfile, join
from pprint import pprint

SPEEDING_CODE_SECTIONS = [
    '18.2-456',
    '22-395',
    '22-396',
    '46.2-0000',
    '46.2-830',
    '46.2-848',
    '46.2-852',
    '46.2-861',
    '46.2-862',
    '46.2-863',
    '46.2-865',
    '46.2-870',
    '46.2-871',
    '46.2-872',
    '46.2-873',
    '46.2-874',
    '46.2-875',
    '46.2-876',
    '46.2-878',
    '46.2-881',
    '46.2-882',
    '82-4-10',
    '878'
]
SPEEDING_VIOLATION_PATTERN = re.compile('[0-9]{2,3}(?:/|\\|-| )[0-9]{2}')

def run():
    # Load daily vehicle miles traveled by locality from VDOT
    traffic_by_court = load_traffic_data()

    # Load court cases with speeding violations
    court_data_path = sys.argv[1]
    load_court_cases(court_data_path, traffic_by_court)

    # Graph miles driven per ticket by locality
    data = []
    # For each locality, create a tuple with the name of the locality
    # and the miles driven per ticket
    for court in traffic_by_court:
        # Remove Manassas because it makes the locality name too long
        localities = [l for l in court['locality'] if 'Manassas' not in l]
        locality = ' / '.join(localities)
        data.append((locality, court['all'] * 365 / court['chargeCount']))

    mean = np.mean([x[1] for x in data])
    std = np.std([x[1] for x in data])
    data = [(x[0], x[1], (float(x[1]) - mean) / std) for x in data]

    plt.figure(figsize=(10, 30))

    # Plot in order of miles per violation
    data.sort(key=lambda x: x[2], reverse=True)
    create_graph(data, 'miles_driven_vs_tickets_order_by_data.png')

    data.sort(key=lambda x: x[0], reverse=True)
    create_graph(data, 'miles_driven_vs_tickets_order_by_locality.png')

def create_graph(data, filename):
    plt.clf()

    title = 'Relative Frequency of Speeding Tickets in Virginia (2015)\n'
    title += '(miles driven / ticket)\n'
    title += 'More Tickets'
    title += ' ' * 100
    title += 'Fewer Tickets'
    plt.title(title)
    plt.xlabel('Standard Deviation')

    rects = plt.barh(
        range(len(data)),
        [x[2] for x in data])

    base_unit = 0.025
    for rect, x in zip(rects, data):
        # Write the locality name
        horizontal_align = 'left' if rect.get_x() < 0 else 'right'
        position = base_unit if rect.get_x() < 0 else (base_unit * -1)
        plt.text(position, rect.get_y(),
                 x[0],
                 va='bottom', ha=horizontal_align)

        # Write the data figure
        position = rect.get_x() if rect.get_x() < 0 else rect.get_width()
        horizontal_align = 'right' if rect.get_x() < 0 else 'left'
        color = 'gray'
        if rect.get_width() > 0.2:
            color = 'white'
            horizontal_align = 'left' if rect.get_x() < 0 else 'right'
        position += base_unit if horizontal_align == 'left' else base_unit * -1
        if position > 1.25:
            position = 1.5 - base_unit
        plt.text(position, rect.get_y(),
                 '%.2f M' % (int(x[1]) / 1000000.0),
                 va='bottom', ha=horizontal_align, color=color)

    plt.gca().set_ylim(-1, len(rects))
    plt.gca().set_xlim(-1.5, 1.5)
    plt.tick_params(
        axis='y',
        left='off',
        labelleft='off')
    plt.tight_layout()

    # Save the figure
    plt.savefig(filename)

def load_traffic_data():
    traffic = {}
    with open('data/traffic_daily_vehicle_miles_traveled_2015.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['District Court FIPS Codes'] == '':
                continue
            if row['District Court FIPS Codes'] not in traffic:
                # Some district courts are represented in the traffic data
                # by mulitple localities. So instead of just loading the traffic
                # data, we have to make sure we combine rows that represent
                # the same court.
                traffic[row['District Court FIPS Codes']] = {
                    'locality': [],
                    'fips': [int(fips) for fips in row['District Court FIPS Codes'].split(',')],
                    'all': 0,
                    'interstate': 0,
                    'primary': 0,
                    'secondary': 0,
                    'limits': {},
                    'chargeCount': 0
                }
            cur = traffic[row['District Court FIPS Codes']]
            cur['locality'].append(row['Locality'].replace('City of ', ''))
            cur['all'] += int(row['All'])
            cur['interstate'] += int(row['Interstate'])
            cur['primary'] += int(row['Primary'])
            cur['secondary'] += int(row['Secondary'])
    return [traffic[fips] for fips in traffic]

def load_court_cases(path, traffic_by_court):
    files = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

    # Read through court data and find cases with speeding charge, which have the
    # general form "actual_speed / speed_limit" e.g. 82/70. For each case, find
    # the traffic data that cooresponds with the court in which the charge was
    # filed. Store the charge in a dict where the key is the speed limit and
    # the value is a list of actual speeds that were in excess of that limit.
    for f in files:
        if not f.endswith('.csv'):
            continue
        print f
        with open(f) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                violation = get_speeding_violation(row['Charge'], row['CodeSection'])
                if violation is None:
                    continue
                try:
                    violation_parts = re.split('/|\\|-| ', violation)
                    speed_actual = int(violation_parts[0])
                    speed_limit = int(violation_parts[1])
                except ValueError:
                    print violation, row['Charge'], row['CodeSection']
                    continue
                for court in traffic_by_court:
                    if int(row['court_fips']) in court['fips']:
                        if speed_limit not in court['limits']:
                            court['limits'][speed_limit] = []
                        #court['limits'][speed_limit].append(speed_actual)
                        court['chargeCount'] += 1
                        break
            #break

def get_speeding_violation(charge, code_section):
    match = SPEEDING_VIOLATION_PATTERN.search(charge)
    if not match:
        # No regex match
        return None

    if all([c_s not in code_section for c_s in SPEEDING_CODE_SECTIONS]):
        # None of the speeding keywords are in the charge
        # and the violation isn't the only thing in the charge
        return None

    violation = match.group(0)
    return violation

run()
