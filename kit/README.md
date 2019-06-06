
# Kusto Ingestion Tools (Kit)  
  
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
* [Concept](##concept)  
* [Usage](##usage)
* [Examples](##examples)

## Concept
Given a data source, usually the workflow would consist of:  
  
1. Describing the data source.  
2. Preparing the target data store (in our case, Kusto)  
3. Mapping Source to Target  
4. Loading the data  
5. *Optional* : Automation / Moving to Production  
  
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
  
#### Conflicting Files  
* Safe `--data-conflict=safe` - Safest option is providing conflict resolution flag, which will bail in case if any conflicts (default)   
  
Below are not implemented yet   
* Extend `--data-conflict=extend` - In any case of conflicts, kit will try and extend the scheme as much as possible to accommodate for change   
* Merge `--data-conflict=merge` - In case you want to be more aggressive, merge can be used, which will do it's best to follow your wishes (in case of conflicts, will try to auto-resolve)  
  
#### Schema Conflicts  
* Safe `--schema-conflict=safe` - Safest option is providing conflict resolution flag, which will bail in case if any conflicts (default)   
  
Below are not implemented yet:  
* Append `--schema-conflict=append` - In any case of conflicts, kit will create copies (if table exists but schema is mismatched, will create a new table with same name + '_')   
* Merge `--schema-conflict=merge` - In case you want to be more aggressive, merge can be used, which will do it's best to follow your wishes (in case of conflicts, will try to auto-resolve)  
  
### Files  
  
#### Database file  
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
  
#### Creation Methods:  
  
**Manually**   
`kit schema create --empty > schema.json`  
  **From an existing cluster**  
  
`kit schema create -h 'https://mycluster.kusto.windows.net' -u appkey/userid -p appsecret/password -a authprovider > schema.json`  
  
**From an sql file**  
  
`kit schema create -sql create_statements.sql > schema.json`  
  
**From a folder with raw data**  
  
`kit schema create -d path/to/dir > schema.json`  
  
**More to come...**  
  
  
#### Sync   
Once we have a database file, we can generate the entire scheme using  
  
`kit schema sync -f schema.json`  
  
#### Manifest file  
A file to describe the details of an ingestion which can be run later  
  
```json  
{  
 "databases": [ "same as schema.json" ], "mappings": [ { "name": "aka_name_from_csv", "columns": [ { "source": { "index": 0, "data_type": "str" }, "target": { "index": 0, "data_type": "str" } } ] } ], "operations": [ { "database": "imdb", "sources": [ { "files": [ "1.csv", "...", "99.csv"          ],  
 "mapping": "aka_name_from_csv" } ], "target": [ "aka_name" ] } ]}  
```  
  
#### Generate   
This file can be generated before ingestion operation to describe what is going to happen during ingestion  
  
  
**Manually**  
  
`kit ingestion manifest --db database.json `  
  
**  
##  Examples
  
### Example 1 : Ingest CSV Dataset (Join Order Benchmark)  
  
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

`kit count --table aka_name -h dadubovs1.westus -db imdb` - should show 901343

And take a peek at the data:
`kit peek --table aka_name -n 10 -h dadubovs1.westus -db imdb`

  
### Example 2 : Ingest CSV ML Tables

Kaggale has tons of interesting dataset for ML/AI purposes.

Let's try and ingest some:

https://www.kaggle.com/mlg-ulb/creditcardfraud/
https://www.kaggle.com/START-UMD/gtd/

Uploaded to our azure storage for convenience:

`wget https://imdb2013dataset.blob.core.windows.net/data/creditcard.csv.gz --no-check-certificate`  
`wget https://imdb2013dataset.blob.core.windows.net/data/globalterrorism.csv.gz --no-check-certificate`
  or   
`curl https://imdb2013dataset.blob.core.windows.net/data/creditcard.csv.gz --output creditcard.csv.tgz`
`curl https://imdb2013dataset.blob.core.windows.net/data/globalterrorism.csv.gz --output globalterrorism.csv.tgz`   
 

### Example 2: CDM  
  
`kit ingest --metadata /path/to/cdmmodel.json --meatatype cdm`  
  
### Example 3: Apache Hive MetaStore  
  
`kit ingest --metadata /path/to/cdmmodel.json --meatatype cdm`