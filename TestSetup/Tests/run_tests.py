import sys
import pandas as pd
import requests
import asyncio
import csv
import time
import json
import os
import logging

"""
param 1: Dataset CSV file
param 2: Options JSON file
param 3: Number of folds
param 4: URL of AutomationService
param 5: [OPTIONAL] CSV file to save the training time to
"""
testfile = sys.argv[1]
optionsfile = sys.argv[2]
outputname = testfile.replace(".csv", "")
folds = int(sys.argv[3])
url = sys.argv[4]
time_file = None

logging.getLogger().setLevel(logging.INFO)

if len(sys.argv) == 6:
    logging.info('Outputfile for timemapping given; time will be added')
    time_file = sys.argv[5]

lines = pd.read_csv(testfile, dtype=object)
no_of_lines = len(lines)


def is_non_zero_file(fpath):
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0


def note_time(curr_fold, time_value):
    with open(time_file, "a") as text_file:
        if not is_non_zero_file:
            text_file.write('File_Name,Fold,Training Time')
        text_file.write(outputname + ',' + str(curr_fold) + ',' + str(time_value) + '\n')


async def run_tests(curr_fold):
    retrainfiles = [('trainingdata', ('tmp/train.csv', open('tmp/train.csv', 'rb'), 'text/csv')),
                    ('testingdata', ('tmp/test.csv', open('tmp/test.csv', 'rb'), 'text/csv')),
                    ('options', ('tmp/options.json', open('tmp/options.json', 'rb'), 'application/json'))]
    testfiles = [('file_to_identify', ('tmp/test.csv', open('tmp/test.csv', 'rb'), 'text/csv'))]
    headers = {'accept': 'text/csv'}

    start_time = time.time()
    resp = requests.post(url + 'retrain', files=retrainfiles)
    training_time = time.time() - start_time
    logging.info("retraining concluded")
    response = requests.post(url + 'api', files=testfiles, headers=headers)
    logging.info("NER concluded")
    path = 'results/' + outputname.rsplit('/', 1)[1] + '-' + str(curr_fold) + '.csv'
    logging.info(response)

    decoded_content = response.content.decode('utf-8')
    cr = csv.reader(decoded_content.splitlines(), delimiter=',')
    my_list = list(cr)

    if time_file is not None:
        note_time(curr_fold, training_time)

    with open(path, 'w') as f:
        writer = csv.writer(f)
        for row in my_list:
            writer.writerow(row)

    return True


async def start_run():
    for j in range(folds):
        testframe = pd.DataFrame(columns=lines.columns)
        trainframe = pd.DataFrame(columns=lines.columns)
        options_obj = open(optionsfile)
        options_json = json.load(options_obj)

        start = no_of_lines / folds * j
        end = no_of_lines / folds * (j + 1)
        logging.info("Using rows " + str(start) + " to " + str(end) + " as testing data.")

        testcount = 0
        traincount = 0
        for i in range(no_of_lines):
            curr_row = lines.iloc[i]
            if ((start - 1) <= i < (end - 1)) or (j == 0 and i == (no_of_lines - 1)):
                testframe.loc[testcount] = curr_row
                testcount = testcount + 1
            else:
                trainframe.loc[traincount] = curr_row
                traincount = traincount + 1

        os.remove("tmp/train.csv")
        os.remove("tmp/test.csv")
        os.remove("tmp/options.json")
        trainframe.to_csv('tmp/train.csv', index=False)
        testframe.to_csv('tmp/test.csv', index=False)
        with open('tmp/options.json', 'w') as f:
            json.dump(options_json, f)

        await run_tests(j)


asyncio.run(start_run())
