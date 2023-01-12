import logging
from typing import Optional
from starlette.requests import Request
from fastapi import UploadFile, File
from fastapi.encoders import jsonable_encoder
import json
from .MLFlowLogging import MLFlowLoggerFactory
import uuid
import os
from copy import deepcopy

ml_logger = None
last_request_json = None


def log_training_results(data, interface, trainer, options, trainingdata: Optional[UploadFile] = File(None),
                            testingdata: Optional[UploadFile] = File(None), run_uuid: Optional[str] = 'no ID given'):
    global ml_logger

    if (trainingdata is not None and trainingdata.content_type == 'text/csv') and (
            testingdata is not None and testingdata.content_type == 'text/csv'):
        traindata = trainingdata.file.read().decode("utf-8")
        testdata = testingdata.file.read().decode("utf-8")
        testingdata.file.close()
    else:
        traindata = json.dumps(data['trainingdata'])
        testdata = json.dumps(data['testingdata'])

    SERVICE_NAME_COMPONENT = os.environ['SERVICE_NAME_COMPONENT']

    if options is not None and options.content_type == 'application/json':
        option_data = json.load(options.file)
    else:
        options = {
            'entities': data['entities'],
            'language': data['language'],
            'modeltype': data['modeltype']
        }
        option_data = options

    option_data['entities'] = json.dumps(option_data['entities'])

    ml_logger.log_train_results(run_uuid, traindata, testdata, option_data, interface.get_config(),
                                interface.get_metadata(), SERVICE_NAME_COMPONENT, "NER", trainer.get_trained_hardware(),
                                "model-best", trainer.get_training_time())


def valid_accept_header(accept):
    if accept == "application/json" or accept == "text/csv":
        return True
    else:
        return False


def get_accept_header(req: Request, file: UploadFile):
    if req.headers["Accept"] is not None and valid_accept_header(req.headers["Accept"]):
        return req.headers["Accept"]
    elif file is not None and valid_accept_header(file.content_type):
        logging.warning("No valid Accept-Header was set, using the content-type of the uploadfile.")
        return file.content_type
    elif valid_accept_header(req.headers["content-type"]):
        logging.warning("No valid Accept-Header was set, using the content-type of the request.")
        return req.headers["content-type"]
    else:
        raise ValueError("Please place an Accept Header with either application/json or text/csv as value.")


def read_optional_json_value(value: str, json_object: json):
    if json_object is not None and value in json_object:
        return json_object[value]
    else:
        return ""


async def handle_retrain_logging(trainer, interface, trainingdata: Optional[UploadFile] = File(None),
                                    testingdata: Optional[UploadFile] = File(None),
                                    options: Optional[UploadFile] = File(None)):
    global ml_logger
    global last_request_json

    if ml_logger is None:
        ml_logger = MLFlowLoggerFactory.get_ml_logger()

    if ml_logger != None:
        testingdata_copy = deepcopy(testingdata)
        this_uuid = str(uuid.uuid1())
        log_training_results(last_request_json, interface, trainer, options, trainingdata, testingdata_copy, this_uuid)
        if testingdata is not None and testingdata.content_type == 'text/csv':
            interface.bulk_recognition_csv_file(testingdata, True, this_uuid, ml_logger)
        elif testingdata is not None and testingdata.content_type == 'application/json':
            json_to_identify = json.load(testingdata.file)
            interface.bulk_recognition_json_file(json_to_identify, True, this_uuid, ml_logger)
        else:
            json_to_identify = last_request_json['testingdata']
            interface.bulk_recognition_json_file(json_to_identify, True, this_uuid, ml_logger)
    else:
        logging.warn("You've asked for MLFlow logging but no logger is available! Proceeding without MLFlow logging.")


async def handle_post_retrain_call(req: Request, trainer, interface, trainingdata: Optional[UploadFile] = File(None),
                                    testingdata: Optional[UploadFile] = File(None),
                                    options: Optional[UploadFile] = File(None)):
    global last_request_json

    if (trainingdata is not None and trainingdata.content_type == 'text/csv') and (
            testingdata is not None and testingdata.content_type == 'text/csv'):
        options_json = None
        if options is not None and options.content_type == 'application/json':
            options_json = json.load(options.file)
        language = read_optional_json_value('language', options_json)
        modeltype = read_optional_json_value('modeltype', options_json)

        success = trainer.handle_csv_upload(trainingdata, testingdata, language, modeltype)
        successmessage = "Successfully updated the spacy model based on your uploaded csv data."

    elif (trainingdata is not None and trainingdata.content_type == 'application/json') and (
            testingdata is not None and testingdata.content_type == 'application/json') and (
            options is not None and testingdata.content_type == 'application/json'):
        training_json = json.load(trainingdata.file)
        testing_json = json.load(testingdata.file)
        options_json = json.load(options.file)

        success = trainer.handle_json_upload(training_json["trainingdata"], testing_json["testingdata"],
                                                options_json["entities"],
                                                read_optional_json_value("language", options_json),
                                                read_optional_json_value("modeltype", options_json))
        successmessage = "Successfully updated the spacy model based on your uploaded json files."

    elif req.headers["content-type"] == "application/json":
        data = await req.json()
        last_request_json = data
        success = trainer.handle_json_upload(data['trainingdata'], data['testingdata'], data['entities'],
                                                data['language'], data['modeltype'])
        successmessage = "Successfully updated the spacy model based on your request json body."

    else:
        return {"Error": "No supported content is given for retraining the model. The original model remains."}

    if success:
        try:
            interface.reload_nlp()
            return {"message": successmessage}
        except:
            logging.error('Could not reload the model. Maybe the files were not moved properly?')
            return {"Error": "Could not reload the model, it will not be uploaded."}
    else:
        return {"Error": "The model could not be updated."}


async def handle_post_api_call(req: Request, interface, helper, file_to_identify: Optional[UploadFile] = File(None),
                                use_ml_logger: Optional[bool] = False):
    global ml_logger
    accept = get_accept_header(req, file_to_identify)
    run_uuid = uuid.uuid1()

    if use_ml_logger and ml_logger is None:
        ml_logger = MLFlowLoggerFactory.get_ml_logger()

    if file_to_identify is not None and file_to_identify.content_type == 'text/csv':
        df = interface.bulk_recognition_csv_file(file_to_identify, use_ml_logger, run_uuid, ml_logger)
        response = helper.save_generated_csv_dataframe(df, accept)
        file_to_identify.file.close()
    elif file_to_identify is not None and file_to_identify.content_type == 'application/json':
        json_to_identify = json.load(file_to_identify.file)
        jsonfile = interface.bulk_recognition_json_file(json_to_identify, use_ml_logger, run_uuid, ml_logger)
        response = helper.save_generated_json(jsonfile, accept)
    elif req.headers["content-type"] == "application/json":
        json_to_identify = await req.json()
        result = interface.bulk_recognition_json_file(jsonable_encoder(json_to_identify), use_ml_logger, run_uuid,
                                                        ml_logger)
        response = helper.save_generated_json(result, accept)
    else:
        return {
            "Error": "No supported content is given to identify. Request[content-type]: " + req.headers["content-type"]}

    if not response:
        return {"Error": "Error while testing the given data."}
    else:

        return response


def handle_get_api_call(text: str, interface):
    result = interface.get_nlp(text)
    return result


def handle_nlp_call_with_start_and_end(text: str, interface):
    result = interface.get_nlp_with_start_and_end_positions_qanary(text)
    return result


def handle_get_visualization_call(text: str, interface):
    result = interface.get_visualisation(text)
    return result
