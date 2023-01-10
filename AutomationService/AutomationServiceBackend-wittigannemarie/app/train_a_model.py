import spacy
from dotenv import load_dotenv
import sys
import os.path
import logging
from helper.spacy_trainer import ModelHelper
from helper.my_exceptions import NoTrainingdataException


def check_if_model_exists(path_to_model):
    try:
        spacy.load(path_to_model)
        return True
    except:
        return False


load_dotenv()

training_data_path = os.getenv('TRAININGLOCATION')
training_data_output = os.getenv('TRAININGDOCBINS')
language = ""
modeltype = ""

numberofarguments = len(sys.argv[1:])

if numberofarguments == 0:
    logging.warning("No language and modeltype were given. For training, the default will be used.")

elif numberofarguments == 1:
    logging.warning("Either the language or the model type is missing. For training, default will be used.")
else:
    language = sys.argv[2]
    modeltype = sys.argv[1]

helper = ModelHelper()

# check if model copied into output folder (default directory)
if check_if_model_exists("/code/app/spacy_model/output/model-best"):
    logging.info("A trained model was given. Nothing to be done here")
else:
    # check if training and validation data is given
    logging.info("Attempting training a new model.")
    if not os.path.exists(training_data_path + 'train.csv'):
        raise NoTrainingdataException("No training data given. Training not possible.")
    elif not os.path.exists(training_data_path + 'test.csv'):
        raise NoTrainingdataException("No testing data given. Training not possible.")
    else:
        helper.generate_docbins(training_data_path, training_data_output)
        helper.train_model("/code/app/spacy_model/output",
                            "/code/app/spacy_model/corpus/spacy-docbins/train.spacy",
                            "/code/app/spacy_model/corpus/spacy-docbins/test.spacy",
                            language,
                            modeltype)
        logging.info("Training concluded.")
