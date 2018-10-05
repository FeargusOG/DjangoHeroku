# PSN Value
This project provides a Djano application, to be deployed on Heroku, for determining the current value of offerings within the PSN store for PS4 games.

## Tech List:

|   | Name   | Description |
| :------: | :------: | :------: |
| ![Python](readme/python.png "Python") | Python | Programming Language |
| ![Django](readme/django.png "Django") | Django | Python Web Framework |
| ![Redis](readme/redis.png "Redis") | Redis | Message Broker |
| ![Celery](readme/celery.png "Celery") | Celery | Asynchronous Task Queue |
| ![Django-Celery-Beat](readme/celery.png "Django-Celery-Beat") | Django-Celery-Beat | Database-backed Periodic Tasks |
| ![Gunicorn](readme/gunicorn.png "Gunicorn") | Gunicorn | Python HTTP Server |
| ![Whitenoise](readme/whitenoise.png "Whitenoise") | Whitenoise | Python Web App Static File Serving |
| ![Requests](readme/requests.png "Requests") | Requests | Python HTTP Library |
| ![PostgreSQL](readme/postgresql.png "PostgreSQL") | PostgreSQL | Object-Relational Database Management System |
| ![Psycopg](readme/psycopg.png "Psycopg") | Psycopg | PostgreSQL for Python |
| ![Heroku](readme/heroku.png "Heroku") | Heroku | PAAS Provider |
| ![Cloudinary](readme/cloudinary.png "Cloudinary") | Cloudinary | SAAS Image and Video Serving |

## Description:
The aim of this project is to provide a web application for determining the current value of offerings within the PSN store for PS4 games. This is accomplished by periodically polling the PSN store for updated pricing and rating information which is used in producing the current value of each game within the store. This scheduling of polls to the store is done using Celery and Redis.

The current value of a game is determined using a number of factors such as:
1. The mean rating of PS4 games in the store
2. The number of ratings made by users for the specific game
3. The standard deviation of ratings with the store and the game in questions deviation from the mean.
4. The current price of the game and the size of discount offered on the game (if any).

All of the relevant game information is stored in a local PostgreSQL DB to minimise hits to the PSN Store. Similiarly, game thumbnails are stored in Cloudinary to prevent hits to the PSN Store when displaying the list of games and their value score.
