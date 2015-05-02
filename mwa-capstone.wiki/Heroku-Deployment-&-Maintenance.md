### The Basics
Heroku has an [excellent tutorial](https://devcenter.heroku.com/articles/getting-started-with-python#introduction) describing the basics of setting up Heroku on your computer, deploying an app, declaring dependencies, and accessing a terminal for your deployed app.

In the `mwa-capstone` folder, there are a few files relevant to the Heroku configuration:
* `runtime.txt` ensures that the app will be run with Python 3.4.2 on Heroku
* `requirements.txt` declares all the Python packages that are necessary to run the application
* `Procfile` declares different process types that you can run (these will be explained in more detail later)

`Procfile` contains five named processes:
* `web`, which is automatically run when the application is deployed. We're using [gunicorn](http://gunicorn-docs.readthedocs.org/en/latest/index.html) as our Web server. The command in the web process is interesting because it's actually running two programs. The Heroku dyno will run the gunicorn command but the `&` will return control to the shell to allow more commands to be added. In this case, the second command being run is the `background.sh` script, which runs `run_background.py` in the `eorlive_prototype` folder. This Python file just runs a data-collection script every 4 hours that collects the data displayed in the table at the very bottom of the site's main page. The reason we run two commands in the web process is as follows. Basically, you can get 1 basic dyno on Heroku for free for 750 hrs/month, as explained [here](https://devcenter.heroku.com/articles/usage-and-billing#750-free-dyno-hours-per-app). Typically, you would run a background job in a different process in the `Procfile`, but this would spin up another dyno whose only job would be to run that task. Since we can only get one dyno for free, this allows us to run a background task and the website on the same dyno.
* `init`
* `migrate`
* `upgrade`
* `default_values`, which inserts a set of default values into the database that EoRLiv3 needs to run properly.

The middle three processes are just convenient ways of running the database management commands on the Heroku app that are explained [here](https://github.com/dhganey/mwa-capstone/wiki/Database-Maintenance). Alternatively, you could open up a terminal into the Heroku app as explained in the tutorial and run the database commands directly.

The last process, `default_values`, will be explained in the next section.

### First-Time Setup
We've provided an initial database migration script to get your database set up properly when you create your own Heroku app. After you've deployed the app to Heroku for the first time, run the `upgrade` process in the `Procfile`: `heroku run upgrade --app name-of-your-app`. This will create all the tables in the database for you.

**Important**: EoRLiv3 requires some initial values in the database to work properly. To ease this process, we've included a script that inserts these values for you. After running the `upgrade` above, just run `heroku run default_values --app name-of-your-app`. After you run this, the site is ready to use! 

**You only need to run the default_values process when you're setting up your app for the first time** (or whenever you wipe all the data in the database).

### Config Variables
We use config variables to provide usernames and passwords for the remote databases we access so we don't have to keep them in our repository. The tutorial mentioned above explains a way of providing these through code, but there's an easier way to do it through the Heroku dashboard. If you go to the app's dashboard on the Heroku website and go to the Settings page, there is a section titled 'Config Vars' where you can add config variables for your app.

The app requires four config variables to run:
* `MWA_DB_USERNAME`, the username used for MWA databases
* `MWA_DB_PW`, the password corresponding to the above username
* `NGAS_DB_USERNAME`, the username used for the NGAS databases
* `NGAS_DB_PW`, the password corresponding to the above username

### Uptime
As explained [here](https://blog.heroku.com/archives/2013/6/20/app_sleeping_on_heroku), when an app on Heroku has only one web dyno (which ours does), that dyno goes to sleep after an hour. The first request to the site after the dyno has gone to sleep will therefore be a bit slow. To prevent this, we used a service called [Uptime Robot](https://uptimerobot.com/) that will ping the site every 5 minutes so (a) the site doesn't go to sleep, and (b) you can be notified when the site goes down. We recommend you set up your own account for Uptime Robot (which is free) and configure it to ping your deployed site.