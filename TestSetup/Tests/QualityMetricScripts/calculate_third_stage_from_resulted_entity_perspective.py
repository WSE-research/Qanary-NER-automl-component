import sys
import json
import os
import re
"""
param 1: Directory storing the json result files
param 2: Output file
param 3: Debug file
"""

no_of_files = 0
result_text = ",Total Resulted Objects Checked,Absolute Matches,Average Matches"

objects_matched_total = 0
objects_counted_total = 0
objects_matched_current = 0
objects_counted_current = 0


def add_debug(result, value):
    if "matched" in result:
        result["matched"] += value
    else:
        result["matched"] = value
    return result

def find_and_handle_exact_matches(expected, results):
    """
    Calculate the number of exactly matching pairs between expected objects and results
    """
    global objects_matched_current

    expected_insensitive = {k.upper():v for k,v in expected.items()}
    
    for result in results:
        result_copy = result.copy()
        same = True

        entities = []
        #added this check so additional recongizes (which are from the different base models) don't cause errors
        for item in expected_insensitive:
            if item not in result_copy or expected_insensitive[item] != result_copy[item]:
                same = False
            if item in result_copy:
                del (result_copy[item])
            entities.append(item)

        for item in result_copy:
            #make sure no additional objects are left
            key_without_counter = re.sub(r'(_[1-9]*$)+', '', item) 
            if key_without_counter in entities: 
                # more entities are recresultnized than intended
                same = False

        if same:
            objects_matched_current = objects_matched_current + 1
            # Make sure an object isn't counted double for multiple expected entity objects
            result = add_debug(result, 1)
        else:
            result = add_debug(result, 0)

    return results

def calculate_absolute_matches(json_object):
    """
    Iterate over all objects and their expected results and trigger calculations
    """
    global objects_counted_current

    for result in json_object:
        # multiple objects expected
        if isinstance(result['entities'], list): 
            for expected in result['entities']:
                result['results'] = find_and_handle_exact_matches(expected, result['results'])
        # single object expected
        else: 
            result['results'] = find_and_handle_exact_matches(result['entities'], result['results'])
            
        objects_counted_current = objects_counted_current + len(result['results'])
    return json_object

def generate_result_text(name, no_of_objects, no_of_matches):
    """
    Calculate the average total matches on the given input and structurally store them in a csv-string 
    """
    global result_text
    percentage = 0
    if no_of_objects == 0:
        if no_of_matches == 0: 
            percentage = 1
    else: 
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

def save_debug_files(file_location, file):
    with open(file_location.replace(".json", "-stage3DEBUG.json"), "w") as f:
        json.dump(file, f, indent=4, ensure_ascii=False)

def open_json_files (path_to_dir: str, output_path: str, debug: str):
    """
    Iterate over all json files in a directory
    """
    global result_text

    files = get_all_jsonfiles_in_directory(path_to_dir)
    for json_file_name in files:
        with open(os.path.join(path_to_dir, json_file_name)) as json_file:
            json_text = json.load(json_file)
            json_text = calculate_absolute_matches(json_text)
            save_current_results(json_file_name)
            if (debug is not None):
                save_debug_files(os.path.join(debug, json_file_name), json_text)

    save_total_result()
    with open(output_path, "w") as csv:
        csv.write(result_text)

debug_dir = None
if (len(sys.argv) > 3):
    debug_dir = sys.argv[3]
open_json_files(path_to_dir=sys.argv[1], output_path=sys.argv[2], debug=debug_dir)