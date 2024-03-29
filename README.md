# epadd-curator-app
This is a service will monitor the Nextcloud S3 buckets that the ePADD user will export bags to. It will call DIMS to kick off the DAIS pipeline for automatic ingest into DRS.

* log files are in the `logs` subdirectory

## Technology Stack
##### Language
NodeJS

##### Framework
Express

##### Development Operations
Docker Compose

## Local Development Environment Setup Instructions

### 1: Clone the repository to a local directory
`git clone git@github.com:harvard-lts/epadd-curator-app.git`

### 2: Create app config

##### Create config file for environment variables
- Make a copy of the config example file `./env-example.txt`
- Rename the file to `.env`
- Replace placeholder values as necessary

*Note: The config file .env is specifically excluded in .gitignore and .dockerignore, since it contains credentials it should NOT ever be committed to any repository.*

### 3: Create drsConfig.txt

- Make a copy resources/drsConfig.txt.template to the resources directory and name it drsConfig.txt

- Copy drsConfig.txt.template to the resources directory and name it drsConfig.txt


### 4: Start

##### START

This command builds all images and runs all containers specified in the docker-compose-local.yml configuration.

```
docker-compose -f docker-compose-local.yml up -d --build --force-recreate
```

### 5: SSH into Container (optional)

##### Run docker exec to execute a shell in the container by name

Open a shell using the exec command to access the epadd-curator-app container.

```
docker exec -it epadd-curator-app bash
```

### 5: Stop

##### STOP AND REMOVE

This command stops and removes all containers specified in the docker-compose-local.yml configuration. This command can be used in place of the 'stop' and 'rm' commands.

```
docker-compose -f docker-compose-local.yml down
```

## Running tests

### 1: Setup Local Environment using instructions from above

### 2: Exec into the container

```
docker exec -it epadd-curator-app bash
```

### 3: Run the tests

```
python3 -m unittest scripts/unit_tests.py 
```

## Running System Tests

### 1: Setup Local Environment using instructions from above or deploy to dev

### 2: Call the following endpoint to kick off test - replace host with 'localhost' when running locally

#### To provide an OSN, execute the following

```
curl http://ltsds-cloud-dev-1.lib.harvard.edu:10586/testExport?osn={yourTestOSN}
```

#### To provide use the default OSN i.e. osn_{timestamp}, execute the following

```
curl http://ltsds-cloud-dev-1.lib.harvard.edu:10586/testExport
```

## Running Performance Tests in QA

Performance tests write their own drsConfig.txt and will ignore any drsConfig.txt files that are provided with the directory.  The provided drsConfig.txt generates a random OSN of the form osn_<timestamp> and sends emails to DTS@HU.onmicrosoft.com

## Prerequisites

- NextCloud account that allows access to the directory int-test-data-store (This looks like epadd-int-test-data-store in the NC directory)


### 1: Upload desired directory to epadd-int-test-data-store (see Prerequisites) or utilize the existing data

### 2: From a browser, make a call to:
```
http://ltsds-cloud-qa-1.lib.harvard.edu:10586/runTest/<name of directory>
```
### 3: Verify that the batch report comes through 
This can be done in two ways:
1. Receiving an email to DTS@HU.onmicrosoft.com if you are part of that group
2. Manually checking the dropbox for a load report.  In QA, the ePADD dropbox is located on ldi3 under epaddqa_secure in the drs QA dropboxes directories.  Load reports will show up under the batch name (osn_<timestamp>-batch)
