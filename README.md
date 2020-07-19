# Colorific
> Image color extraction application

[![stkrizh](https://circleci.com/gh/stkrizh/colorific.svg?style=shield)](https://circleci.com/gh/stkrizh/colorific)
[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

The app displays a color palette for all the colors identified in uploaded images.
Currently it uses [K-means](https://scikit-learn.org/stable/modules/clustering.html#k-means)
clustering algorithm internally for color extraction.

**>> [Live demo](https://colorific.stkrizh.dev)**


## Development setup
Make sure you have [Docker](https://docs.docker.com/get-docker/) and 
[docker-compose](https://docs.docker.com/compose/install/)
installed on your system.

Clone the repository:
```
git clone git@github.com:stkrizh/colorific.git
cd colorific
```
Create **Python 3.8** virtual environment:
```
python3.8 -m venv --prompt Colorific .venv
source .venv/bin/activate
```
Install dependencies:
```
pip install -r requirements/main.txt
```
Create `.env` file with the following configuration:
```
IMAGE_INDEXING=false

POSTGRES_USER=user
POSTGRES_PASSWORD=123
POSTGRES_DB=colorific_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

POSTGRES_TEST_USER=test_user
POSTGRES_TEST_PASSWORD=123
POSTGRES_TEST_DB=colorific_db_test
POSTGRES_TEST_HOST=localhost
POSTGRES_TEST_PORT=5433

REDIS_HOST=localhost
REDIS_PORT=6379

CORS_ALLOW_ORIGIN=*

OMP_NUM_THREADS=1
```
Run PostgreSQL database and Redis services:
```
make docker-up
```
Apply DB migrations:
```
make migrate
```
Run tests:
```
make test
```
Run backend application in development mode:
```
make run
```

### Frontend application
Make sure you have [Node.js](https://nodejs.org/en/) (>= v12.18.2) and 
[npm](https://www.npmjs.com/) (>=6.14.5)
installed on your system.

All the following commands should be run within `frontend/` directory.

Install dependencies:
```
npm install
```

Run frontend application in development mode:
```
./node_modules/@angular/cli/bin/ng serve
```

## Contact
[stkrizh.dev](https://stkrizh.dev)
