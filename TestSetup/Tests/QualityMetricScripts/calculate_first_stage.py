"""
    Correct (COR) : both are the same;
    Incorrect (INC) : the output of a system and the golden annotation don’t match;
    Partial (PAR) : system and the golden annotation are somewhat “similar” but not the same; - not included as we use the exact match policy (partial matches are counted as false)
    Missing (MIS) : a golden annotation is not captured by a system;
    Spurius (SPU) : system produces a response which doesn’t exist in the golden annotation;
"""
import sys
import json
import os

"""
param 1: Directory storing the json result files
param 2: Output file
"""

no_of_files = 0

result_text = ""

cor_total = 0
inc_total = 0
mis_total = 0
spu_total = 0

cor_current_file = 0
inc_current_file = 0
mis_current_file = 0
spu_current_file = 0

cor_current_object = 0
inc_current_object = 0
mis_current_object = 0
spu_current_object = 0

def flatten_dict(item, result_lists):
    """
    Transform a dictionary from entity: text structures to flattened text: [entity] lists
    """
    for key in item:
        value = item[key]
        if value != '':
            #saving as list in case multiple same named entities occur
            if (value in result_lists):
                curr = result_lists[value]
                curr.append(key)
                result_lists[value] = curr
            else:
                result_lists[value] = [key]
    return result_lists

def get_values_as_list (dic):
    """
    Flatten the dictionaries to value: [key] lists
    """
    result_lists = {}
    if isinstance(dic, list):
        for item in dic:
            result_lists = flatten_dict(item, result_lists)
    else:
        result_lists = flatten_dict(dic, result_lists)
    return result_lists

def calculate_values_for_two_lists_with_same_key (expected, resulted):
    """
    For a given value in the original text, this method compares it's recognized entities and calculates the necessary values (an explanation can be found at the top of the script)
    """
    global cor_current_object
    global inc_current_object
    global mis_current_object
    global spu_current_object

    for golden_entity in expected:
        # COR, an expected entity is found in the result list (note that recognized entities are always written in CAPS while expected ones are not)
        if golden_entity.upper() in resulted:
            cor_current_object = cor_current_object + 1
            resulted.remove(golden_entity.upper())
            expected.remove(golden_entity)

    # There are leftover golden annotations
    if len(expected) > 0 or len(resulted) > 0:
        leftover_expected = len(expected)
        leftover_resulted = len(resulted)
        # INC is the number of recognized entities still found in both sets
        inc = min(leftover_expected, leftover_resulted)
        # MIS is the number of expected entities minus the INC ones
        mis = leftover_expected - inc
        # SPU is the number of resulted entities minus the INC ones
        spu = leftover_resulted - inc

        inc_current_object = inc_current_object + inc
        mis_current_object = mis_current_object + mis
        spu_current_object = spu_current_object + spu

def add_to_global():
    global cor_current_file
    global inc_current_file
    global mis_current_file
    global spu_current_file
    global cor_current_object
    global inc_current_object
    global mis_current_object
    global spu_current_object

    cor_current_file += cor_current_object
    inc_current_file += inc_current_object
    mis_current_file += mis_current_object
    spu_current_file += spu_current_object


def calculate_values(json_file):
    """
    Iterate over a given JSON file and compare the expected entities with the recognized one, calculating quality metrics based on the similarities / differences
    """
    global cor_current_object
    global inc_current_object
    global mis_current_object
    global spu_current_object

    for json_object in json_file:
        cor_current_object = 0
        inc_current_object = 0
        mis_current_object = 0
        spu_current_object = 0
        expected = json_object['entities']
        result = json_object['results']

        expected_flattened = get_values_as_list(expected)
        result_flattened = get_values_as_list(result)

        for value in expected_flattened: 
            expected_entity_list = expected_flattened[value]

            # Both have recognized entities for this value
            if value in result_flattened:
                result_entity_list = result_flattened[value]
                calculate_values_for_two_lists_with_same_key(expected_entity_list, result_entity_list)
                # Remove the value from the result list as all values were included
                del result_flattened[value]

            # MIS, the result objects have no entities for the value, they are missing
            else:
                for value in expected_entity_list:
                    mis_current_object = mis_current_object + 1
        
        # SPU, all leftover values in the result_list were falsely recognized as entities
        for leftover_value in result_flattened:
            for leftover_entity in result_flattened[leftover_value]:
                if (leftover_entity != ""):
                    spu_current_object = spu_current_object + 1

        json_object["quality metrics"]= {
            "correct": cor_current_object,
            "incorrect": inc_current_object,
            "missing": mis_current_object,
            "spurius": spu_current_object
        }

        add_to_global()

    return json_file

def generate_result_text(title, cor, inc, mis, spu):
    """
    Calculate quality metrics based on the given input and structurally store them in a csv-string 
    """
    global result_text
    possible = cor + inc + mis
    actual = cor + inc + spu

    precision = cor / actual
    recall = cor / possible
    f1 = (2 * precision * recall) / (precision + recall)

    result_text = """{result_text}
{title},,,,
CORRECT,INCORRECT,MISSING,SPURIUS,
{cor},{inc},{mis},{spu}

POSSIBLE,ACTUAL,Precision,Recall,F1
{pos},{act},{prec},{rec},{f1}
""".format(
            result_text=result_text,
            title=title,
            cor=cor,
            inc=inc,
            mis=mis,
            spu=spu,
            pos=possible,
            act=actual,
            prec=precision,
            rec=recall,
            f1=f1)

def save_current_file_results(title):
    """
    Store the current results and reset the values
    """
    global cor_current_file
    global inc_current_file
    global mis_current_file
    global spu_current_file
    global cor_total 
    global inc_total 
    global mis_total 
    global spu_total 

    title = title.replace('.json', '')
    generate_result_text(title=title, cor=cor_current_file, inc=inc_current_file, mis=mis_current_file, spu=spu_current_file)

    cor_total = cor_total + cor_current_file
    inc_total = inc_total + inc_current_file
    mis_total = mis_total + mis_current_file
    spu_total = spu_total + spu_current_file
    cor_current_file = 0
    inc_current_file = 0
    mis_current_file = 0
    spu_current_file = 0

def save_total_result():
    """
    Store the total result within the result string
    """
    global cor_total 
    global inc_total 
    global mis_total 
    global spu_total 
    
    generate_result_text(title='Total', cor=cor_total, inc=inc_total, mis=mis_total, spu=spu_total)


def get_all_jsonfiles_in_directory (path_to_dir: str):
    return [filename for filename in os.listdir(path_to_dir) if filename.endswith('.json')]

def save_debug_files(file_location, file):
    with open(file_location.replace(".json", "-stage1DEBUG.json"), "w") as f:
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
            json_text = calculate_values(json_text)
            save_current_file_results(json_file_name)
            if (debug is not None):
                save_debug_files(os.path.join(debug, json_file_name), json_text)

    save_total_result()
    with open(output_path, "w") as csv:
        csv.write(result_text)

debug_dir = None
if (len(sys.argv) > 3):
    debug_dir = sys.argv[3]
open_json_files(path_to_dir=sys.argv[1], output_path=sys.argv[2], debug=debug_dir)