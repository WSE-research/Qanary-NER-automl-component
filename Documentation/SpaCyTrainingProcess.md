# Model Training
To explain the training process of a model, we go through the process step by step at the example of the address recognition model.

## Data Preparation
To train a spaCy model, we use data in a CSV format. It contains columns for the text and each entity the model should be able to classify. Then, each data-text is written into the text-column and additionally the values for each entity inside the text are highlighted additionally. If a text does not contain a value for a defined entity, the corresponding cell must be empty.
To explain the process, we follow the example of the address recognition. The dataset of this model would look like this:

| **Address**                                                         | **Street**        | **House\_Nr** | **Post\_Code** | **City**        |
|---------------------------------------------------------------------|-------------------|---------------|----------------|-----------------|
| My working address is Lohmannstraße 23 06366 Köthen                 | Lohmannstraße     | 23            | 06366          | Köthen          |
| My mailing address is Bernburger straße 55, 06366, Köthen (Anhalt). | Bernburger straße | 55            | 06366          | Köthen (Anhalt) |
| I am living in Marion Street 486.                                   | Marion Street     | 486           |                |                 |
| My address is 3452 Melody Lane, 23060 Glen Allen.                   | Melody Lane       | 3452          | 23060          | Glen Allen      |

To train a model, we need two such datasets, one being training data and one validation data.
In the [generate_spacy_data](https://github.com/AnnemarieWittig/RecognitionService/blob/main/SpacyModels/spacy_address_model/generate_spacy_data.py) script, the given datasets are cleaned up and rewritten into a spaCy compatible format. The format for the first datapoint would be:
```
(My working address is Lohmannstraße 23 06366 Köthen,
   [(22, 35, STREET), (36, 38, HOUSE_NR),
    (39, 44, POST_CODE), (45, 51, CITY)])
```
We are telling the model exactly, where each entity starts and ends within the text. Additionally, the new format must be serialized, which is why a DocBin object is initialized with it. The DocBin data is then stored separately to be used within the training. The script can be called without further input.
## Configuration data
For the training, a config is needed. Starting with a simple skeleton in a .cfg file, such as:
```config
[components]
[components.ner]
factory="ner"[nlp]
lang = "en"
pipeline = ["ner"][training]
[training.batch_size]
[@schedules](http://twitter.com/schedules) = "compounding.v1"
start = 4
stop = 32
compound = 1.001
```
This file can be adjusted to the needs of the model. The spaCy documentation offers a [generator ](https://spacy.io/usage/training#quickstart) that generates a skeleton based on information given by the user.
This is then transformed to a full-fledged configuration using the command
```shell
python -m spacy init fill-config {Path to skeleton} {Path to new config}
```
This can be adjusted to the needs of the user. E.g., you could adjust the "max_steps" and "eval_frequency" of the model, which defines the maximal "number of update steps to train for" (0 meaning unlimited number of steps). In the [example config](https://spacy.io/usage/training#config) in the documentation many other values are explained.

## Initializing training
To start the training, another shell command must be run:
```shell
python -m spacy train {Path to config} --paths.train {path to training data DocBin file} --paths.dev {Path to test data DocBin file} --output {path to output folder}
```
This triggers the training-process. In the output folder, two models will be saved: The best performing (which we use in the classification service) called `model-best` and the last one generated `model-last`.

## Using the model in python
To use the model, it must be loaded into python.
```python
import spacy
nlp=spacy.load("./output/models/model-best")
```
It can then be accessed to classify given texts.
```python
address = 'My place of residence is Frankfurter Straße 50, 12345 Frankfurt am Main'
doc=nlp(address)
ent_list=[(ent.text, ent.label_) for  ent  in  doc.ents]
print("Address string -> "+address)
print("Parsed address -> "+str(ent_list))
print("******")
```

##
The process is based on a [medium article](https://medium.com/globant/building-an-address-parser-with-spacy-e3376b7cff)
##

**NOTE**: Due to working with Rasa connected to this project, all processes shown use python 3.8