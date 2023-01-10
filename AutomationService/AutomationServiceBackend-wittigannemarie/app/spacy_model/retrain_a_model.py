import json
from typing import List
from fastapi import UploadFile
from dotenv import load_dotenv
import shutil
from pathlib import Path
import os
import os.path
import logging
import csv

from app.helper.my_exceptions import NoTrainingdataException
from app.helper.filehelper import FileHelper
from app.helper.spacy_trainer import ModelHelper


class ModelReTrainer:
    """
    The class manages all actions that are needed to prepare, move, etc. files for retraining a model
    and trigger the interactions with Spacy
    """
    load_dotenv()
    file_helper = FileHelper()
    model_helper = ModelHelper()

    training_data_path = os.getenv('TRAININGLOCATION')
    training_docbins = os.getenv('TRAININGDOCBINS')
    model_location = os.getenv('MODELLOCATION')
    config = os.getenv('SPACYCONFIG')

    temporary_trainingdata_path = os.getenv('TEMPTRAININGLOCATION')
    temporary_docbin_path = os.getenv('TEMPDOCBINLOCATION')
    temporary_model_output = os.getenv('TEMPMODELOUTPUT')

    def get_trained_hardware(self):
        return self.model_helper.get_trained_hardware()

    def get_training_time(self):
        return self.model_helper.get_training_time()

    def uploadfile_not_empty(self, path_to_file, filename):
        if not self.file_helper.check_file_size(path_to_file):
            raise NoTrainingdataException(
                filename + " either couldn't be saved properly or has a size of 0 and therefore is empty. "
                            "Please make sure to send a full file.")
        else:
            return

    @staticmethod
    def save_to_disk(upload_file: UploadFile, destination: Path) -> None:
        try:
            with destination.open("wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
        finally:
            pass  # upload_file.file.close()

    def validate_train_and_test_save(self, file_ending: str):
        """
        Ensure the train and testing files exist and have content
        """
        self.uploadfile_not_empty(self.temporary_trainingdata_path + 'train' + file_ending, 'train' + file_ending)
        self.uploadfile_not_empty(self.temporary_trainingdata_path + 'test' + file_ending, 'test' + file_ending)

    def save_upload_files(self, trainingfile: UploadFile, testingfile: UploadFile, file_ending: str):
        """
        Save files temporary for later reusage
        """
        self.save_to_disk(trainingfile, Path(self.temporary_trainingdata_path + 'train' + file_ending))
        self.save_to_disk(testingfile, Path(self.temporary_trainingdata_path + 'test' + file_ending))
        self.validate_train_and_test_save('.csv')

    def temp_train_with_csv(self, language: str, modeltype: str):
        """
        Train a new model in a temporary directory using the temporary training and testing files
        """
        self.model_helper.generate_docbins(self.temporary_trainingdata_path, self.temporary_docbin_path)
        self.model_helper.train_model(self.temporary_model_output,
                                        self.temporary_docbin_path + 'train.spacy',
                                        self.temporary_docbin_path + 'test.spacy',
                                        language,
                                        modeltype)

    @staticmethod
    def remove_recursively(path_to_dir: str):
        """
        Remove leftover files in directory
        """
        for filename in os.listdir(path_to_dir):
            file_path = os.path.join(path_to_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error('Failed to delete %s. Reason: %s' % (file_path, e))

    def move_contents_of_dir(self, source_dir: str, dest_dir: str):
        """
        Move all files in directory to new location
        """
        file_names = os.listdir(source_dir)

        for file_name in file_names:
            source_file = os.path.join(source_dir, file_name)
            dest_file = os.path.join(dest_dir, file_name)
            if os.path.isdir(source_file):
                Path(dest_file).mkdir(parents=True, exist_ok=True)
                self.move_contents_of_dir(source_file, dest_file)
            else:
                if os.path.exists(dest_file):
                    # in case of the src and dst are the same file
                    if os.path.samefile(source_file, dest_file):
                        continue
                    os.remove(dest_file)

                shutil.move(source_file, dest_dir)

    def cleanup(self):
        """
        Move the new model and the training and testing files to the constant
        directories and remove all leftover temporary files
        """
        self.move_contents_of_dir(self.temporary_model_output + 'model-best/', self.model_location)  # move model
        self.move_contents_of_dir(self.temporary_docbin_path, self.training_docbins)  # move docbins
        self.move_contents_of_dir(self.temporary_trainingdata_path, self.training_data_path)  # move trainingdata

        # Deletes are not necessary, but supposed to keep it clean
        self.remove_recursively(self.temporary_model_output)  # delete leftover models
        self.remove_recursively(self.temporary_docbin_path)  # clean docbin folder
        self.remove_recursively(self.temporary_trainingdata_path)  # clean trainingdata

    def handle_csv_upload(self, trainingfile: UploadFile, testingfile: UploadFile, language: str, modeltype: str):
        """
        Initialize retraining
        """
        self.save_upload_files(trainingfile, testingfile, ".csv")
        self.temp_train_with_csv(language, modeltype)
        self.cleanup()
        return True

    @staticmethod
    def transfer_json_to_csv(json_data: json, header: List, path: str):
        """
        Rewrite a given JSON into a CSV file that is suitable for retraining the spaCy model
        """
        with open(path, 'w', encoding='UTF8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            for entry in json_data:
                row = {"Text": entry["text"]}
                for entity in entry["entities"]:
                    row[entity] = entry["entities"][entity]
                try:
                    writer.writerow(row)
                except ValueError as e:
                    raise Exception('The row generated from ' + entry[
                        "text"] + ' could not be added. Please check the values. Process continues.') from e

    def save_json_files(self, trainingfile: json, testingfile: json, entities: List[str]):
        """
        Save given JSON files in a format suitable for retraining a spaCy model
        """
        header = entities
        header.insert(0, "Text")

        self.transfer_json_to_csv(trainingfile, header, self.temporary_trainingdata_path + 'train.csv')
        self.transfer_json_to_csv(testingfile, header, self.temporary_trainingdata_path + 'test.csv')
        self.validate_train_and_test_save('.csv')

    def handle_json_upload(self, trainingfile: json, testingfile: json, entities: json, language: str, modeltype: str):
        """
        Initialize the Retraining process with training and testingfiles in json format
        """
        self.save_json_files(trainingfile, testingfile, entities)
        self.temp_train_with_csv(language, modeltype)
        self.cleanup()
        return True
