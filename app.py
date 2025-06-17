import uuid
import json
from datetime import datetime
from functools import wraps
from enum import Enum

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# These are assumed to be provided by your own code.
from scripts.criteriatable import CriteriaTable
from scripts.incrementstable import IncrementsTable
from scripts.table_handler import TableHandler

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secret-key"  # Change for production!
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///interviews.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------
class Interview(db.Model):
    __tablename__ = "interviews"
    id       = db.Column(db.String(8), primary_key=True)
    base_edu = db.Column(db.Integer, nullable=False)
    base_exp = db.Column(db.Integer, nullable=False)
    base_trn = db.Column(db.Integer, nullable=False)
    type     = db.Column(db.Enum("teaching", "promotion", "non-teaching", name="interview_type"),
                         nullable=False, default="non-teaching")
    # Relationships: evaluator_tokens and participants are auto-populated via backref.

class EvaluatorToken(db.Model):
    __tablename__ = "evaluator_tokens"
    token        = db.Column(db.String(8), primary_key=True)
    interview_id = db.Column(db.String(8), db.ForeignKey("interviews.id"), nullable=False)
    registered   = db.Column(db.Boolean, default=False, nullable=False)
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
    extra_data    = db.Column(db.Text, nullable=True)  # JSON-encoded extra teaching data

class Validation(db.Model):
    __tablename__ = "validations"
    id                = db.Column(db.Integer, primary_key=True)
    interview_id      = db.Column(db.String(8), db.ForeignKey("interviews.id"), nullable=False)
    evaluator_token   = db.Column(db.String(8), db.ForeignKey("evaluator_tokens.token"), nullable=False)
    participant_code  = db.Column(db.String(8), db.ForeignKey("participants.code"),  nullable=False)
    comment           = db.Column(db.Text, nullable=True)

# ------------------------------------------------------------------------------
# Authentication helper
# ------------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ------------------------------------------------------------------------------
# Admin credentials (demo only)
# ------------------------------------------------------------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# ------------------------------------------------------------------------------
# Admin Routes
# ------------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
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
    th = TableHandler()
    ed_labels = th.parse_table("table", "education")
    ex_labels = th.parse_table("table", "experience")
    tr_labels = th.parse_table("table", "training")
    interviews = Interview.query.all()
    return render_template("admin_dashboard.html",
                           interviews=interviews,
                           ed_labels=ed_labels,
                           ex_labels=ex_labels,
                           tr_labels=tr_labels)

@app.route("/admin/create_interview", methods=["GET", "POST"])
@admin_required
def create_interview():
    if request.method == "POST":
        iid = str(uuid.uuid4())[:8].upper()
        interview_type = request.form.get("interview_type", "non-teaching").lower()
        if interview_type not in ["teaching", "promotion", "non-teaching"]:
            interview_type = "non-teaching"
        iv = Interview(
            id=iid,
            base_edu=int(request.form["baseline_education"]),
            base_exp=int(request.form["baseline_experience"]),
            base_trn=int(request.form["baseline_training"]),
            type=interview_type
        )
        db.session.add(iv)
        db.session.commit()
        flash(f"Interview {iid} created", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("create_interview.html")

@app.route("/admin/interview/<iid>")
@admin_required
def admin_interview_detail(iid):
    iv = Interview.query.get_or_404(iid)
    applicants = iv.participants
    eval_tokens = iv.evaluator_tokens

    th = TableHandler()
    ed_labels = th.parse_table("table", "education")
    ex_labels = th.parse_table("table", "experience")
    tr_labels = th.parse_table("table", "training")

    validations = Validation.query.filter_by(interview_id=iid).all()
    val_map = {}
    for v in validations:
        val_map.setdefault(v.participant_code, []).append(v)

    return render_template("admin_interview_detail.html",
                           interview=iv,
                           applicants=applicants,
                           eval_tokens=eval_tokens,
                           ed_labels=ed_labels,
                           ex_labels=ex_labels,
                           tr_labels=tr_labels,
                           val_map=val_map)

@app.route("/admin/applicant/<code>")
@admin_required
def applicant_detail(code):
    applicant = Participant.query.get_or_404(code)
    extra_data = None
    if applicant.extra_data:
        try:
            extra_data = json.loads(applicant.extra_data)
        except Exception:
            extra_data = applicant.extra_data

    validations = Validation.query.filter_by(
        interview_id=applicant.interview_id,
        participant_code=applicant.code
    ).all()

    return render_template("applicant_detail.html",
                           applicant=applicant,
                           extra_data=extra_data,
                           validations=validations)

@app.route("/admin/evaluator/<token>")
@admin_required
def evaluator_detail(token):
    evaluator = EvaluatorToken.query.get_or_404(token)
    validations = Validation.query.filter_by(evaluator_token=token,
                                             interview_id=evaluator.interview_id).all()
    return render_template("evaluator_detail.html",
                           evaluator=evaluator,
                           validations=validations)

@app.route("/admin/add_applicant", methods=["POST"])
@admin_required
def add_applicant():
    iid = request.form["interview_id"]
    interview_obj = Interview.query.get(iid)
    if not interview_obj:
        flash("Interview not found", "error")
        return redirect(url_for("admin_dashboard"))
    code = request.form.get("applicant_code")
    if not code:
        code = str(uuid.uuid4())[:8].upper()
    else:
        code = code.strip().upper()

    name    = request.form["name"].strip()
    address = request.form["address"].strip()
    bstr    = request.form["birthday"].strip()  # format: YYYY-MM-DD
    bd      = datetime.strptime(bstr, "%Y-%m-%d").date()
    age     = int(request.form["age"])
    sex     = request.form["sex"].strip()

    raw_edu = int(request.form["education"])
    raw_exp = int(request.form["experience"])
    raw_trn = int(request.form["training"])

    # Compute base scores using CriteriaTable and IncrementsTable (assumed to return numeric scores)
    crit = CriteriaTable()
    incs = IncrementsTable()
    delta_edu = crit.get_score(raw_edu, interview_obj.base_edu)
    delta_exp = crit.get_score(raw_exp, interview_obj.base_exp)
    delta_trn = crit.get_score(raw_trn, interview_obj.base_trn)

    s_edu = incs.get_score(delta_edu, TableHandler().parse_table("increments", "education"))
    s_exp = incs.get_score(delta_exp, TableHandler().parse_table("increments", "experience"))
    s_trn = incs.get_score(delta_trn, TableHandler().parse_table("increments", "training"))

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

    # If the interview is of teaching type, then capture and compute teaching-related scores.
    if interview_obj.type == "teaching":
        teaching_qualification = request.form.get("teaching_qualification", "").strip()
        try:
            pbet_rating = float(request.form.get("pbet_rating", 0))
            classroom_obs = float(request.form.get("classroom_observation", 0))
            teacher_reflection_input = float(request.form.get("teacher_reflection", 0))
        except ValueError:
            flash("Teaching rating inputs must be numeric.", "error")
            return redirect(url_for("admin_interview_detail", iid=iid))

        # Convert teaching inputs using the specified formulas
        ppst_cois = (pbet_rating / 100.0) * 10       # out of 10 points
        ppst_ncois = (classroom_obs / 30.0) * 35       # out of 35 points
        teacher_reflection_score = (teacher_reflection_input / 20.0) * 25  # out of 25 points

        teaching_total = ppst_cois + ppst_ncois + teacher_reflection_score
        base_total = s_edu + s_exp + s_trn
        overall_total = base_total + teaching_total

        # Allow for a very small tolerance due to floating-point arithmetic.
        if abs(overall_total - 100) > 0.01:
            flash(f"Total points must equal 100. Calculated total is {overall_total:.2f}.", "error")
            return redirect(url_for("admin_interview_detail", iid=iid))

        extra = {
            "teaching_qualification": teaching_qualification,
            "pbet_rating": pbet_rating,
            "ppst_cois": ppst_cois,
            "classroom_observation": classroom_obs,
            "ppst_ncois": ppst_ncois,
            "teacher_reflection": teacher_reflection_input,
            "teacher_reflection_score": teacher_reflection_score
        }
        p.extra_data = json.dumps(extra)

    db.session.add(p)
    db.session.commit()
    flash(f"Added applicant {code}", "success")
    return redirect(url_for("admin_interview_detail", iid=iid))

@app.route("/admin/generate_evaluator_tokens", methods=["POST"])
@admin_required
def generate_evaluator_tokens():
    iid = request.form["interview_id"]
    count = int(request.form["count_tokens"])
    new = []
    for _ in range(count):
        tk = str(uuid.uuid4())[:8].upper()
        et = EvaluatorToken(token=tk, interview_id=iid)
        db.session.add(et)
        new.append(tk)
    db.session.commit()
    flash(f"Generated evaluator tokens: {', '.join(new)}", "success")
    return redirect(url_for("admin_interview_detail", iid=iid))

# ------------------------------------------------------------------------------
# Evaluator Routes
# ------------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def evaluator_login():
    if request.method == "POST":
        tk = request.form["token"].strip().upper()
        if not tk:
            flash("Token is required.", "error")
            return render_template("evaluator_login.html")
        et = EvaluatorToken.query.get(tk)
        if not et:
            flash("Invalid evaluator token", "error")
            return render_template("evaluator_login.html")
        if not et.registered:
            et.registered = True
            db.session.commit()
        session["evaluator_token"] = tk
        session["interview_id"] = et.interview_id
        return redirect(url_for("evaluator_dashboard"))
    return render_template("evaluator_login.html")

@app.route("/evaluator", methods=["GET"])
def evaluator_dashboard():
    if "evaluator_token" not in session:
        return redirect(url_for("evaluator_login"))
    iid = session["interview_id"]
    iv = Interview.query.get(iid)
    applicants = iv.participants
    return render_template("evaluator_dashboard.html",
                           applicants=applicants,
                           interview=iv)

@app.route("/evaluator/applicant/<code>", methods=["GET", "POST"])
def evaluator_applicant_detail(code):
    if "evaluator_token" not in session:
        return redirect(url_for("evaluator_login"))
    iid = session["interview_id"]
    tk = session["evaluator_token"]
    applicant = Participant.query.get_or_404(code)
    if applicant.interview_id != iid:
        flash("Invalid applicant for this interview.", "error")
        return redirect(url_for("evaluator_dashboard"))
    validation = Validation.query.filter_by(
        interview_id=iid,
        evaluator_token=tk,
        participant_code=code
    ).first()
    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        if not comment:
            flash("Comment cannot be empty.", "error")
        else:
            if validation:
                validation.comment = comment
                flash("Your comment has been updated.", "success")
            else:
                validation = Validation(
                    interview_id=iid,
                    evaluator_token=tk,
                    participant_code=code,
                    comment=comment
                )
                db.session.add(validation)
                flash("Your comment has been submitted.", "success")
            db.session.commit()
        return redirect(url_for("evaluator_applicant_detail", code=code))
    return render_template("evaluator_applicant_detail.html",
                           applicant=applicant,
                           validation=validation)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("evaluator_login"))

# ------------------------------------------------------------------------------
# Run the Application
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
