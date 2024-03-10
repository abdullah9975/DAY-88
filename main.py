import os
from functools import wraps
from forms import RegisterForm, LoginForm
from flask import Flask, render_template, redirect, url_for, request, abort, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.fields.simple import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, URL
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required

app = Flask(__name__)
Bootstrap5(app)

'''SECRET_KEY=8BYkEfBA6O6donzWlSihBXox7C0sKR6b'''


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///cafes.db"
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


# Create the extension
db = SQLAlchemy(model_class=Base)
# Initialise the app with the extension
db.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    cafes = relationship("Cafe", back_populates="user")


# Cafe TABLE Configuration
class Cafe(db.Model):
    __tablename__ = "cafe"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="cafes")
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    map_url: Mapped[str] = mapped_column(String(500), nullable=False)
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    has_toilet: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_wifi: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_sockets: Mapped[bool] = mapped_column(Boolean, nullable=False)
    can_take_calls: Mapped[bool] = mapped_column(Boolean, nullable=False)
    seats: Mapped[str] = mapped_column(String(250), nullable=False)
    coffee_price: Mapped[str] = mapped_column(String(250), nullable=True)


class CafeForm(FlaskForm):
    name = StringField('Cafe name', validators=[DataRequired()])
    map_url = StringField('Cafe Location on Google Map(URL)', validators=[DataRequired(), URL()])
    img_url = StringField('Image URL', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    has_toilet = BooleanField('Washroom Availability')
    has_wifi = BooleanField('Wi-Fi Availability')
    has_sockets = BooleanField('Power Socket Availability')
    can_take_calls = BooleanField('Calling Availability')
    submit = SubmitField('Submit')


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# Create an admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


# Register new users into the User database
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # Check if user email is already present in the database.
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/")
def home():
    result = db.session.execute(db.select(Cafe))
    all_cafes = result.scalars().all()
    '''one line of code for the above code to fetch the data from database'''
    # all_cafes = Cafe.query.all()
    return render_template("index.html", cafes=all_cafes, current_user=current_user)


# @app.route('/cafes')
# def cafes():
#     result = db.session.execute(db.select(Cafe))
#     all_cafes = result.scalars().all()
#     '''one line of code for the above code to fetch the data from database'''
#     # all_cafes = Cafe.query.all()
#     return render_template('index.html', cafes=all_cafes)


@app.route('/add', methods=["GET", "POST"])
def add_cafe():
    form = CafeForm()
    if form.validate_on_submit():
        new_cafe = Cafe(
            name=form.name.data,
            map_url=form.map_url.data,
            img_url=form.img_url.data,
            location=form.location.data,
            has_toilet=form.has_toilet.data,  # Convert tick/cross symbols to boolean
            has_wifi=form.has_wifi.data,      # Convert tick/cross symbols to boolean
            has_sockets=form.has_sockets.data,  # Convert tick/cross symbols to boolean
            can_take_calls=form.can_take_calls.data,  # Convert tick/cross symbols to boolean
            user_id=current_user.id  # Assign the user_id
        )
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add.html', form=form)


# @app.route("/delete")
# def delete():
#     cafe_id = request.args.get("id")
#     cafe_to_delete = db.get_or_404(Cafe, cafe_id)
#     db.session.delete(cafe_to_delete)
#     db.session.commit()
#     return redirect(url_for('home'))

# @app.route("/delete/<int:cafe_id>", methods=["GET", "POST"])
# def delete(cafe_id):
#     cafe_to_delete = Cafe.query.get_or_404(cafe_id)
#
#     # Check if the cafe exists and if it belongs to the current user
#     if cafe_to_delete.user_id == current_user.id:
#         db.session.delete(cafe_to_delete)
#         db.session.commit()
#         flash("Cafe deleted successfully", "success")
#     else:
#         flash("Could not delete cafe", "danger")
#
#     return redirect(url_for('home'))


@app.route("/delete/<int:cafe_id>", methods=["GET", "POST"])
@login_required
def delete(cafe_id):
    cafe_to_delete = Cafe.query.get_or_404(cafe_id)

    # Check if the user is an admin or if the cafe belongs to the current user
    if current_user.is_admin or cafe_to_delete.user_id == current_user.id:
        db.session.delete(cafe_to_delete)
        db.session.commit()
        flash("Cafe deleted successfully", "success")
    else:
        flash("You are not authorized to delete this cafe", "danger")

    return redirect(url_for('home'))


@app.route("/cafe/<int:cafe_id>", methods=["GET", "POST"])
def show_cafe(cafe_id):
    requested_post = db.get_or_404(Cafe, cafe_id)
    return render_template("cafe.html", post=requested_post)


# search by location only by typing loc=location name whatever is the name of the location
# @app.route("/search", methods=["GET", "POST"])
# def search():
#     location = request.args.get("loc")
#     cafes = db.session.execute(db.select(Cafe).where(Cafe.location == location))
#     if cafes:
#         return render_template("searched.html", cafes=cafes)
#     else:
#         return render_template("searched.html", error="Sorry, we don't have a cafe at that location.")


# search by location by directly typing location name
# @app.route("/search", methods=["GET", "POST"])
# def search():
#     if request.method == "POST":
#         search_query = request.form.get("location")
#         cafes = Cafe.query.filter(Cafe.location.ilike(f"%{search_query}%")).all()
#         if cafes:
#             return render_template("searched.html", cafes=cafes)
#         else:
#             error = "Sorry, we don't have a cafe at that location."
#             return render_template("searched.html", error=error)
#     return render_template("searched.html")


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query")

    # Check if the query matches any existing cafe name
    cafes_by_name = Cafe.query.filter(Cafe.name.ilike(f"%{query}%")).all()
    if cafes_by_name:
        return render_template("searched.html", cafes=cafes_by_name)

    # Check if the query matches any existing cafe location
    cafes_by_location = Cafe.query.filter(Cafe.location.ilike(f"%{query}%")).all()
    if cafes_by_location:
        return render_template("searched.html", cafes=cafes_by_location)

    # If no matching cafes are found, display an error message
    error = "Sorry, we couldn't find any cafes matching your search query."
    return render_template("searched.html", error=error)


if __name__ == "__main__":
    app.run(debug=True)
