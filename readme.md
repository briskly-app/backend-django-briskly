# Project structure

```
apps/
  logistics/     # GTFS, cities, stops, attractions, destination search
  trips/         # User trips, trip connections (segments), connection notes
core/            # Shared API exception handler, middlewares
briskly/         # Django project settings
```

If you upgrade from the old monolithic `routes` app and tables already exist, run:

```
python manage.py migrate logistics --fake-initial
python manage.py migrate trips --fake-initial
```

# How to run?

Create environment and install libraries

```
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

remember to add .env with corresponding variables, send message to author to receive details

To start django app:

```
python manage.py runserver
```

in case you installed new libraries remember to add them to requirements.txt with:

```
git freeze > requirements.txt
```

If you make changes in structure of database remember to make migrations

```
python manage.py makemigrations
python manage.py migrate
```

If you want to start seeder command, check them in apps/logistics/management/commands and run

```
python manage.py [command_name] [parameters]
```

Tip: You can check all available custom commands by running 'python manage.py help'
