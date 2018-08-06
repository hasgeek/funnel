import csv
with open('rootconf_2016_crew_list.csv') as csvfile:
    reader = csv.DictReader(open('rootconf_2016_crew_list.csv'))
    rows = []
    print reader
    for row in reader:
        print row['Name']
        # rows.append(row)