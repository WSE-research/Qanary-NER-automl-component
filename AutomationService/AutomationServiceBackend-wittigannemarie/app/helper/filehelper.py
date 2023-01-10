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
    def generate_csv_dataframe_response(df):
        """
        Move pandas dataframe to a suitable Response object containing a csv file
        """
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
        
    def normalize_json(self, json_object):
        """
        Normalize 2 level JSON list to 1 level
        """
        new_json = dict()
        counter = 1
        for entry in json_object:
            new_entry = self.normalize_entry(entry)
            new_json[counter] = new_entry
            counter = counter + 1

        return new_json

    def save_generated_json(self, generated, accept_header):
        """
        Save generated JSON and transform it to CSV before, if necessary
        """
        if self.file_must_transform("application/json", accept_header):
            jsonnew = self.normalize_json(generated)
            df = pd.DataFrame.from_dict(jsonnew, orient='index')
            return self.generate_csv_dataframe_response(df)
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
