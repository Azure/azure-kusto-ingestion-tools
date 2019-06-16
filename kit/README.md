
# Kusto Ingestion Tools (Kit)  


[*azure-kusto-ingestion-tools*]("https://github.com/Azure/azure-kusto-ingestion-tools/tree/master/kit")  a simple toolkit to help with ingestions, avialble here
<br>
[![PyPI version](https://badge.fury.io/py/azure-kusto-ingestion-tools.svg)](https://badge.fury.io/py/azure-kusto-ingestion-tools)
[![Downloads](https://pepy.tech/badge/azure-kusto-ingestion-tools)](https://pepy.tech/project/azure-kusto-ingestion-tools)<br>

## Purpose  
Make ingestion simpler (*at least for common cases*).
After creating an ADX (Kusto) cluster via Azure portal, we want to explore / visualize some data. 
When evaluating data stores / tools we usually want to  just POC capabilities and move fast.  

That is what this project was created for. 
It contains features to support:

1. Data source **schema** inference (csv / kusto/ ...)
2. Common **ingestion** scenarios (from file /entire folder / ...)
3. Other helpful utilities (kql generator, ...)

## TOC
* [Concept](#concept)  
* [Install](#install)
* [Usage](#usage)
* [Examples](#examples)

## Concept
Given a data source, usually the workflow would consist of:  
  
1. Describing the data source.  
2. Preparing the target data store (in our case, Kusto)  
3. Mapping Source to Target  
4. Loading the data  
5. *Optional* : Automation / Moving to Production  
  
## Install

### Minimum Requirements
* Python 3.7+
* See setup.py for dependencies

### Pip

To install via the Python Package Index (PyPI), type:

`pip install azure-kusto-ingestion-tools`

This will expose a new cli commands : `kit --help`


## Usage  

### Basic  
  
`kit ingest -d /path/to/data/imdb -h mycluster.westus`  
  
The following command will try to ingest all files in `/path/to/data/imdb` (non-recursive) using type inference.  
  
  
**<!>NOTICE<!>**: without providing any other arguments, this command is extremely *opinionated*, and will assume the following:  
  
### Options  
  
#### Auth  
Every command that needs to authenticate against kusto, will require authentication arguemnts.

By default, will try to grab token from [azure cli](https://docs.microsoft.com/en-us/cli/azure/?view=azure-cli-latest)

Other options are:

App:

`kit [command] -app {app_id}:{app_secret}`

User:

`kit [command] -user {user_id}:{password}` 
  
#### Naming  
* **database** will be set to is the dir in which data sits, so `/path/to/data/imdb` will look for, and create if missing, a database named `imdb`.   
If more control is need, try `--database`  
* **tables** are actual file names, so `/path/to/data/imdb/aka_name.csv` will look for, and create if missing, a table named `aka_name`.   
This can be tweaked by making sure data is split into folder, where any folder would be a table.  
This recursive mode assumes that the table structure is the same for all files.    

### Files  
  
#### Database Schema file  
This is a simple way to describe a database.  
  
This can be used to describe a db schema using plain JSON format, and thus easily copy entire database schemas.  
  
```json 
{
    "name": "imdb",
    "tables": [{
        "name": "aka_name",
        "columns": [{
            "dtype": "int",
            "name": "id",
            "index": 0
        }, {
            "dtype": "int",
            "name": "person_id",
            "index": 1
        }, {
            "dtype": "string",
            "name": "name",
            "index": 2
        }, {
            "dtype": "string",
            "name": "imdb_index",
            "index": 3
        }, {
            "dtype": "string",
            "name": "name_pcode_cf",
            "index": 4
        }, {
            "dtype": "string",
            "name": "name_pcode_nf",
            "index": 5
        }, {
            "dtype": "string",
            "name": "surname_pcode",
            "index": 6
        }, {
            "dtype": "string",
            "name": "md5sum",
            "index": 7
        }]
    },
    ...
    ]  
}
```  

**From an existing cluster**  
  
`kit schema create -h 'https://mycluster.kusto.windows.net' -db imdb > imdb_schema.json`  
  
**From an sql file**  
  
`kit schema create -sql imdb.sql > schema.json`  
  
**From a folder with raw data**  
  
`kit schema create -d path/to/dir > schema.json`  
  
**More to come...**  
  
#### Manifest file  
A file to describe the details of an ingestion which can be run later  
  
```json  
{  
 "databases": [ "same as schema.json" ], 
 "mappings": [{ 
  "name": "aka_name_from_csv", 
  "columns": [{ 
    "source": { 
        "index": 0, 
      "data_type": "str" 
      }, 
      "target": { 
        "index": 0, 
        "data_type": "str" 
       }
    }] 
   }], 
   "operations": [{ 
      "database": "imdb", 
      "sources": [{ 
        "files": ["1.csv", "...", "99.csv"], 
      "mapping": "aka_name_from_csv" 
      }], 
      "target": [ "aka_name" ] 
   }]
 }  
```  
  
##  Examples
  
### Example 1 : Ingest IMDB Dataset , CSV files (used in Join Order Benchmark)  
  
One useful scenario would be to load an entire existing dataset into Kusto.  
Let's take for example the [Join Order Benchmark](https://github.com/gregrahn/join-order-benchmark) used in the paper [How good are query optimizers really?](http://www.vldb.org/pvldb/vol9/p204-leis.pdf).  
  
#### 1. Copy files to local dir:  
  
[Download](https://imdb2013dataset.blob.core.windows.net/data/imdb.tgz) from Azure Storage  
`wget https://imdb2013dataset.blob.core.windows.net/data/imdb.tgz --no-check-certificate`  
  or   
`curl https://imdb2013dataset.blob.core.windows.net/data/imdb.tgz --output imdb.tgz`  
  
  
Original Files [are available](https://homepages.cwi.nl/~boncz/job/imdb.tgz), but are malformed (don't conform to https://tools.ietf.org/html/rfc4180).   
One can fix them using tools like [xsv](https://github.com/BurntSushi/xsv/releases/tag/0.13.0),   
but this is we shall leave error handling for another section.   
  
#### 2. Extract files:  
  
`tar -xvzf imdb.tgz`  
  
  
#### 3. Download SQL Create commands:  
  
`wget https://raw.githubusercontent.com/gregrahn/join-order-benchmark/master/schema.sql -O imdb.sql --no-check-certificate`  
  
or  
  
`curl https://raw.githubusercontent.com/gregrahn/join-order-benchmark/master/schema.sql --output imdb.sql`  
  
#### 4. Create schema from sql statement  
  
`kit schema create -sql schema.sql > imdb_schema.json`  
  
#### 5. Apply schema on cluster   
Assuming we already have a cluster, and we are signed in using az cli, we can just apply the schema on a database we choose:  
  
`kit schema apply -f imdb_schema.json -h mycluster.westus -db imdb`  
  
#### 6. Ingest data from local files  
  
`kit ingest -d . --pattern "*.csv" -h mycluster.westus -db imdb`  
  
#### 7. Query  
  
Using the Azure portal, you can now easily login and query your data.   
  
You can always make sure that data was loaded by comparing the source line count with target column count:

`xsv count aka_name.csv` - should show 901343 rows

or

`wc -l aka_name.csv` - should show 901343 rows

Query from kusto should show the same:

`kit count --table aka_name -h mycluster.westus -db imdb` - should show 901343

And take a peek at the data:
`kit peek --table aka_name -n 10 -h mycluster.westus -db imdb`

  
### Example 2 : Ingest Kaggle ML Datasets, CSV and JSON

Kaggale has tons of interesting dataset for ML/AI purposes.

Let's try and ingest some:

https://www.kaggle.com/mlg-ulb/creditcardfraud/
https://www.kaggle.com/START-UMD/gtd/

Uploaded to our azure storage for convenience:

```
wget https://imdb2013dataset.blob.core.windows.net/data/creditcard.csv.gz --no-check-certificate  
wget https://imdb2013dataset.blob.core.windows.net/data/globalterrorism.csv.gz --no-check-certificate
wget https://imdb2013dataset.blob.core.windows.net/data/arxivData.csv.gz --no-check-certificate
```
  or   
```
curl https://imdb2013dataset.blob.core.windows.net/data/creditcard.csv.gz --output creditcard.csv.gz
curl https://imdb2013dataset.blob.core.windows.net/data/globalterrorism.csv.gz --output globalterrorism.csv.gz   
curl https://imdb2013dataset.blob.core.windows.net/data/arxivData.json.gz --output arxivData.json.gz
```
 
 Once downloaded and unzipped, same idea, only this time files contain headers, so schema is infered:

`kit ingest -d . -h mycluster.westus -db ml --headers`

### Example 3 : Complex nested JSON mappings

Let's look at a more advance use case:

`wget https://imdb2013dataset.blob.core.windows.net/data/demo.json --no-check-certificate`
    
   or

`curl https://imdb2013dataset.blob.core.windows.net/data/demo.json --output demo.json`

Say our data is a json lines files, where each item looks like:

`{"header":{"time":"24-Aug-18 09:42:15", "id":"0944f542-a637-411b-94dd-8874992d6ebc", "api_version":"v2"}, "payload":{"data":"NEEUGQSPIPKDPQPIVFE", "user":"owild@fabrikam.com"}}`

It seems that we have a nested object. 
Because we are not sure what will happen, let's dry run.
Let's try and `--dry` run an ingestion with `--object-depth 2`.

`kit ingest -f demo.json --object-depth 2 -h mycluster.westus -db ml --dry > manifest.json`

This produces the following `manifest.json` which contains the operations to be executed.

```json
{
  "databases": [
    {
      "name": "ml",
      "tables": []
    }
  ],
  "mappings": [
    {
      "name": "demo_from_json",
      "columns": [
        {
          "source": {
            "dtype": "string",
            "name": "header.time",
            "index": null
          },
          "target": {
            "dtype": "string",
            "name": "header.time",
            "index": null
          }
        },
        {
          "source": {
            "dtype": "string",
            "name": "header.id",
            "index": null
          },
          "target": {
            "dtype": "string",
            "name": "header.id",
            "index": null
          }
        },
        {
          "source": {
            "dtype": "string",
            "name": "header.api_version",
            "index": null
          },
          "target": {
            "dtype": "string",
            "name": "header.api_version",
            "index": null
          }
        },
        {
          "source": {
            "dtype": "string",
            "name": "payload.data",
            "index": null
          },
          "target": {
            "dtype": "string",
            "name": "payload.data",
            "index": null
          }
        },
        {
          "source": {
            "dtype": "string",
            "name": "payload.user",
            "index": null
          },
          "target": {
            "dtype": "string",
            "name": "payload.user",
            "index": null
          }
        }
      ]
    }
  ],
  "operations": [
    {
      "database": "ml",
      "sources": [
        {
          "files": [
            "C:\\Users\\dadubovs\\temp\\ml_datasets\\demo.json"
          ],
          "mapping": "demo_from_json",
          "options": {},
          "data_format": "json"
        }
      ],
      "target": "demo"
    }
  ]
}
```

Now, let's say that we don't need the `id` field, we can edit the mapping and save it.


If we are still unsure, and want to get a better understanding are the commands that will be created, we can inspect the kql

`kit kql -m manifest.json`

Which should output something like:

```
// Table Creation Commands:
.create table demo (['header.time']:string,['header.api_version']:string,['payload.data']:string,['payload.user']:string)

// Ingestion Mapping Creation Commands:
.create table demo ingestion json mapping "demo_from_json" '[{"column":"header.time","path":"$.header.time","datatype":"string"},{"column":"header.api_version","path":"$.header.api_version","datatype":"string"},{"column":"payload.data","path":"$.payload.data","datatype":"string"},{"column":"payload.user","path":"$.payload.user","datatype":"string"}]'
```

Once we are ready, we can resume our ingestion based on the manifest

`kit ingest -m manifest.json -h mycluster.westus`
