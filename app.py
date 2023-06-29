import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

if os.path.exists("env.py"):
    import env

app = Flask(__name__)


app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/get_journals")
def get_journals():
    try:
        journals = mongo.db.journals.find()
        return render_template("journals.html", journals=journals)
    except Exception as e:
        return f"Error connecting to MongoDB: {str(e)}"


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username exists in the db
        username = request.form.get("username", "")
        if not username:
            flash("Please provide a username")
            return redirect(url_for("register"))

        existing_user = mongo.db.users.find_one({"username": username.lower()})
        if existing_user:
            flash("Oops, that username is not available")
            return redirect(url_for("register"))

        register = {
            "username": username.lower(),
            "password": generate_password_hash(request.form.get("password")),
            "email": request.form.get("email")
        }

        mongo.db.users.insert_one(register)

        # creates cookie session for new user
        session["user"] = username.lower()
        flash("Welcome to LifeWrite!")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check if username exists in the database
        existing_user = mongo.db.users.find_one({"username": request.form.get("username").lower()})  # noqa

        if existing_user:
            # Ensure hashed password matches user input
            if check_password_hash(existing_user["password"], request.form.get("password")):  # noqa
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(request.form.get("username")))
                return redirect(url_for("profile", username=session["user"]))

        # Invalid username or password
        flash("Incorrect Username and/or Password")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    # Retrieve the user's username from the session
    username = session.get("username")

    if not username:
        flash("Please log in to access your profile")
        return redirect(url_for("login"))

    # Retrieve the user's information from the database based on the session username  # noqa
    user = mongo.db.users.find_one({"username": username})

    if not user:
        flash("User not found")
        return redirect(url_for("login"))

    return render_template("profile.html", username=user["username"])


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
