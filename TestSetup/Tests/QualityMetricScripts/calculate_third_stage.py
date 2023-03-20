import sys
import json
import os
"""
param 1: Directory storing the json result files
param 2: Output file
"""

no_of_files = 0
result_text = ",Total Objects Checked,Absolute Matches,Average Matches"

objects_matched_total = 0
objects_counted_total = 0
objects_matched_current = 0
objects_counted_current = 0


def find_and_handle_exact_matches(expected, results):
    """
    Calculate the number of exactly matching pairs between expected objects and results
    """
    global objects_matched_current
    global objects_counted_current

    expected = {k.upper():v.upper() for k,v in expected.items()}
    
    for og in results:
        result = {k.upper():v.upper() for k,v in og.items()}
        if expected == result:
            objects_matched_current = objects_matched_current + 1
            # Make sure an object isn't counted double for multiple expected entity objects
            results.remove(og)

    objects_counted_current = objects_counted_current + 1
    return results

def calculate_absolute_matches(json_object):
    """
    Iterate over all objects and their expected results and trigger calculations
    """
    for result in json_object:
        # multiple objects expected
        if isinstance(result['entities'], list): 
            for expected in result['entities']:
                result['results'] = find_and_handle_exact_matches(expected, result['results'])
        # single object expected
        else: 
            result['results'] = find_and_handle_exact_matches(result['entities'], result['results'])


def generate_result_text(name, no_of_objects, no_of_matches):
    """
    Calculate the average total matches on the given input and structurally store them in a csv-string 
    """
    global result_text
    percentage = no_of_matches / no_of_objects

    result_text = """{result_text}
{name},{no_objects},{no_of_matches},{percentage}""".format(
            result_text=result_text,
            name=name,
            no_objects=no_of_objects,
            no_of_matches=no_of_matches,
            percentage=percentage)

def save_current_results(title):
    """
    Store the current results and reset the values
    """
    global objects_counted_current
    global objects_matched_current
    global objects_counted_total
    global objects_matched_total

    title = title.replace('.json', '')
    generate_result_text(name=title, no_of_objects=objects_counted_current, no_of_matches=objects_matched_current)

    objects_counted_total = objects_counted_total + objects_counted_current
    objects_matched_total = objects_matched_total + objects_matched_current
    objects_counted_current = 0
    objects_matched_current = 0

def save_total_result():
    """
    Store the total result within the result string
    """
    global objects_counted_total
    global objects_matched_total
    
    generate_result_text(name='Total', no_of_objects=objects_counted_total, no_of_matches=objects_matched_total)


def get_all_jsonfiles_in_directory (path_to_dir: str):
    return [filename for filename in os.listdir(path_to_dir) if filename.endswith('.json')]

def open_json_files (path_to_dir: str, output_path: str):
    """
    Iterate over all json files in a directory
    """
    global result_text

    files = get_all_jsonfiles_in_directory(path_to_dir)
    for json_file_name in files:
        with open(os.path.join(path_to_dir, json_file_name)) as json_file:
            json_text = json.load(json_file)
            calculate_absolute_matches(json_text)
            save_current_results(json_file_name)

    save_total_result()
    with open(output_path, "w") as csv:
        csv.write(result_text)

open_json_files(path_to_dir=sys.argv[1], output_path=sys.argv[2])