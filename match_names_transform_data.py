import csv
import json
from pprint import pprint

data = {}
with open('match_names.csv') as f:
    rows = csv.DictReader(f)
    for row in rows:
        for key in row:
            if row[key] == 'NULL':
                row[key] = None
        name_key = row['Name'].split(' ')[0]
        if name_key not in data:
            data[name_key] = {}
        case_key = '{}-{}'.format(row['fips'], row['CaseNumber'])
        if case_key not in data[name_key]:
            data[name_key][case_key] = row
            data[name_key][case_key]['Hearings'] = []
        data[name_key][case_key]['Hearings'].append({
            'Date': row['Date'].split(' ')[0],
            'Result': row['Result'],
            'Plea': row['Plea'],
            'ContinuanceCode': row['ContinuanceCode'],
            'HearingType': row['HearingType']
        })

final_data = []
for name_key in data:
    final_temp = []
    for case_key in data[name_key]:
        data[name_key][case_key]['Hearings'].sort(key=lambda x: x['Date'])
        final_temp.append(data[name_key][case_key])
    final_temp.sort(key=lambda x: x['FiledDate'])
    final_data.append(final_temp)
pprint(final_data)

with open('match_names.json', 'w') as f:
    f.write(json.dumps(final_data))
