import csv
import subprocess

from time import sleep

from fuzzywuzzy import fuzz

def run():
    filename = 'temp_names.csv'
    #download_data("DistrictCriminalCase", '2/1/1004', 'Male', filename)
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        name_id = 0
        last_id = 0
        results = {}
        for i, row in enumerate(rows):
            if not row['Name'].startswith('R'): continue
            if 'id' not in row:
                row['id'] = name_id
                row['score'] = -1
                row['lastAddresses'] = set()
                name_id += 1
            j = i + 1
            while True:
                if j >= len(rows):
                    break
                if rows[i]['Name'][:2] != rows[j]['Name'][:2]:
                    break
                name_a = sanitize_name(rows[i]['Name'])
                name_b = sanitize_name(rows[j]['Name'])
                score = fuzz.partial_ratio(name_a, name_b)
                if score >= 90:
                    rows[j]['id'] = rows[i]['id']
                    rows[j]['score'] = score
                    rows[j]['lastAddresses'] = rows[i]['lastAddresses']
                    rows[j]['lastAddresses'].add(rows[i]['Address'])
                    break
                elif score >= 80:
                    best_address_score = fuzz.partial_ratio(rows[i]['Address'], rows[j]['Address'])
                    for address in rows[i]['lastAddresses']:
                        new_address_score = fuzz.partial_ratio(address, rows[j]['Address'])
                        if new_address_score > best_address_score:
                            best_address_score = new_address_score
                    if best_address_score >= 80:
                        rows[j]['id'] = rows[i]['id']
                        rows[j]['score'] = score
                        rows[j]['lastAddresses'] = rows[i]['lastAddresses']
                        rows[j]['lastAddresses'].add(rows[i]['Address'])
                        break
                j += 1
            if last_id != row['id']:
                #print ''
                last_id = row['id']
                #sleep(1)
            #print row['id'], row['Name'], row['score'], row['Address']
            if row['id'] not in results:
                results[row['id']] = []
            results[row['id']].append({
                'Name': row['Name'],
                'Address': row['Address'],
                'Charge': row['Charge'],
                'Filed': row['FiledDate'],
                'FineCosts': row['Fine'] is not None or row['Costs'] is not None,
                'FineCostsPaidDate': row['FineCostsPaidDate'],
                'score': row['score']
            })
        for result_id in results:
            for result in sorted(results[result_id], key=lambda x: x['Filed']):
                print result['Filed'], result['Name'], result['Charge'], result['FineCosts'], result['FineCostsPaidDate']
            print ''
            #if any(-1 < result['score'] < 90 for result in results[result_id]):
            #    for result in results[result_id]:
            #        print result_id, result['Name'], result['Address'], result['score']
            #    print ''

def sanitize_name(name):
    name = name.replace('3RD', 'III').replace('.', '')
    if ';' in name:
        name = name[:name.index(';')]
    if '  ' in name:
        name = name[:name.index('  ')]
    return name

def download_data(table, date, gender, outfile_path):
    # PGHOST, PGDATABASE, PGUSER, PGPASSWORD
    copy_cmd = '\\copy (Select "Name", "AKA1", "Gender", "Race", "Address", "Charge", "FiledDate", "Fine", "Costs", "FineCostsPaid", "FineCostsPaidDate" From "{}" '.format(table)
    copy_cmd += 'where "DOB" = \'{}\' and "Gender" = \'{}\' '.format(date, gender)
    copy_cmd += 'order by "Name") To \'{}\' With CSV HEADER;'.format(outfile_path)

    psql_cmd = [
        'psql',
        '-c', copy_cmd
    ]
    print subprocess.check_output(psql_cmd)

run()
