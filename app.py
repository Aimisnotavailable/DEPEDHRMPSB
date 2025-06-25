import uuid
import json
from datetime import datetime
from functools import wraps
from enum import Enum

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

from scripts.criteriatable import CriteriaTable
from scripts.incrementstable import IncrementsTable
from scripts.table_handler import TableHandler

from download import download_pdf


app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secret-key"  # Change for production!
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///interviews.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

EVAL_STRUCTURE = {
    "non-teaching" : {"Behavior Interview" : {
                    "aptitude" : 1,
                    "characteristics" : 1,
                    "fitness" : 1,
                    "leadership" : 1,
                    "communication" : 1
                },
                },
    "teaching" : {"Behavior Interview" : {
                        "aptitude" : 1,
                        "characteristics" : 1,
                        "fitness" : 1,
                        "leadership" : 1,
                        "communication" : 1
                    },
                    },
    "school administration" : {"Behavior Interview" : {
                    "aptitude" : 1,
                    "characteristics" : 1,
                    "fitness" : 1,
                    "leadership" : 1,
                    "communication" : 1
                },
                },
    "related teaching" : {"Behavior Interview" : {
                        "aptitude" : 1,
                        "characteristics" : 1,
                        "fitness" : 1,
                        "leadership" : 1,
                        "communication" : 1
                    },
                    },

    "promotion" : {
                    "Written Examination" : {
                        "focus and detail" : 2,
                        "organization" : 2,
                        "content" : 2,
                        "word choice" : 2,
                        "sentence, structure, grammar mechanics, and spelling" : 2,
                        "work sample test" : 5
                    },
                    "Behavior Interview" : {
                        "aptitude" : 1,
                        "characteristics" : 1,
                        "fitness" : 1,
                        "leadership" : 1,
                        "communication" : 1
                    },
                    },
}

WEIGHT_STRUCTURE = {
    "teaching" : {
        "education" : 10,
        "experience" : 10,
        "training" : 10,
    },
    "non-teaching" : {
        "education" : 10,
        "experience" : 10,
        "training" : 10,
    }
}

APPLICANT_STRUCTURE = {
    "teaching" : {
        "lpt_rating" : {"WEIGHT" : 10, "MAX_SCORE" : 100, "LABEL" : "LPT/PBET/LEPT Rating"},
        "cot" : {"WEIGHT" : 35, "MAX_SCORE" : 30, "LABEL" : "COT"},
        "trf_rating" : {"WEIGHT" : 20, "MAX_SCORE" : 20, "LABEL" : "TRF"}
    }
}

# ------------------------------------------------------------------------------
# MODELS
# ------------------------------------------------------------------------------

class Interview(db.Model):
    __tablename__ = "interviews"
    id       = db.Column(db.String(8), primary_key=True)
    base_edu = db.Column(db.Integer, nullable=False)
    base_exp = db.Column(db.Integer, nullable=False)
    base_trn = db.Column(db.Integer, nullable=False)
    type     = db.Column(db.Enum("non teaching", "teaching", "school administration", "related teaching", "promotion", name="interview_type"),
                         nullable=False, default="non-teaching")
    sg_level = db.Column(db.String(100))
    # Relationships via backref: evaluator_tokens, participants

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
    extra_data    = db.Column(db.Text, nullable=True)
    # extra_data for teaching interviews stores:
    #   { "lpt_rating": <raw>, "COI": <computed> }

class Evaluation(db.Model):
    __tablename__ = "evaluations"
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.String(8), db.ForeignKey("interviews.id"), nullable=False)
    evaluator_token = db.Column(db.String(8), db.ForeignKey("evaluator_tokens.token"), nullable=False)
    participant_code = db.Column(db.String(8), db.ForeignKey("participants.code"), nullable=False)
    extra_data = db.Column(db.Text, nullable=True)

    # This relationship allows the evaluation to access the associated Interview
    # with which it is linked via interview_id.
    interview = db.relationship("Interview", backref="evaluations")

# ------------------------------------------------------------------------------
# AUTHENTICATION HELPER
# ------------------------------------------------------------------------------

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ------------------------------------------------------------------------------
# ADMIN CREDENTIALS (demo only)
# ------------------------------------------------------------------------------

ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# ------------------------------------------------------------------------------
# ADMIN ROUTES
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
        interview_type = request.form.get("interview_type", "non teaching").lower()
        sg_level = request.form.get("sg_level")
        print("HEHE", interview_type)
        iv = Interview(
            id=iid,
            base_edu=int(request.form["baseline_education"]),
            base_exp=int(request.form["baseline_experience"]),
            base_trn=int(request.form["baseline_training"]),
            type=interview_type,
            sg_level=sg_level
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

    applicant_structure = APPLICANT_STRUCTURE[iv.type]

    return render_template("admin_interview_detail.html",
                           interview=iv,
                           applicants=applicants,
                           applicant_structure=applicant_structure,
                           eval_tokens=eval_tokens,
                           ed_labels=ed_labels,
                           ex_labels=ex_labels,
                           tr_labels=tr_labels)

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

    eval_records = Evaluation.query.filter_by(
         interview_id=applicant.interview_id,
         participant_code=applicant.code
    ).all()

    # For teaching interviews, compute NCOI as:
    #   NCOI = Admin's TRF (max 20) + Average of evaluators' five criteria scores (max 5)
    eval_type = Interview.query.filter_by(id=applicant.interview_id).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]

    avg_eval = None
    scores = []
    applicant_structure = APPLICANT_STRUCTURE[applicant.interview.type]
    evaluation_scores = {}
    total_score = applicant.score_edu + applicant.score_exp + applicant.score_trn

    app_json = json.loads(applicant.extra_data)
    for field in app_json.keys():
        total_score += app_json[field]

    if eval_records:
        for key in eval_struct.keys():
            total = 0
            for eval_record in eval_records:
                temp_json = json.loads(eval_record.extra_data)
                for val in temp_json[key].values():
                    total += val
            avg_eval = round(total / len(eval_records), 2)
            evaluation_scores[key] = avg_eval
            total_score += avg_eval

    for eval_record in eval_records:
        overall = 0
        extra_data_json = json.loads(eval_record.extra_data)
        for key in eval_struct.keys():
            for field in eval_struct[key].keys():
                overall = round(overall + extra_data_json[key][field], 2)
            scores.append(overall)



    return render_template("applicant_detail.html",
                           applicant=applicant,
                           applicant_structure=applicant_structure,
                           extra_data=extra_data,
                           evaluation_scores=evaluation_scores,
                           total_score=total_score,
                           scores=scores,
                           avg_eval=avg_eval)

@app.route("/admin/applicant/<code>/download")
@admin_required
def download_applicant_pdf(code):
    
    doc_io = download_pdf(code, Participant(), Evaluation(), Interview(), EVAL_STRUCTURE=EVAL_STRUCTURE)
    print(doc_io)

    return send_file(
        doc_io,
        as_attachment=True,
        download_name=f'APPLICANT {code}_DETAILS.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route("/admin/evaluator/<token>")
@admin_required
def evaluator_detail(token):
    evaluator = EvaluatorToken.query.get_or_404(token)
    # Get all evaluations made by this evaluator.
    eval_records = Evaluation.query.filter_by(
         interview_id=evaluator.interview_id,
         evaluator_token=token
    ).all()
    
    eval_type = Interview.query.filter_by(id=evaluator.interview_id).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]
    scores = []
    for eval_record in eval_records:
        overall = 0
        extra_data_json = json.loads(eval_record.extra_data)
        for key in eval_struct.keys():
            for field in eval_struct[key].keys():
                overall = round(overall + extra_data_json[key][field], 2)
            scores.append(overall)

    return render_template("evaluator_detail.html",
                           evaluator=evaluator,
                           eval_records=eval_records,
                           scores=scores)

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
    
    weight_stucture = WEIGHT_STRUCTURE[interview_obj.type]
    name    = request.form["name"].strip()
    address = request.form["address"].strip()
    bstr    = request.form["birthday"].strip()  # Expected format: YYYY-MM-DD
    bd      = datetime.strptime(bstr, "%Y-%m-%d").date()
    age     = int(request.form["age"])
    sex     = request.form["sex"].strip()

    raw_edu = int(request.form["education"])
    raw_exp = int(request.form["experience"])
    raw_trn = int(request.form["training"])

    # Compute base scores using CriteriaTable and IncrementsTable
    crit = CriteriaTable()
    incs = IncrementsTable()

    delta_edu = crit.get_score(raw_edu, interview_obj.base_edu)
    delta_exp = crit.get_score(raw_exp, interview_obj.base_exp)
    delta_trn = crit.get_score(raw_trn, interview_obj.base_trn)


    inc_edu = (weight_stucture['education'] // 5)
    inc_exp = (weight_stucture['experience'] // 5)
    inc_trn = (weight_stucture['training'] // 5)
    s_edu = (incs.get_score(delta_edu, TableHandler().parse_table("increments", "education")) // inc_edu) * inc_edu
    s_exp = (incs.get_score(delta_exp, TableHandler().parse_table("increments", "experience")) // inc_exp) * inc_exp
    s_trn = (incs.get_score(delta_trn, TableHandler().parse_table("increments", "training")) // inc_trn) * inc_trn

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

    # For teaching interviews, the admin now inputs the TRF rating (max 20)
    applicant_structure = APPLICANT_STRUCTURE[interview_obj.type]
    
    calculated_score = {}
    try:
        for field in applicant_structure.keys():
            calculated_score[field] = round((float(request.form.get(field, 0)) /  applicant_structure[field]['MAX_SCORE']) * applicant_structure[field]['WEIGHT'], 2)
    except ValueError:  
        flash("TRF rating must be numeric.", "error")
        return redirect(url_for("admin_interview_detail", iid=iid))
    # Store the TRF in extra_data as JSON
    p.extra_data = json.dumps(calculated_score)

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
# EVALUATOR ROUTES
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
    tk = session["evaluator_token"]
    iv = Interview.query.get(iid)
    applicants = iv.participants

    # print(evaluation.interview.type)
    eval_type = Interview.query.filter_by(id=iid).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]
    # For each applicant, get only the evaluation record for the current evaluator.
    my_scores = {}
    for a in applicants:
        eval_rec = Evaluation.query.filter_by(
            interview_id=iid,
            evaluator_token=tk,
            participant_code=a.code
        ).first()
        if eval_rec:
            extra_data_json = json.loads(eval_rec.extra_data)
            overall = 0
            for key in eval_struct.keys():
                for field in eval_struct[key].keys():
                    overall = round(overall + extra_data_json[key][field], 2)
            my_scores[a.code] = round(overall, 2)
        else:
            my_scores[a.code] = None

    return render_template("evaluator_dashboard.html",
                           applicants=applicants,
                           interview=iv,
                           my_scores=my_scores)


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
    
    evaluation = Evaluation.query.filter_by(
        interview_id=iid,
        evaluator_token=tk,
        participant_code=code
    ).first()

    eval_type = Interview.query.filter_by(id=iid).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]
    if request.method == "POST":
        try:
            extra_data = {}
            for key in eval_struct.keys():
                extra_data[key] = {}
                for field in eval_struct[key].keys():
                    extra_data[key][field] = float(request.form.get(f'{key}_{field}', 0))
        except ValueError:
            flash("Please enter valid numeric values.", "error")
            return redirect(url_for("evaluator_applicant_detail", code=code))
        # Validate that each score is between 0 and 1

        for key in eval_struct.keys():
            for field in eval_struct[key].keys():   
                if extra_data[key][field] <= 0 or extra_data[key][field] > eval_struct[key][field]:
                    flash("Each criteria must be between 0 and 1.", "error")
                    return redirect(url_for("evaluator_applicant_detail", code=code))

        extra_data_str = json.dumps(extra_data)            
        if evaluation:
            evaluation.extra_data = extra_data_str
            flash("Your evaluation has been updated.", "success")
        else:
            evaluation = Evaluation(
                interview_id=iid,
                evaluator_token=tk,
                participant_code=code,
                extra_data=extra_data_str
            )
            db.session.add(evaluation)
            flash("Your evaluation has been submitted.", "success")

        db.session.commit()
        return redirect(url_for("evaluator_dashboard"))
    
    if evaluation and evaluation.extra_data:
        try:
            existing_data = json.loads(evaluation.extra_data)
        except ValueError:
            existing_data = {}
    else:
        existing_data = {}

    overall = None
    if evaluation:
        extra_data_json = json.loads(evaluation.extra_data)
        overall = 0
        for key in eval_struct.keys():
            for field in eval_struct[key].keys():
                overall = round(overall + extra_data_json[key][field], 2)
    return render_template(
        "evaluator_applicant_detail.html",
        applicant=applicant,
        evaluation=evaluation,
        overall=overall,
        eval_struct=eval_struct,
        existing_data=existing_data  # Pass it directly
    )

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
