# Tenmiles Assignment
Simple project to fetch mails from GMail after authenticating a user
and storing their OAuth token.

Then CRUD of some conditions, actions, and rules made out of them, to take
some actions on those mails

## Installation

* Clone this repo
* Create a virtualenv (better use virtualenvwrapper: `mkvirtualenv <venv-name>`)
* Install python requirements: `pip install -r requirements.txt`
* Run migrations: `./manage.py migrate`
* Create a superuser to get initial access to all APIs etc: `./manage.py createsuperuser` and follow the steps
* Run server: `./manage.py runserver`, you can then goto [http://localhost:8000](http://localhost:8000)
* Run celery: `celery worker -A gmailops.celery -c1 -linfo` (here we just use the concurrency of 1 worker with INFO level of log output)

That's it.


## Usage

* Run server at port 8000 (django runserver by default runs on it)
And make sure you access it using the `localhost` host name, because the client
json I've added from Google Developer console to run this project has redirect URI set to http://localhost:8000/google-oauth2callback/
* Goto [http://localhost:8000](http://localhost:8000), and if you're not logged in, log in.
* You'll see a message which asks you to click on the link to authorize our Google app to have access to your GMail mails.
* Once you do that, and give access on the OAuth consent screen, you'll be redirected back to the home page, this time seeing the message that you're authorized.

Here, the application is a little crude, as there's no check or button to do re-auth flow or to tell our app to re-sync the mails etc. We'll have to manually delete the credentials of the user, then reload the home page, then authorize, etc, to fetch the mails.

* Once the authorization is done and you're redirected back to the home page, a background task is already sent off to do a full sync of your mails to our database.

* **Rule creation**: Goto [http://localhost:8000/api/v1] (http://localhost:8000/api/v1) and create Condition(s), Action(s) and Rule(s) as according to need.

CRUD of these is working perfectly.


## Enhancements  

TODO:

- The only part of the assignment not done:  
    `Add sufficient validations and error cases.`

Unfortunately, I honestly couldn't get much time outside of office and during the weekends because, circumstances.