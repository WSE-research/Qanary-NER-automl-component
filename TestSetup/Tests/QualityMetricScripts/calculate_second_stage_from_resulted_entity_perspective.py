import sys
import json
import os
"""
param 1: Directory storing the json result files
param 2: Output file
"""

no_of_files = 0
result_text = ",Total Result Objects Checked,Average Similarities"

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

def get_item_length(item):
    count = 0
    for key in item:
        if item[key] != '':
            count += 1
    return count

def get_shared_items(main_item, comparing_item):
    matches = {}
    for key in comparing_item:
        if (key.upper() in main_item and main_item[key.upper()] != "" and main_item[key.upper()] == comparing_item[key]):
            matches[key.upper()] = main_item[key.upper()]
    return matches

def find_and_handle_closest_golden_object(result_object, golden_objects):
    """
    Calculate the maximal similarities of key/value pairs between result objects and golden objects
    """
    similarities = -1
    length = -1
    matched = {}

    if not isinstance(golden_objects, list):
        golden_objects = [golden_objects]
        
    for golden in golden_objects:
        shared_items = {k: golden[k] for k in golden if k.upper() in result_object and golden[k] == result_object[k.upper()] and result_object[k.upper()] != ""}
        if len(shared_items) > similarities:
            similarities = len(shared_items)
            matched = golden
            length = len({k: golden[k] for k in golden if golden[k] != ""})

    # Make sure an object isn't counted double for multiple result_object entity objects
    #if matched != {}:
    #    results.remove(matched)

    result_object["similarities"] = similarities / length
    handle_closest_match(no_of_similarities=similarities, total=length)
    return result_object

def calculate_maximal_similarities (json_object):
    """
    Iterate over all objects and their results and trigger calculations
    """
    for result in json_object:
        for entity_object in result['results']:
            entity_object = find_and_handle_closest_golden_object(entity_object, result['entities'])
    return json_object

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

def save_debug_files(file_location, file):
    with open(file_location.replace(".json", "-stage2DEBUG.json"), "w") as f:
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
            json_text = calculate_maximal_similarities(json_text)
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