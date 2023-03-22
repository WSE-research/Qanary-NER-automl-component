import sys
import json
import os
"""
param 1: Directory storing the json result files
param 2: Output file
"""

no_of_files = 0
result_text = ",Total Expected Objects Checked,Average Similarities"

similarities_perc_total = 0
objects_counted_total = 0
similarities_perc_current = 0
objects_counted_current = 0


def handle_closest_match(no_of_similarities, total):
    """
    Add calculated closest matches to the global counters
    """
    global objects_counted_current
    global similarities_perc_current

    objects_counted_current = objects_counted_current + 1
    if no_of_similarities >= 0:
        similarities_perc_current = similarities_perc_current + (no_of_similarities / total)

def find_and_handle_closest_result_object(expected, results):
    """
    Calculate the maximal similarities of key/value pairs between expected objects and results
    """
    similarities = -1
    length = -1
    matched = {}
    for result in results:
        shared_items = {k: expected[k] for k in expected if k.upper() in result and expected[k] == result[k.upper()] and expected[k] != ""}
        if len(shared_items) > similarities:
            length = len({k: expected[k] for k in expected if expected[k] != ""})
            similarities = len(shared_items)
            matched = result

    # Make sure an object isn't counted double for multiple expected entity objects
    if matched != {}:
        results.remove(matched)

    handle_closest_match(no_of_similarities=similarities, total=length)
    return results

def calculate_maximal_similarities (json_object):
    """
    Iterate over all objects and their expected results and trigger calculations
    """
    for result in json_object:
        # multiple objects expected
        if isinstance(result['entities'], list): 
            for expected in result['entities']:
                result['results'] = find_and_handle_closest_result_object(expected, result['results'])
        # single object expected
        else: 
            result['results'] = find_and_handle_closest_result_object(result['entities'], result['results'])


def generate_result_text(name, no_of_objects, added_average_similarities):
    """
    Calculate average similarities of objects and store it in a result string 
    """
    global result_text
    percentage = added_average_similarities / no_of_objects

    result_text = """{result_text}
{name},{no_objects},{percentage}""".format(
            result_text=result_text,
            name=name,
            no_objects=no_of_objects,
            percentage=percentage)

def save_current_results(title):
    """
    Store the current results and reset the values
    """
    global objects_counted_current
    global similarities_perc_current
    global objects_counted_total
    global similarities_perc_total

    title = title.replace('.json', '')
    generate_result_text(name=title, no_of_objects=objects_counted_current, added_average_similarities=similarities_perc_current)

    objects_counted_total = objects_counted_total + objects_counted_current
    similarities_perc_total = similarities_perc_total + similarities_perc_current
    objects_counted_current = 0
    similarities_perc_current = 0

def save_total_result():
    """
    Store the total result within the result string
    """
    global objects_counted_total
    global similarities_perc_total
    
    generate_result_text(name='Total', no_of_objects=objects_counted_total, added_average_similarities=similarities_perc_total)


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
            calculate_maximal_similarities(json_text)
            save_current_results(json_file_name)

    save_total_result()
    with open(output_path, "w") as csv:
        csv.write(result_text)

open_json_files(path_to_dir=sys.argv[1], output_path=sys.argv[2])