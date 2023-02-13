import spacy
from spacy.tokens import DocBin
import pandas as pd
import re

pd.set_option('display.max_colwidth', -1)


def massage_data(name):
    # Preprocess name string to remove new line characters, add comma punctuations etc.
    cleansed_name1 = re.sub(r'(,)(?!\s)', ', ', name)
    cleansed_name2 = re.sub(r'(\\n)', ', ', cleansed_name1)
    cleansed_name3 = re.sub(r'(?!\s)(-)(?!\s)', ' - ', cleansed_name2)
    return cleansed_name3


def get_name_span(name=None, name_component=None, label=None):
    """
    Search for specified name component and get the span.
    """

    if pd.isna(name_component) or str(name_component) == 'nan':
        pass
    else:
        name_component1 = re.sub(r'\.', '', name_component)
        name_component2 = re.sub(r'(?!\s)(-)(?!\s)', ' - ', name_component1)
        span = re.search('\\b(?:' + name_component2 + ')\\b', name)
        # print(name + ' and entity ' + name_component)
        return span.start(), span.end(), label


def extend_list(entity_list, entity):
    if pd.isna(entity):
        return entity_list
    else:
        entity_list.append(entity)
        return entity_list


# Name,First_Name,Middle_Name,Last_Name
def create_entity_spans(df, tag_list):
    """
    Create entity spans for training/test datasets
    """
    df['Name'] = df['Name'].apply(lambda x: massage_data(x))
    df["FirstNameTag"] = df.apply(
        lambda row: get_name_span(name=row['Name'], name_component=row['First_Name'], label='FIRST_NAME'), axis=1)
    df["MiddleNameTag"] = df.apply(
        lambda row: get_name_span(name=row['Name'], name_component=row['Middle_Name'], label='MIDDLE_NAME'), axis=1)
    df["LastNameTag"] = df.apply(
        lambda row: get_name_span(name=row['Name'], name_component=row['Last_Name'], label='LAST_NAME'), axis=1)
    df['EmptySpan'] = df.apply(lambda x: [], axis=1)

    for i in tag_list:
        df['EntitySpans'] = df.apply(lambda row: extend_list(row['EmptySpan'], row[i]), axis=1)
        df['EntitySpans'] = df[['EntitySpans', 'Name']].apply(lambda x: (x[1], x[0]), axis=1)
    return df['EntitySpans']


# https://spacy.io/usage/training#training-data
def get_doc_bin(training_data, nlp):
    """
    Create DocBin object for building training/test corpus
    """
    # the DocBin will store the example documents
    db = DocBin()
    for text, annotations in training_data:
        doc = nlp(text)  # Construct a Doc object
        ents = []
        for start, end, label in annotations:
            span = doc.char_span(start, end, label=label)
            ents.append(span)
        if None in ents:
            print('None Type detected in:')
            print(text)
            print('with annotations')
            print(annotations)
            print('creates entitites:')
            print(ents)
            continue
        doc.ents = ents
        db.add(doc)
    return db


# Load blank English model. This is needed for initializing a Document object for our training/test set.
nlp = spacy.blank("en")

# Define custom entity tag list
tag_list = ["FirstNameTag", "MiddleNameTag", "LastNameTag"]

###### Training dataset prep ###########
# Read the training dataset into pandas
df_train = pd.read_csv(filepath_or_buffer="./corpus/trainingdata/name_data.csv", sep=",", dtype=str)

# Get entity spans
df_entity_spans = create_entity_spans(df_train.astype(str), tag_list)
training_data = df_entity_spans.values.tolist()

# Get & Persist DocBin to disk
doc_bin_train = get_doc_bin(training_data, nlp)
doc_bin_train.to_disk("./corpus/spacy-docbins/train.spacy")
######################################


###### Validation dataset prep ###########
# Read the validation dataset into pandas
df_test = pd.read_csv(filepath_or_buffer="./corpus/trainingdata/name_validation_data.csv", sep=",", dtype=str)

# Get entity spans
df_entity_spans = create_entity_spans(df_test.astype(str), tag_list)
validation_data = df_entity_spans.values.tolist()

# Get & Persist DocBin to disk
doc_bin_test = get_doc_bin(validation_data, nlp)
doc_bin_test.to_disk("./corpus/spacy-docbins/test.spacy")
##########################################
