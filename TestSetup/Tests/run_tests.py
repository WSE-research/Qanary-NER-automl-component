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
param 6: [OPTIONAL] CSV file for human dataset (single results)
param 7: [OPTIONAL] JSON file for human dataset (multiple results)
"""
testfile = sys.argv[1]
optionsfile = sys.argv[2]
outputname = testfile.replace(".csv", "")
folds = int(sys.argv[3])
url = sys.argv[4]
time_file = None
human_single = None
human_multiple = None

logging.getLogger().setLevel(logging.INFO)

if len(sys.argv) >= 6:
    logging.info('Outputfile for timemapping given; time will be added')
    time_file = sys.argv[5]

if len(sys.argv) >= 7:
    logging.info('Outputfile for human dataset with single results given; will be added to testing iteration')
    human_single = sys.argv[6]

if len(sys.argv) == 8:
    logging.info('Outputfile for human dataset with multiple results given; will be added to testing iteration')
    human_multiple = sys.argv[7]

f = open(testfile)
json_file = json.load(f)
no_of_objects = len(json_file)

def is_non_zero_file(fpath):
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0


def note_time(curr_fold, time_value):
    with open(time_file, "a") as text_file:
        if not is_non_zero_file:
            text_file.write('File_Name,Fold,Training Time')
        text_file.write(outputname + ',' + str(curr_fold) + ',' + str(time_value) + '\n')

async def run_tests(curr_fold):
    retrainfiles = [('trainingdata', ('tmp/train.json', open('tmp/train.json', 'rb'), 'application/json')),
                    ('testingdata', ('tmp/test.json', open('tmp/test.json', 'rb'), 'application/json')),
                    ('options', ('tmp/options.json', open('tmp/options.json', 'rb'), 'application/json'))]
    testfiles = [('file_to_identify', ('tmp/recognition.json', open('tmp/recognition.json', 'rb'), 'application/json'))]
    headers = {'accept': 'application/json'}

    start_time = time.time()
    resp = requests.post(url + 'retrain', files=retrainfiles)
    training_time = time.time() - start_time
    logging.info("retraining concluded")
    response = requests.post(url + 'api', files=testfiles, headers=headers)
    logging.info("NER concluded")
    path = 'tmp/results/base/' + outputname.rsplit('/', 1)[1].replace(".json", "") + '-' + str(curr_fold) + '.json'
    logging.info(response)

    decoded_content = response.json()

    if time_file is not None:
        note_time(curr_fold, training_time)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(decoded_content, f, ensure_ascii=False, indent=4)

    if human_single is not None:
        testfiles = [('file_to_identify', (human_single, open(human_single, 'rb'), 'application/json'))]
        response = requests.post(url + 'api', files=testfiles, headers=headers)
        path = 'tmp/results/human_single/' + outputname.rsplit('/', 1)[1].replace(".json", "") + 'human-' + str(curr_fold) + '.json'
        
        decoded_content = response.json()
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(decoded_content, f, ensure_ascii=False, indent=4)

    if human_multiple is not None:
        testfiles = [('file_to_identify', (human_multiple, open(human_multiple, 'rb'), 'application/json'))]
        response = requests.post(url + 'api', files=testfiles, headers={'accept': 'application/json'})

        decoded_content = response.json()
        path = 'tmp/results/human_multiple/' + outputname.rsplit('/', 1)[1].replace(".json", "") + 'human-' + str(curr_fold) + '.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(decoded_content, f, ensure_ascii=False, indent=4)

    return True


async def start_run():
    for j in range(folds):
        options_obj = open(optionsfile)
        options_json = json.load(options_obj)
        traindata = {}
        testdata = {}
        traindata["trainingdata"] = []
        testdata["testingdata"] = []

        start = no_of_objects / folds * j
        end = no_of_objects / folds * (j + 1)
        logging.info("Using objects " + str(start) + " to " + str(end) + " as testing data.")
        for i in range(no_of_objects):
            curr_json = json_file[i]
            if ((start - 1) <= i < (end - 1)) or (j == 0 and i == (no_of_objects - 1)):
                testdata["testingdata"].append(curr_json)
            else:
                traindata["trainingdata"].append(curr_json)


        os.remove("tmp/train.json")
        os.remove("tmp/recognition.json")
        os.remove("tmp/test.json")
        os.remove("tmp/options.json")
        with open('tmp/options.json', 'w') as f:
            json.dump(options_json, f, indent= 4, ensure_ascii=False)

        with open('tmp/train.json', 'w') as f:
            json.dump(traindata, f, indent= 4, ensure_ascii=False)

        with open('tmp/recognition.json', 'w') as f:
            json.dump(testdata['testingdata'], f, indent= 4, ensure_ascii=False)

        with open('tmp/test.json', 'w') as f:
            json.dump(testdata, f, indent= 4, ensure_ascii=False)

        await run_tests(j)
        options_obj.close()


asyncio.run(start_run())
f.close()