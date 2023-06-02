import json
import os.path
import pandas as pd
from io import StringIO
from datetime import datetime
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse


class FileHelper:
    """
    Provides functions handling files that are needed at multiple stages.
    """

    load_dotenv()
    results = os.getenv('RESULTLOCATION')

    @staticmethod
    def check_file_size(fpath):
        """
        Ensure a given file exists and is not empty
        """
        try:
            return os.path.isfile(fpath) and os.path.getsize(fpath) > 0
        except:
            return False

    @staticmethod
    def file_must_transform(content_type="", accept_type=""):
        """
        Control whether the content-type of a file is the same as the given accepted type
        """
        if content_type == accept_type:
            return False
        else:
            return True

    def save_json(self, json_object=None):
        """
        Save JSON locally
        """
        if json_object is None:
            json_object = {}
        path = self.results + 'identified-' + datetime.now().strftime("%m-%d-%Y_%H-%M-%S") + '.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(json_object, f, ensure_ascii=False, indent=4)

    def save_csv(self, csv_datastream):
        """
        Save CSV locally
        """
        now = datetime.now()
        date_time = now.strftime("%m-%d-%Y_%H-%M-%S")
        csv_datastream.to_csv(self.results + 'identified-' + date_time + '.csv', sep=',', encoding='utf-8')

    @staticmethod
    def generate_csv_dataframe_response(df, sort = False):
        """
        Sort dataframe alphabetically, having the text and language as first elements
        Move pandas dataframe to a suitable Response object containing a csv file.
        """
        if sort:
            cols = df.columns.tolist()
            cols.sort()
            if 'language' in cols:
                cols.remove('language')
                cols = ['language'] + cols 
            if 'text' in cols:
                cols.remove('text')
                cols = ['text'] + cols
            if 'Text' in cols:
                cols.remove('Text')
                cols = ['Text'] + cols
            df = df[cols]
        stream = StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=nerresult.csv"
        return response
    
    @staticmethod
    def normalize_entry(data: dict) -> dict:
        """
        Normalize 2 level JSON object to 1 level
        """
        new_data = dict()
        for key, value in data.items():
            if not isinstance(value, dict):
                new_data[key] = value
            else:
                for k, v in value.items():
                    new_data[key + "_" + k] = v
    
        return new_data
        
    def add_to_json_if_exists(self, goal_json, src_json, label, prefix, suffix):
        if label in src_json:
            generated_label = prefix + label + suffix
            goal_json[generated_label] = src_json[label]
        return goal_json

    def normalize_json(self, json_object):
        """
        Transform Json object from the standard layout of results to csv.
        """
        new_json = dict()
        for i in range(len(json_object)):
            entry = json_object[i]
            new_entry = self.add_to_json_if_exists({}, entry, 'text', '', '')
            new_entry = self.add_to_json_if_exists(new_entry, entry, 'language', '', '')
            if 'entities' in entry:
                counter = 1
                for list_or_object in entry['entities']:
                    if type(list_or_object) == str:
                        new_entry = self.add_to_json_if_exists(new_entry, entry['entities'], list_or_object, 'expected_', '') 
                    else:
                        for expected_entity in list_or_object:
                            new_entry = self.add_to_json_if_exists(new_entry, list_or_object, expected_entity, 'expected_', f'_{counter}')
                        counter = counter + 1 

            if 'results' in entry:
                counter = 1
                for resulted_entity in entry['results']:
                    for unit in resulted_entity:
                        new_entry = self.add_to_json_if_exists(new_entry, resulted_entity, unit, 'recognized_', f"_{counter}") 
                    counter += 1
            new_json[i] = new_entry
        return new_json

    def save_generated_json(self, generated, accept_header):
        """
        Save generated JSON and transform it to CSV before, if necessary
        """
        if self.file_must_transform("application/json", accept_header):
            jsonnew = self.normalize_json(generated)
            df = pd.DataFrame.from_dict(jsonnew, orient='index')
            return self.generate_csv_dataframe_response(df, True)
        else:
            self.save_json(generated)
            return generated

    def save_generated_csv_dataframe(self, generated, accept_header):
        """
        Save generated CSV and transform it to JSON before, if necessary
        """
        if self.file_must_transform("text/csv", accept_header):
            json_new = json.loads(generated.to_json(orient='records'))
            self.save_json(json_new)
            return json_new
        else:
            self.save_csv(generated)
            return self.generate_csv_dataframe_response(generated)
