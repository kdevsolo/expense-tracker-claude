from flask import Flask, redirect, render_template, request, url_for

from database.db import create_user, get_user_by_email, init_db, seed_db

app = Flask(__name__)


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def is_valid_email(email):
    """Reject obviously malformed addresses.

    Deliberately permissive — real deliverability is not registration's job.
    Requires exactly one @, a non-empty local part, at least two non-empty
    domain labels, and no whitespace anywhere.
    """
    if email.count("@") != 1:
        return False
    local, _, domain = email.partition("@")
    if not local or not domain:
        return False
    if any(char.isspace() for char in email):
        return False
    labels = domain.split(".")
    return len(labels) >= 2 and all(labels)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not name or not email or not password:
            error = "All fields are required."
        elif not is_valid_email(email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif get_user_by_email(email) is not None:
            error = "An account with that email already exists."

        # The UNIQUE constraint is the real guard — a duplicate can still slip
        # past the check above between the lookup and the insert.
        if error is None and create_user(name, email, password) is None:
            error = "An account with that email already exists."

        if error is not None:
            return render_template(
                "register.html", error=error, name=name, email=email
            )

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    # Kept inside the main guard so importing this module (e.g. from tests)
    # never creates or seeds a database as a side effect.
    with app.app_context():
        init_db()
        seed_db()

    app.run(debug=True, port=5001)
