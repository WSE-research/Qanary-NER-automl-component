import json
import spacy
import logging
import pandas as pd
import os
from spacy import displacy
from io import StringIO
from fastapi import UploadFile
from datetime import datetime
from dotenv import load_dotenv
import time
import uuid


class SpacyInterface:
    load_dotenv()
    model_location = os.getenv('MODELLOCATION')
    results = os.getenv('RESULTLOCATION')

    nlp = spacy.load(model_location)

    def __init__(self):
        logging.info("Spacy parser initialized")

    def initialize_empty_result_object(self):
        result = {}
        for entity in self.nlp.get_pipe('ner').labels:
            result[entity] = ""
        return result

    def get_nlp(self, text):
        """
        Generate a NER result based on a given input string
        """
        doc = self.nlp(text)
        results = {}
        result_object = self.initialize_empty_result_object()
        results['text'] = text
        result_list = []
        for entity in doc.ents:
            label = entity.label_
            content = entity.text
            if result_object[label] == "":
                result_object[label] = content
            else:
                result_list.append(result_object)
                result_object = self.initialize_empty_result_object()
                result_object[label] = content

        result_list.append(result_object)
        results['result'] = result_list

        return results

    def get_metadata(self):
        return self.nlp.meta

    def get_config(self):
        return self.nlp.config

    def get_visualisation(self, text):
        doc2 = self.nlp(text)
        html = displacy.render([doc2], style="dep", page=True)
        html = html + displacy.render([doc2], style="ent", page=True)
        return html

    def reload_nlp(self):
        """
        Attempt to reload the NER model and replace the current one if the re-load is successful
        """
        new_nlp = spacy.load("./app/spacy_model/output/model-best")
        self.nlp = new_nlp

    def append_entity_columns(self, dataframe: pd.DataFrame):
        for entity in self.nlp.get_pipe('ner').labels:
            dataframe[entity] = ""
        return dataframe

    def bulk_recognition_csv_file_with_mlflow(self, uploadfile: UploadFile, run_uuid: str, ml_logger):
        """
        Run each line of an input CSV file through NER and annotate it with the results. Additionally,
        generate the data for the logging in MLFLow
        """
        csv_df = pd.read_csv(StringIO(str(uploadfile.file.read(), 'utf-8')), encoding='utf-8', dtype=object)
        identify_df = self.append_entity_columns(csv_df)
        identifying_data = identify_df[csv_df.columns[0]]
        no_trainingdata = len(identifying_data)
        logging_list = list()

        for i in range(no_trainingdata):
            start = time.time()
            doc = self.nlp(identifying_data.iloc[i])
            end = time.time() - start

            expected = {}
            for j in range(len(csv_df.columns)):
                if j != 0:
                    column_name = csv_df.columns[j]
                    row = csv_df.iloc[i]
                    cell_value = row[column_name]
                    if cell_value != '':
                        expected[column_name] = cell_value
            if len(csv_df.columns) <= 1:
                expected["entities"] = "none given"

            result = {}
            for entity in doc.ents:
                identify_df[entity.label_][i] = entity.text
                result[entity.label_] = entity.text

            logging_item = {
                "input": identifying_data.iloc[i],
                "model_uuid": run_uuid,
                "runtime": end,
                "true_target": expected,
                "predicted_target": result
            }

            logging_list.append(logging_item)

        ml_logger.log_test_results(logging_list)

        now = datetime.now()
        date_time = now.strftime("%m-%d-%Y_%H-%M-%S")
        identify_df.to_csv(self.results + 'identified-' + date_time + '.csv', sep=',', encoding='utf-8')

        return identify_df

    def bulk_recognition_csv_file_classic(self, uploadfile: UploadFile):
        """
        Run each line of an input CSV file through NER and annotate it with the results
        """
        csv_df = pd.read_csv(StringIO(str(uploadfile.file.read(), 'utf-8')), encoding='utf-8', dtype=object)
        identify_df = self.append_entity_columns(csv_df)
        identifying_data = identify_df[csv_df.columns[0]]
        no_trainingdata = len(identifying_data)

        for i in range(no_trainingdata):
            doc = self.nlp(identifying_data.iloc[i])
            for entity in doc.ents:
                identify_df[entity.label_][i] = entity.text

        now = datetime.now()
        date_time = now.strftime("%m-%d-%Y_%H-%M-%S")
        identify_df.to_csv(self.results + 'identified-' + date_time + '.csv', sep=',', encoding='utf-8')

        return identify_df

    def bulk_recognition_csv_file(self, uploadfile: UploadFile, use_ml_flow=False, run_uuid: str = '',
                                    ml_logger=None):
        if use_ml_flow and ml_logger != None:
            return self.bulk_recognition_csv_file_with_mlflow(uploadfile, run_uuid, ml_logger)
        else:
            if use_ml_flow and ml_logger == None:
                logging.warn("You have asked for MLFlowLogging but no MLFlow logger is available. Proceeding without logging.")
            return self.bulk_recognition_csv_file_classic(uploadfile)

    def bulk_recognition_json_file_with_ml_flow(self, jsonfile: json, run_uuid: str, ml_logger):
        """
        Run each object of an input JSON through NER and annotate it with the results
        """
        logging_list = list()
        for entry in jsonfile:
            entry['results'] = {}
            start = time.time()
            doc = self.get_nlp(entry['text'])
            end = time.time() - start
            entry['results'] = doc['result']

            expected = {}
            result = doc['result']
            if 'entities' in entry:
                expected = entry['entities']
            else:
                expected["entities"] = 'none given'

            logging_item = {
                "input": entry['text'],
                "model_uuid": run_uuid,
                "runtime": end,
                "true_target": expected,
                "predicted_target": result
            }

            logging_list.append(logging_item)

        ml_logger.log_test_results(logging_list)

        path = self.results + 'identified-' + datetime.now().strftime("%m-%d-%Y_%H-%M-%S") + '.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(jsonfile, f, ensure_ascii=False, indent=4)

        return jsonfile

    def bulk_recognition_json_file_classic(self, jsonfile: json):
        """
        Run each object of an input JSON through NER and annotate it with the results
        """
        for entry in jsonfile:
            entry['results'] = {}
            doc = self.get_nlp(entry['text'])
            entry['results'] = doc['result']

        path = self.results + 'identified-' + datetime.now().strftime("%m-%d-%Y_%H-%M-%S") + '.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(jsonfile, f, ensure_ascii=False, indent=4)

        return jsonfile

    def bulk_recognition_json_file(self, jsonfile: json, use_ml_flow: bool = False, run_uuid: str = '',
                                    ml_logger=None):
        if use_ml_flow and ml_logger != None:
            if run_uuid == '':
                run_uuid = uuid.uuid1()
            return self.bulk_recognition_json_file_with_ml_flow(jsonfile, run_uuid, ml_logger)
        else:
            if use_ml_flow and ml_logger == None:
                logging.warn("You have asked for MLFlowLogging but no MLFlow logger is available. Proceeding without logging.")
            return self.bulk_recognition_json_file_classic(jsonfile)

    def get_nlp_with_start_and_end_positions_qanary(self, text):
        """
        Generate a NER result based on a given input string, returning start and end positions of results.
        This method is for qanary use.
        """
        doc = self.nlp(text)
        results = {}
        result_object = {}
        results['text'] = text
        result_list = []
        for entity in doc.ents:
            label = entity.label_
            text = entity.text
            content = {
                'start': entity.start_char,
                'end': entity.end_char
            }
            if text != "":
                if label not in result_object:
                    result_object[label] = content
                else:
                    result_list.append(result_object)
                    result_object = {label: content}

        result_list.append(result_object)
        results['result'] = result_list

        return results
