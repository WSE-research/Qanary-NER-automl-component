# Data Generation
In this article an approach to generate data for a spaCy nlp model is shown. To train a spaCy model, we use data in a CSV format. It contains columns for the text and each entity the model should be able to classify. Then, each data-text is written into the text-column and additionally the values for each entity inside the text are highlighted additionally. If a text does not contain a value for a defined entity, the corresponding cell must be empty.

First, we have to define what parameters the model should classify. In this example, those are streetnames, house numbers, post codes and cities.
The data set can then be defined by hand in a table, containing a general text and highlighting the values of the parameters. Those tables are structured as:

| **Address**                                                         | **Street**        | **House\_Nr** | **Post\_Code** | **City**        |
|---------------------------------------------------------------------|-------------------|---------------|----------------|-----------------|
| My working address is Lohmannstraße 23 06366 Köthen                 | Lohmannstraße     | 23            | 06366          | Köthen          |
| My mailing address is Bernburger straße 55, 06366, Köthen (Anhalt). | Bernburger straße | 55            | 06366          | Köthen (Anhalt) |
| I am living in 486 Marion Street, 05301 Brattleboro.                | Marion Street     | 486           | 05301          | Brattleboro     |
| My address is 3452 Melody Lane, 23060 Glen Allen.                   | Melody Lane       | 3452          | 23060          | Glen Allen      |

To save some manual labor and generate a significantly higher number of data, we follow a different approach.  
**Note: the creation of entity spans does not work if any entities include "(", ")" or "."**

To automatically generate data, we first have to prepare some templates, such as:
- I live in {{STREET}} {{HOUSENR}}.
- I am currently residing in {{POSTCODE}} {{CITY}}.
- I reside at {{STREET}} {{HOUSENR}} {{CITY}}.
- My main address is {{STREET}} {{HOUSENR}}, {{POSTCODE}} {{CITY}}.
- Currently, my residence is {{CITY}}, {{HOUSENR}} {{STREET}}.

They use placeholders for the values we later want to classify. We then randomly fill these templates and placeholders using Open Street Map data. Given that the data does not always have values for all the parameters, some will sometimes be left empty, creating more divers texts.

A python notebook doing just this is in the [repository](). This process can be applied to any other classification model.

The generated data has then to be split in a ratio of choice, s.t. there is a dataset for training and one for validation
