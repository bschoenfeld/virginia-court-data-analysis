import csv
import json
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
    '46.2-1003', # DEFECTIVE SPEEDOMETER
    '46.2-1080', # DEFECTIVE SPEEDOMETER
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

    # Create milesPerCharge for each court
    all_miles_per_charge = []
    for court in traffic_by_court:
        # Remove Manassas because it makes the locality name too long
        localities = [l for l in court['locality'] if 'Manassas' not in l]
        court['localityNames'] = ' / '.join(localities)
        court['excessSpeedsMean'] = np.mean(court['excessSpeeds'])
        court['milesPerCharge'] = court['all'] * 365 / court['chargeCount']
        all_miles_per_charge.append(court['milesPerCharge'])

    # Get the standard deviation of milesPerCharge
    mean = np.mean(all_miles_per_charge)
    std = np.std(all_miles_per_charge)

    # Create a metric for how many standard deviations each court is from the mean
    traffic_by_court_fips = {}
    for court in traffic_by_court:
        court['milesPerChargeStd'] = (float(court['milesPerCharge']) - mean) / std
        for fips in court['fips']:
            traffic_by_court_fips[fips] = court['milesPerChargeStd']

    # Write the standard deviation metric to a json file so we can use it in a map
    with open('data/speeding_vs_miles_driven.json', 'w') as f:
        json.dump(traffic_by_court_fips, f)

    # Generate the charts
    plt.figure(figsize=(10, 30))
    chart_miles_per_charge(traffic_by_court, 'miles_driven_vs_tickets_order_by_data.png')
    chart_charge_count(traffic_by_court, 'tickets.png')

def chart_charge_count(traffic_by_court, filename):
    traffic_by_court.sort(key=lambda x: x['excessSpeedsMean'])

    plt.clf()

    plt.title('Tickets by Locality (2015)')
    plt.xlabel('Tickets')

    rects = plt.barh(
        range(len(traffic_by_court)),
        [x['excessSpeedsMean'] for x in traffic_by_court],
        tick_label=[x['localityNames'] for x in traffic_by_court])

    xlim_max = plt.gca().get_xlim()[1]
    base_unit = int(xlim_max * 0.005)
    under_margin = int(xlim_max * 0.1)

    for rect in rects:
        width = rect.get_width()
        position = width - base_unit
        horizontal_align = 'right'
        color = 'white'
        if width < under_margin:
            # Set the value inside the bar if its over margin
            position = width + base_unit # pad the value
            horizontal_align = 'left'
            color = 'gray'
        plt.text(position, rect.get_y(),
                 '%d' % width,
                 va='bottom', ha=horizontal_align, color=color)

    plt.gca().set_ylim(-1, len(rects))
    plt.tight_layout()
    plt.savefig(filename)

def chart_miles_per_charge(traffic_by_court, filename):
    traffic_by_court.sort(key=lambda x: x['milesPerChargeStd'], reverse=True)

    plt.clf()

    title = 'Relative Frequency of Speeding Tickets in Virginia (2015)\n'
    title += '(miles driven / ticket)\n'
    title += 'More Tickets'
    title += ' ' * 100
    title += 'Fewer Tickets'
    plt.title(title)
    plt.xlabel('Standard Deviation')
    plt.ylabel('Rank')

    rects = plt.barh(
        range(len(traffic_by_court)),
        [x['milesPerChargeStd'] for x in traffic_by_court])

    base_unit = 0.025
    for rect, x in zip(rects, traffic_by_court):
        # Write the locality name
        horizontal_align = 'left' if rect.get_x() < 0 else 'right'
        position = base_unit if rect.get_x() < 0 else (base_unit * -1)
        plt.text(position, rect.get_y(),
                 x['localityNames'],
                 va='bottom', ha=horizontal_align)

        # Write the data figure
        position = rect.get_x() if rect.get_x() < 0 else rect.get_width()
        horizontal_align = 'right' if rect.get_x() < 0 else 'left'
        color = 'gray'
        if rect.get_width() > 0.2:
            color = 'white'
            horizontal_align = 'left' if rect.get_x() < 0 else 'right'
        position += base_unit if horizontal_align == 'left' else base_unit * -1
        if position > 1.6:
            position = 1.7 - base_unit
        plt.text(position, rect.get_y(),
                 '%d K' % (int(x['milesPerCharge']) / 1000),
                 va='bottom', ha=horizontal_align, color=color)

    plt.gca().set_ylim(-1, len(rects))
    plt.gca().set_xlim(-1.7, 1.7)
    plt.yticks(range(0, len(traffic_by_court)), reversed(range(1, len(traffic_by_court) + 1)))
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
                    'excessSpeeds': [],
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
                        court['limits'][speed_limit].append(speed_actual)
                        court['excessSpeeds'].append(speed_actual - speed_limit)
                        court['chargeCount'] += 1
                        break
            print count_regex, count_speed
            #break

count_regex = 0
count_speed = 0

def get_speeding_violation(charge, code_section):
    global count_regex, count_speed
    match = SPEEDING_VIOLATION_PATTERN.search(charge)
    speeding = False #'SPEED' in charge or 'RECK' in charge

    if not match and not speeding:
        # No regex match
        return None

    if all([c_s not in code_section for c_s in SPEEDING_CODE_SECTIONS]):
        # None of the speeding keywords are in the charge
        # and the violation isn't the only thing in the charge
        #print charge, code_section
        return None

    if match:
        count_regex += 1
    else:
        count_speed += 1

    violation = match.group(0) if match else speeding
    return violation

run()
