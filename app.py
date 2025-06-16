import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy

from scripts.criteriatable import CriteriaTable
from scripts.incrementstable import IncrementsTable
from scripts.table_handler import TableHandler

# -----------------------------------------------------------------------------
# App & DB setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secret-key"        # Change for production!
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///interviews.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class Interview(db.Model):
    __tablename__ = "interviews"
    id       = db.Column(db.String(8), primary_key=True)
    base_edu = db.Column(db.Integer, nullable=False)
    base_exp = db.Column(db.Integer, nullable=False)
    base_trn = db.Column(db.Integer, nullable=False)
    # participants & evaluator_tokens backrefs are injected automatically

class EvaluatorToken(db.Model):
    __tablename__ = "evaluator_tokens"
    token        = db.Column(db.String(8), primary_key=True)
    interview_id = db.Column(db.String(8), db.ForeignKey("interviews.id"), nullable=False)
    interview    = db.relationship("Interview", backref="evaluator_tokens")

class Participant(db.Model):
    __tablename__ = "participants"
    code          = db.Column(db.String(8), primary_key=True)
    interview_id  = db.Column(db.String(8), db.ForeignKey("interviews.id"), nullable=False)
    interview     = db.relationship("Interview", backref="participants")
    name          = db.Column(db.String(128), nullable=False)
    address       = db.Column(db.String(256), nullable=False)
    birthday      = db.Column(db.Date, nullable=False)
    age           = db.Column(db.Integer, nullable=False)
    sex           = db.Column(db.String(16), nullable=False)
    raw_edu       = db.Column(db.Integer, nullable=False)
    raw_exp       = db.Column(db.Integer, nullable=False)
    raw_trn       = db.Column(db.Integer, nullable=False)
    score_edu     = db.Column(db.Integer, nullable=False)
    score_exp     = db.Column(db.Integer, nullable=False)
    score_trn     = db.Column(db.Integer, nullable=False)

class Validation(db.Model):
    __tablename__ = "validations"
    id                = db.Column(db.Integer, primary_key=True)
    interview_id      = db.Column(db.String(8), db.ForeignKey("interviews.id"), nullable=False)
    evaluator_token   = db.Column(db.String(8), db.ForeignKey("evaluator_tokens.token"), nullable=False)
    participant_code  = db.Column(db.String(8), db.ForeignKey("participants.code"),  nullable=False)
    comment           = db.Column(db.Text, nullable=True)

# -----------------------------------------------------------------------------
# Authentication helper
# -----------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# -----------------------------------------------------------------------------
# Admin credentials (demo only)
# -----------------------------------------------------------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# -----------------------------------------------------------------------------
# Admin routes
# -----------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if (request.form["username"] == ADMIN_USER and
            request.form["password"] == ADMIN_PASS):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    th        = TableHandler()
    ed_labels = th.parse_table("table", "education")
    ex_labels = th.parse_table("table", "experience")
    tr_labels = th.parse_table("table", "training")

    interviews = Interview.query.all()
    evaluator_tokens = EvaluatorToken.query.all()  # Fetch all evaluator tokens

    return render_template(
        "admin_dashboard.html",
        interviews=interviews,
        evaluator_tokens=evaluator_tokens,
        ed_labels=ed_labels,
        ex_labels=ex_labels,
        tr_labels=tr_labels
    )


@app.route("/admin/create_interview", methods=["POST"])
@admin_required
def create_interview():
    iid = str(uuid.uuid4())[:8].upper()
    iv = Interview(
        id=iid,
        base_edu=int(request.form["baseline_education"]),
        base_exp=int(request.form["baseline_experience"]),
        base_trn=int(request.form["baseline_training"])
    )
    db.session.add(iv)
    db.session.commit()
    flash(f"Interview {iid} created", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/generate_evaluator_tokens", methods=["POST"])
@admin_required
def generate_evaluator_tokens():
    iid   = request.form["interview_id"]
    count = int(request.form["count_tokens"])
    new   = []
    for _ in range(count):
        tk = str(uuid.uuid4())[:8].upper()
        et = EvaluatorToken(token=tk, interview_id=iid)
        db.session.add(et)
        new.append(tk)
    db.session.commit()
    flash(f"Generated evaluator tokens: {', '.join(new)}", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/add_applicant", methods=["POST"])
@admin_required
def add_applicant():
    iid     = request.form["interview_id"]
    code    = str(uuid.uuid4())[:8].upper()
    name    = request.form["name"].strip()
    address = request.form["address"].strip()
    bstr    = request.form["birthday"].strip()  # format YYYY-MM-DD
    bd      = datetime.strptime(bstr, "%Y-%m-%d").date()
    age     = int(request.form["age"])
    sex     = request.form["sex"].strip()

    raw_edu = int(request.form["education"])
    raw_exp = int(request.form["experience"])
    raw_trn = int(request.form["training"])

    # compute transmuted scores
    crit = CriteriaTable()
    incs = IncrementsTable()
    delta_edu = crit.get_score(raw_edu, Interview.query.get(iid).base_edu)
    delta_exp = crit.get_score(raw_exp, Interview.query.get(iid).base_exp)
    delta_trn = crit.get_score(raw_trn, Interview.query.get(iid).base_trn)

    s_edu = incs.get_score(delta_edu, TableHandler().parse_table("increments","education"))
    s_exp = incs.get_score(delta_exp, TableHandler().parse_table("increments","experience"))
    s_trn = incs.get_score(delta_trn, TableHandler().parse_table("increments","training"))

    p = Participant(
        code=code,
        interview_id=iid,
        name=name,
        address=address,
        birthday=bd,
        age=age,
        sex=sex,
        raw_edu=raw_edu,
        raw_exp=raw_exp,
        raw_trn=raw_trn,
        score_edu=s_edu,
        score_exp=s_exp,
        score_trn=s_trn
    )
    db.session.add(p)
    db.session.commit()
    flash(f"Added participant {code}", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/interview/<iid>")
@admin_required
def admin_interview_detail(iid):
    iv = Interview.query.get_or_404(iid)
    participants = iv.participants  # list of Participant
    validations = Validation.query.filter_by(interview_id=iid).all()

    # group validations by participant_code
    val_map = {}
    for v in validations:
        val_map.setdefault(v.participant_code, []).append(v)

    return render_template(
        "admin_interview_detail.html",
        interview=iv,
        participants=participants,
        val_map=val_map
    )

# -----------------------------------------------------------------------------
# Evaluator routes
# -----------------------------------------------------------------------------
@app.route("/", methods=["GET","POST"])
def evaluator_login():
    if request.method == "POST":
        tk = request.form["token"].strip().upper()
        et = EvaluatorToken.query.get(tk)
        if not et:
            flash("Invalid evaluator token", "error")
        else:
            session["evaluator_token"] = tk
            session["interview_id"]    = et.interview_id
            return redirect(url_for("evaluator_dashboard"))
    return render_template("evaluator_login.html")

@app.route("/evaluator", methods=["GET","POST"])
def evaluator_dashboard():
    if "evaluator_token" not in session:
        return redirect(url_for("evaluator_login"))
    iid    = session["interview_id"]
    tk     = session["evaluator_token"]
    locked = Validation.query.filter_by(
        interview_id=iid,
        evaluator_token=tk
    ).first() is not None

    iv           = Interview.query.get(iid)
    participants = iv.participants

    if request.method == "POST" and not locked:
        for p in participants:
            comment = request.form.get(f"comment-{p.code}", "").strip()
            if comment:
                v = Validation(
                    interview_id=iid,
                    evaluator_token=tk,
                    participant_code=p.code,
                    comment=comment
                )
                db.session.add(v)
        db.session.commit()
        flash("Comments submitted (locked)", "success")
        return redirect(url_for("evaluator_dashboard"))

    return render_template(
        "evaluator.html",
        participants=participants,
        locked=locked
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("evaluator_login"))

# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
