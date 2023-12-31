import os
from functools import wraps
from flask import (
    Flask, flash, render_template, redirect, request, session, url_for
)
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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@app.route("/home")
def home():
    welcome_message = (
        "Welcome to MemoraLog, your personal journaling companion!")
    return render_template("home.html", welcome_message=welcome_message)


@app.route("/get_journals")
def get_journals():
    try:
        if 'user' in session:
            current_user_id = session.get("user")
            journals = mongo.db.journals.find({"user_id": current_user_id})
            return render_template("journals.html", journals=journals)
        else:
            flash("Please log in to access your journals.", "warning")
            return redirect(url_for("login"))
    except Exception as e:
        return f"Error connecting to MongoDB: {str(e)}"


@app.route("/journal/<journal_id>")
@login_required
def view_journal(journal_id):
    try:
        # Retrieve the journal from the database using the journal_id
        journal = mongo.db.journals.find_one({"_id": ObjectId(journal_id)})
        if journal:
            # Render the journal modal template with the journal data
            return render_template("journal_modal.html", journal=journal)
        else:
            return "Journal not found"
    except Exception as e:
        return f"Error retrieving journal: {str(e)}"


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
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "email": request.form.get("email"),
        }

        mongo.db.users.insert_one(register)

        # creates cookie session for new user
        session["user"] = request.form.get("username").lower()
        flash("Welcome to MemoraLog!")
        return redirect(url_for("get_journals"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check if username exists in the database
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()}
        )

        if existing_user:
            # Ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get("password")
            ):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(request.form.get("username")))
                return redirect(
                    url_for("get_journals", username=session["user"]))
            else:
                # Invalid username or password
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # Redirects the user to the journals page
    if "user" in session:
        return redirect(url_for("get_journals"))
    # Retrieve the user's information from the database based
    #  on the provided username
    user = mongo.db.users.find_one({"username": username})

    if not user:
        flash("User not found")
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out. See you soon!")
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/new_journal", methods=["GET", "POST"])
@login_required
def new_journal():
    # creates a new journal on the database
    if request.method == "POST":
        journal = {
            "journal_name": request.form.get("journal_name"),
            "journal_entry": request.form.get("journal_entry"),
            "user_id": session["user"],
        }
        mongo.db.journals.insert_one(journal)
        flash("Yay! You created a new journal")
        return redirect(url_for("get_journals"))

    return render_template("new_journal.html")


@app.route("/edit_journal/<journal_id>", methods=["GET", "POST"])
@login_required
def edit_journal(journal_id):
    # updates the journal on the database
    journal = mongo.db.journals.find_one({"_id": ObjectId(journal_id)})
    if journal['user_id'] != session['user']:
        flash('You do not have permission to edit this journal.', 'danger')
        return redirect(url_for('get_journals'))

    if request.method == "POST":
        submit = {
            "journal_name": request.form.get("journal_name"),
            "journal_entry": request.form.get("journal_entry"),
        }
        mongo.db.journals.update_one(
            {"_id": ObjectId(journal_id)}, {"$set": submit})
        flash("You just updated a journal")
        return redirect(url_for("get_journals"))

    return render_template("edit_journal.html", journal=journal)


@app.route("/delete_journal/<journal_id>", methods=["POST"])
@login_required
def delete_journal(journal_id):
    # Removes the journal on the database
    journal = mongo.db.journals.find_one({"_id": ObjectId(journal_id)})
    if journal['user_id'] != session['user']:
        flash('You do not have permission to delete this journal.', 'danger')
        return redirect(url_for('get_journals'))

    mongo.db.journals.delete_one({"_id": ObjectId(journal_id)})
    flash("You just deleted a journal")
    return redirect(url_for("get_journals"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")), debug=False)
