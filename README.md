# Django + Django REST Framework

This school project is developed using Django with Django REST Framework to build a backend Mahjong API.
Django uses the classic MVC structure contained in python packages. 

Rapid overview of a Django project:
1. To create add a new functionality, let's say score calculation with different yakus, start by creating a new python package with this command: `python manage.py startapp scoring`. 
2. If you want to add Models and Controllers you need to go in the models.py file.
3. If you want to add Views you need to add them in views.py file and reference them in urls.py file, this files must then be referenced in the riichiBackend/urls.py file.
4. If you want to export data from a model to a View JSON, create a serializers.py file and start building your own serializers.
5. If you have constants, and you don't know where to put them, create an utils.py file and put them in.
6. For your package to take effect you also need to add it in INSTALLED_APPS in riichiBackend/settings.py
7. After having creating new models you must run `python manage.py makemigrations` and `python manage.py migrate` before running your server with `python manage.py runserver`

For more info on Django check out [Django docs](https://docs.djangoproject.com/en/4.1/).

The backend is deployed with a postgreSQL database using the docker-compose.yml file, if you don't have Docker get it [here](https://docs.docker.com/get-docker/).  

## TODO

1. Adding ron and tsumo to end a hand
2. Adding riichi
3. Adding yakus with a new package to calculate the score of a hand
4. Handles the following hands and rounds of the game
5. Transform the tenpai algorithm to return tiles the player is waiting for