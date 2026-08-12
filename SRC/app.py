import os
import re
import secrets
from datetime import datetime
from functools import wraps

import pymysql
from dotenv import load_dotenv
from flask import Flask, abort, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
    DB_HOST=os.getenv("DB_HOST", "localhost"),
    DB_PORT=int(os.getenv("DB_PORT", "3306")),
    DB_USER=os.getenv("DB_USER", "raintrack"),
    DB_PASSWORD=os.getenv("DB_PASSWORD", ""),
    DB_NAME=os.getenv("DB_NAME", "rainTrack"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
)

CPF_RE = re.compile(r"^\d{11}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
UUID_RE = re.compile(r"^[A-F0-9]{12}$")


def get_db_connection():
    connector = app.config.get("DB_CONNECTOR", pymysql.connect)
    return connector(
        host=app.config["DB_HOST"], port=app.config["DB_PORT"],
        user=app.config["DB_USER"], password=app.config["DB_PASSWORD"],
        db=app.config["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
        autocommit=False, charset="utf8mb4",
    )


def nocache(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers.update({
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache", "Expires": "0",
        })
        return response
    return wrapped


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))
        if session.get("user_role") != 1 or session.get("is_guest"):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.before_request
def protect_csrf():
    if request.method == "POST":
        expected = session.get("csrf_token")
        supplied = request.form.get("csrf_token")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            abort(400, "Token CSRF inválido ou ausente.")


@app.context_processor
def inject_context():
    return {
        "csrf_token": csrf_token,
        "user_name": session.get("user_name"),
        "user_role": session.get("user_role"),
        "is_guest": session.get("is_guest", False),
    }


def normalize_uuid(value):
    return re.sub(r"[^A-Fa-f0-9]", "", value or "").upper()


def validate_user(name, email, cpf, role, password=None):
    if not all((name, email, cpf)) or role not in {"0", "1"}:
        return "Preencha os campos obrigatórios com valores válidos."
    if not EMAIL_RE.fullmatch(email):
        return "Informe um e-mail válido."
    if not CPF_RE.fullmatch(cpf):
        return "O CPF deve conter exatamente 11 números."
    if password is not None and len(password) < 8:
        return "A senha deve ter pelo menos 8 caracteres."
    return None


def validate_station(name, latitude, longitude, uuid, selected_parameters):
    if not name or not uuid or not selected_parameters:
        return None, "Preencha os campos e selecione pelo menos um parâmetro."
    try:
        latitude, longitude = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None, "Latitude e longitude devem ser números."
    clean_uuid = normalize_uuid(uuid)
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return None, "Latitude deve estar entre -90 e 90 e longitude entre -180 e 180."
    if not UUID_RE.fullmatch(clean_uuid):
        return None, "O UUID deve ser o MAC do ESP32 com 12 dígitos hexadecimais."
    return (name.strip(), latitude, longitude, clean_uuid), None


def verify_password(stored, supplied):
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, supplied), False
    return secrets.compare_digest(stored, supplied), True


@app.route("/", methods=["GET", "POST"])
@nocache
def index():
    if request.method == "GET":
        return render_template("index.html")
    entry, password = request.form.get("entry", "").strip(), request.form.get("password", "")
    if not entry or not password:
        return render_template("index.html", error="Preencha todos os campos."), 400
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, password, email, name, role, cpf FROM users WHERE email=%s OR cpf=%s", (entry, entry))
            user = cursor.fetchone()
            if not user:
                return render_template("index.html", error="Usuário não encontrado."), 401
            valid, legacy = verify_password(user["password"], password)
            if not valid:
                return render_template("index.html", error="Senha incorreta."), 401
            if legacy:
                cursor.execute("UPDATE users SET password=%s WHERE id=%s", (generate_password_hash(password), user["id"]))
                connection.commit()
        session.clear()
        session.update(user_name=user["name"].split()[0], user_role=int(user["role"]), user_id=user["id"], is_guest=False)
        return redirect(url_for("home"))
    finally:
        connection.close()


@app.route("/guest")
def guest():
    session.clear()
    session.update(user_name="Convidado", user_role=0, user_id="guest", is_guest=True)
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/home")
@nocache
@login_required
def home():
    return render_template("home.html")


@app.route("/admin", methods=["GET", "POST"])
@nocache
@admin_required
def admin():
    if request.method == "GET":
        return render_template("admin.html")
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    cpf = re.sub(r"\D", "", request.form.get("cpf", ""))
    password, role = request.form.get("password", ""), request.form.get("role", "")
    error = validate_user(name, email, cpf, role, password)
    if error:
        return render_template("admin.html", error=error), 400
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (name,email,cpf,password,role) VALUES (%s,%s,%s,%s,%s)",
                           (name, email, cpf, generate_password_hash(password), int(role)))
        connection.commit()
        return render_template("admin.html", success="Usuário cadastrado com sucesso!")
    except pymysql.err.IntegrityError:
        connection.rollback()
        return render_template("admin.html", error="E-mail ou CPF já cadastrado."), 409
    finally:
        connection.close()


@app.route("/stations")
@nocache
@admin_required
def stations():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,name,latitude,longitude,uuid FROM stations ORDER BY createdAt DESC")
            rows = cursor.fetchall()
        return render_template("stations.html", stations=rows)
    finally:
        connection.close()


def parameter_types(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id,name,unit FROM typeParameters ORDER BY name")
        return cursor.fetchall()


@app.route("/add_station", methods=["GET", "POST"])
@nocache
@admin_required
def add_station():
    connection = get_db_connection()
    try:
        available = parameter_types(connection)
        if request.method == "GET":
            return render_template("add_station.html", parameters=available)
        selected = request.form.getlist("cdParameter")
        values, error = validate_station(request.form.get("name"), request.form.get("latitude"),
                                         request.form.get("longitude"), request.form.get("uuid"), selected)
        if error:
            return render_template("add_station.html", error=error, parameters=available), 400
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO stations (name,latitude,longitude,uuid) VALUES (%s,%s,%s,%s)", values)
            station_id = cursor.lastrowid
            for parameter_id in selected:
                cursor.execute("INSERT INTO parameters (cdStation,cdTypeParameter) VALUES (%s,%s)", (station_id, parameter_id))
        connection.commit()
        return redirect(url_for("stations"))
    except pymysql.err.IntegrityError:
        connection.rollback()
        return render_template("add_station.html", error="UUID duplicado ou parâmetro inválido.", parameters=available), 409
    finally:
        connection.close()


@app.route("/parameters")
@nocache
@admin_required
def parameters():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM typeParameters ORDER BY name")
            rows = cursor.fetchall()
        return render_template("parameters.html", parameters=rows)
    finally:
        connection.close()


def validate_parameter(name, unit, type_json, decimal_places):
    if not all((name, unit, type_json)) or type_json not in {"number", "boolean", "temperature", "humidity"}:
        return None, "Preencha os campos com valores válidos."
    try:
        decimal_places = int(decimal_places)
    except (TypeError, ValueError):
        return None, "Casas decimais deve ser um número."
    if not 0 <= decimal_places <= 10:
        return None, "Casas decimais deve estar entre 0 e 10."
    return (name.strip(), unit.strip(), type_json, decimal_places), None


@app.route("/add_parameter", methods=["GET", "POST"])
@nocache
@admin_required
def add_parameter():
    if request.method == "GET":
        return render_template("add_parameter.html")
    values, error = validate_parameter(request.form.get("name"), request.form.get("unit"),
                                       request.form.get("typeJson"), request.form.get("decimalPlaces"))
    if error:
        return render_template("add_parameter.html", error=error), 400
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO typeParameters (name,unit,typeJson,numberOfDecimalPlaces) VALUES (%s,%s,%s,%s)", values)
        connection.commit()
        return redirect(url_for("parameters"))
    except pymysql.err.IntegrityError:
        connection.rollback()
        return render_template("add_parameter.html", error="Nome de parâmetro já cadastrado."), 409
    finally:
        connection.close()


@app.route("/users")
@nocache
@admin_required
def users():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,name,cpf,email,role,createdAt FROM users ORDER BY id")
            rows = cursor.fetchall()
        return render_template("users.html", users=rows)
    finally:
        connection.close()


@app.route("/graphs")
@nocache
@login_required
def graphs():
    start_date, end_date = request.args.get("start_date"), request.args.get("end_date")
    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
        if start_date and end_date and start_date > end_date:
            raise ValueError
    except ValueError:
        abort(400, "Período de datas inválido.")
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,name,uuid FROM stations ORDER BY createdAt DESC")
            station_rows = cursor.fetchall()
            for station in station_rows:
                query = """SELECT tp.name,tp.unit,m.value,m.measureTime FROM parameters p
                           JOIN typeParameters tp ON p.cdTypeParameter=tp.id
                           JOIN measures m ON m.cdParameter=p.id WHERE p.cdStation=%s"""
                params = [station["id"]]
                if start_date:
                    query += " AND m.measureTime >= %s"; params.append(f"{start_date} 00:00:00")
                if end_date:
                    query += " AND m.measureTime <= %s"; params.append(f"{end_date} 23:59:59")
                cursor.execute(query + " ORDER BY m.measureTime", tuple(params))
                measures = cursor.fetchall()
                categories = sorted({m["measureTime"].strftime("%Y-%m-%d %H:%M") for m in measures})
                positions = {category: index for index, category in enumerate(categories)}
                grouped = {}
                for measure in measures:
                    key = f'{measure["name"]} ({measure["unit"]})'
                    grouped.setdefault(key, [None] * len(categories))
                    grouped[key][positions[measure["measureTime"].strftime("%Y-%m-%d %H:%M")]] = float(measure["value"])
                station["categories"] = categories
                station["series"] = [{"name": name, "data": data} for name, data in grouped.items()]
        return render_template("graphs.html", stations=station_rows, start_date=start_date, end_date=end_date)
    finally:
        connection.close()


@app.post("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        abort(400, "Você não pode excluir sua própria conta.")
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        connection.commit()
        return redirect(url_for("users"))
    finally:
        connection.close()


@app.route("/edit_parameter/<int:parameter_id>", methods=["GET", "POST"])
@nocache
@admin_required
def edit_parameter(parameter_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM typeParameters WHERE id=%s", (parameter_id,))
            parameter = cursor.fetchone()
            if not parameter:
                abort(404)
            if request.method == "POST":
                values, error = validate_parameter(request.form.get("name"), request.form.get("unit"),
                                                   request.form.get("typeJson"), request.form.get("decimalPlaces"))
                if error:
                    return render_template("edit_parameter.html", parameter=parameter, error=error), 400
                cursor.execute("UPDATE typeParameters SET name=%s,unit=%s,typeJson=%s,numberOfDecimalPlaces=%s WHERE id=%s",
                               (*values, parameter_id))
                connection.commit()
                return redirect(url_for("parameters"))
        return render_template("edit_parameter.html", parameter=parameter)
    except pymysql.err.IntegrityError:
        connection.rollback()
        return render_template("edit_parameter.html", parameter=parameter, error="Nome já cadastrado."), 409
    finally:
        connection.close()


@app.route("/edit_station/<int:station_id>", methods=["GET", "POST"])
@nocache
@admin_required
def edit_station(station_id):
    connection = get_db_connection()
    try:
        available = parameter_types(connection)
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM stations WHERE id=%s", (station_id,))
            station = cursor.fetchone()
            if not station:
                abort(404)
            cursor.execute("SELECT id,cdTypeParameter FROM parameters WHERE cdStation=%s", (station_id,))
            links = cursor.fetchall()
            current = {str(row["cdTypeParameter"]): row["id"] for row in links}
            if request.method == "POST":
                selected_list = request.form.getlist("cdParameter")
                values, error = validate_station(request.form.get("name"), request.form.get("latitude"),
                                                 request.form.get("longitude"), request.form.get("uuid"), selected_list)
                if error:
                    return render_template("edit_station.html", station=station, parameters=available,
                                           current_parameters=list(current), error=error), 400
                selected = set(selected_list)
                cursor.execute("UPDATE stations SET name=%s,latitude=%s,longitude=%s,uuid=%s WHERE id=%s", (*values, station_id))
                for type_id in selected - set(current):
                    cursor.execute("INSERT INTO parameters (cdStation,cdTypeParameter) VALUES (%s,%s)", (station_id, type_id))
                for type_id in set(current) - selected:
                    cursor.execute("SELECT 1 FROM measures WHERE cdParameter=%s LIMIT 1", (current[type_id],))
                    if cursor.fetchone():
                        connection.rollback()
                        return render_template("edit_station.html", station=station, parameters=available,
                                               current_parameters=list(current),
                                               error="Não é possível remover um parâmetro que possui medições."), 409
                    cursor.execute("DELETE FROM parameters WHERE id=%s", (current[type_id],))
                connection.commit()
                return redirect(url_for("stations"))
        return render_template("edit_station.html", station=station, parameters=available, current_parameters=list(current))
    except pymysql.err.IntegrityError:
        connection.rollback()
        return render_template("edit_station.html", station=station, parameters=available,
                               current_parameters=list(current), error="UUID duplicado ou parâmetro inválido."), 409
    finally:
        connection.close()


@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
@nocache
@admin_required
def edit_user(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,name,email,cpf,role FROM users WHERE id=%s", (user_id,))
            user = cursor.fetchone()
            if not user:
                abort(404)
            if request.method == "POST":
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").strip().lower()
                cpf = re.sub(r"\D", "", request.form.get("cpf", ""))
                role, password = request.form.get("role", ""), request.form.get("password", "")
                error = validate_user(name, email, cpf, role, password if password else None)
                if error:
                    return render_template("edit_user.html", user=user, error=error), 400
                if password:
                    cursor.execute("UPDATE users SET name=%s,email=%s,cpf=%s,password=%s,role=%s WHERE id=%s",
                                   (name, email, cpf, generate_password_hash(password), int(role), user_id))
                else:
                    cursor.execute("UPDATE users SET name=%s,email=%s,cpf=%s,role=%s WHERE id=%s",
                                   (name, email, cpf, int(role), user_id))
                connection.commit()
                return redirect(url_for("users"))
        return render_template("edit_user.html", user=user)
    except pymysql.err.IntegrityError:
        connection.rollback()
        return render_template("edit_user.html", user=user, error="E-mail ou CPF já cadastrado."), 409
    finally:
        connection.close()


@app.route("/editUser/<int:idUser>")
@admin_required
def editUser(idUser):
    return redirect(url_for("edit_user", user_id=idUser))


@app.route("/about")
@nocache
def about():
    return render_template("about.html")


@app.route("/user_profile")
@nocache
@login_required
def user_profile():
    if session.get("is_guest"):
        return redirect(url_for("home"))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,name,email,cpf,role,createdAt FROM users WHERE id=%s", (session["user_id"],))
            user = cursor.fetchone()
        if not user:
            session.clear()
            return redirect(url_for("index"))
        return render_template("user_profile.html", user=user)
    finally:
        connection.close()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
