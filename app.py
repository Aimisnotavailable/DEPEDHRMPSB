import uuid
import json
from datetime import datetime
from functools import wraps
from enum import Enum

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc

from scripts.criteriatable import CriteriaTable
from scripts.incrementstable import IncrementsTable
from scripts.table_handler import TableHandler

from scripts.download_handler import download_applicant_data, download_CAR

from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secret-key"  # Change for production!
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///interviews.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# TO-DO
# SG LEVEL
# contact number email

EVAL_STRUCTURE = {
    "teacher 1" : {"Behavior Interview" : {"CATEGORY" : {
                        "aptitude" : 1,
                        "characteristics" : 1,
                        "fitness" : 1,
                        "leadership" : 1,
                        "communication" : 1
                    }, "TOTAL" : 5, "WEIGHT" : 5},
                    },
    "related teaching" : {
                    "Written Examination" : {"CATEGORY" : {
                        "focus and detail" : 2,
                        "organization" : 2,
                        "content" : 2,
                        "word choice" : 2,
                        "sentence, structure, grammar mechanics, and spelling" : 2,
                        "work sample test" : 5
                    }, "TOTAL" : 15, "WEIGHT" : 15},
                    "Behavior Interview" : {"CATEGORY" : {
                        "aptitude" : 1,
                        "characteristics" : 1,
                        "fitness" : 1,
                        "leadership" : 1,
                        "communication" : 1
                    }, "TOTAL" : 5, "WEIGHT" : 5},
                    },
    "higher teaching" : {       
                    "BEI" : {"CATEGORY" : {
                        "Alignment with the NCOIs" : 3,
                        "Clarity and Coherence" : 3,
                        "Active listening" : 3,
                        "Confidence" : 3,
                    }, "TOTAL" : 12, "WEIGHT" : 5},
                },
    "non teaching" : {
                    "Exam" :{"CATEGORY" : {
                        "written exam" : 5,
                        "practice set" : 10
                    }, "TOTAL" : 15, "WEIGHT" : 15},
                    "Behavior Interview" : {"CATEGORY" : {
                        "aptitude" : 1,
                        "characteristics" : 1,
                        "fitness" : 1,
                        "leadership" : 1,
                        "communication" : 1
                    }, "TOTAL" : 5, "WEIGHT" : 5},
                    },
    "school administration" : {
                    "Written Examination" : {"CATEGORY" : {
                        "focus and detail" : 1,
                        "organization" : 1,
                        "content" : 1,
                        "word choice" : 1,
                        "sentence, structure, grammar mechanics, and spelling" : 1,
                    }, "TOTAL" : 5, "WEIGHT" : 5},
                    "Behavior Interview" : {"CATEGORY" : {
                        "aptitude" : 2,
                        "characteristics" : 2,
                        "fitness" : 2,
                        "leadership" : 2,
                        "communication" : 2
                    }, "TOTAL" : 10, "WEIGHT" : 10},
                    }
}                 


WEIGHT_STRUCTURE = {
    "teacher 1" : {
        "education" : 10,
        "experience" : 10,
        "training" : 10,
    },
    "related teaching" : {
        "education" : 10,
        "experience" : 10,
        "training" : 10,
    },
    "higher teaching" : {
        "education" : 10,
        "experience" : 10,
        "training" : 10,
    },  
    "non teaching" : {
        "education" : 5,
        "experience" : 5,
        "training" : 20,
    },
    "school administration" : {
        "education" : 10,
        "experience" : 10,
        "training" : 10,
    },
}

APPLICANT_STRUCTURE = {
    "teacher 1" : {
        "lpt_rating" : {"WEIGHT" : 10, "MAX_SCORE" : 100, "LABEL" : "LPT/PBET/LEPT Rating"},
        "cot" : {"WEIGHT" : 35, "MAX_SCORE" : 30, "LABEL" : "COT"},
        "trf_rating" : {"WEIGHT" : 25, "MAX_SCORE" : 25, "LABEL" : "TRF"}
    },
    "related teaching" : {
        "performance" : {"WEIGHT" : 20, "MAX_SCORE" : 20, "LABEL" : "PERFORMANCE"},
        "outstanding_accomplishment" : {"WEIGHT" : 5, "MAX_SCORE" : 5, "LABEL" : "OUTSTANDING ACCOMPLISHMENT"},
        "application_of_education" : {"WEIGHT" : 15, "MAX_SCORE" : 15, "LABEL" : "APPLICATION OF EDUCATION"},
        "application_of_learning_and_development" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "APPLICATION OF LEARNING AND DEVELOPMENT"},
    },
    "higher teaching" : {
        "performance" : {"WEIGHT" : 30, "MAX_SCORE" : 30, "LABEL" : "PERFORMANCE"},
        "ppst_cois" : {"WEIGHT" : 25, "MAX_SCORE" : 25, "LABEL" : "PPST COIS"},
        "ppst_ncois" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "PPST NCOIS"},
    },
    "non teaching" : {
        "performance" : {"WEIGHT" : 20, "MAX_SCORE" : 20, "LABEL" : "PERFORMANCE"},
        "outstanding_accomplishment" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "OUTSTANDING ACCOMPLISHMENT"},
        "application_of_education" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "APPLICATION OF EDUCATION"},
        "application_of_learning_and_development" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "APPLICATION OF LEARNING AND DEVELOPMENT"},
    },
    "school administration" : {
        "performance" : {"WEIGHT" : 25, "MAX_SCORE" : 25, "LABEL" : "PERFORMANCE"},
        "outstanding_accomplishment" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "OUTSTANDING ACCOMPLISHMENT"},
        "application_of_education" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "APPLICATION OF EDUCATION"},
        "application_of_learning_and_development" : {"WEIGHT" : 10, "MAX_SCORE" : 10, "LABEL" : "APPLICATION OF LEARNING AND DEVELOPMENT"},
    },

}

# ------------------------------------------------------------------------------
# MODELS
# ------------------------------------------------------------------------------
class Interview(db.Model):
    __tablename__ = "interviews"

    id              = db.Column(db.String(8), primary_key=True)
    date            = db.Column(db.Date, nullable=False)
    base_edu        = db.Column(db.Integer, nullable=False)
    base_exp        = db.Column(db.Integer, nullable=False)
    base_trn        = db.Column(db.Integer, nullable=False)
    type            = db.Column(
                        db.Enum(
                          "non teaching",
                          "teacher 1",
                          "school administration",
                          "related teaching",
                          "higher teaching",
                          name="interview_type"
                        ),
                        nullable=False,
                        default="non teaching"
                      )
    position_title  = db.Column(db.String(100))
    sg_level        = db.Column(db.String(100))
    weight_struct   = db.Column(db.String(150))
    status          = db.Column(db.String(7))

    # ORM cascades + passive_deletes so we don't have to loop & delete children manually
    evaluator_tokens = db.relationship(
        "EvaluatorToken",
        back_populates="interview",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    applicants = db.relationship(
        "Applicant",
        back_populates="interview",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    evaluations = db.relationship(
        "Evaluation",
        back_populates="interview",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class EvaluatorToken(db.Model):
    __tablename__ = "evaluator_tokens"

    token        = db.Column(db.String(8), primary_key=True)
    interview_id = db.Column(
                      db.String(8),
                      db.ForeignKey("interviews.id", ondelete="CASCADE"),
                      nullable=False
                    )
    registered   = db.Column(db.Boolean, default=False, nullable=False)

    # link back to parent
    interview    = db.relationship(
                      "Interview",
                      back_populates="evaluator_tokens"
                    )


class Applicant(db.Model):
    __tablename__ = "applicants"

    code           = db.Column(db.String(8), primary_key=True)
    interview_id   = db.Column(
                       db.String(8),
                       db.ForeignKey("interviews.id", ondelete="CASCADE"),
                       nullable=False
                     )
    name           = db.Column(db.String(128), nullable=False)
    address        = db.Column(db.String(256), nullable=False)
    contact_number = db.Column(db.String(256), nullable=False)
    email_addr     = db.Column(db.String(256), nullable=False)
    birthday       = db.Column(db.Date, nullable=False)
    age            = db.Column(db.Integer, nullable=False)
    sex            = db.Column(db.String(16), nullable=False)
    raw_edu        = db.Column(db.Integer, nullable=False)
    raw_exp        = db.Column(db.Integer, nullable=False)
    raw_trn        = db.Column(db.Integer, nullable=False)
    extra_data     = db.Column(db.Text, nullable=True)
    interview      = db.relationship(
                       "Interview",
                       back_populates="applicants"
                     )


class Evaluation(db.Model):
    __tablename__ = "evaluations"

    id               = db.Column(db.Integer, primary_key=True)
    interview_id     = db.Column(
                         db.String(8),
                         db.ForeignKey("interviews.id", ondelete="CASCADE"),
                         nullable=False
                       )
    evaluator_token  = db.Column(
                         db.String(8),
                         db.ForeignKey("evaluator_tokens.token", ondelete="CASCADE"),
                         nullable=False
                       )
    applicant_code   = db.Column(
                         db.String(8),
                         db.ForeignKey("applicants.code", ondelete="CASCADE"),
                         nullable=False
                       )
    extra_data       = db.Column(db.Text, nullable=True)

    interview        = db.relationship(
                         "Interview",
                         back_populates="evaluations"
                       )
    # (optionally, add relationships to EvaluatorToken & Applicant if you need them)

# ------------------------------------------------------------------------------
# Calculation HELPER
# ------------------------------------------------------------------------------

def calculate_baseline_score(applicant : Applicant, interview: Interview) -> dict[str, int]:
        crit = CriteriaTable()
        incs = IncrementsTable()
        
        weight_struct = json.loads(interview.weight_struct)
        delta_edu = crit.get_score(applicant.raw_edu, interview.base_edu)
        delta_exp = crit.get_score(applicant.raw_exp, interview.base_exp)
        delta_trn = crit.get_score(applicant.raw_trn, interview.base_trn)

        inc_edu = (weight_struct['education'] // 5)
        inc_exp = (weight_struct['experience'] // 5)
        inc_trn = (weight_struct['training'] // 5)

        applicant_score = {}

        applicant_score['edu'] = (incs.get_score(delta_edu, TableHandler().parse_table("increments", "education")) // 2) * inc_edu
        applicant_score['exp'] = (incs.get_score(delta_exp, TableHandler().parse_table("increments", "experience")) // 2) * inc_exp
        applicant_score['trn'] = (incs.get_score(delta_trn, TableHandler().parse_table("increments", "training")) // 2) * inc_trn

        return applicant_score

def calculate_applicant_score(applicant_data : Applicant, eval_struct):
    eval_records = Evaluation.query.filter_by(
         interview_id=applicant_data.interview_id,
         applicant_code=applicant_data.code
    ).all()
    applicant_data_score = calculate_baseline_score(applicant_data, applicant_data.interview)
    total_score = applicant_data_score['edu'] +applicant_data_score['exp'] + applicant_data_score['trn']
    
    app_json = json.loads(applicant_data.extra_data)
    eval_score = 0
    for field in app_json.keys():
        total_score += app_json[field]

    if eval_records:
        for key in eval_struct.keys():
            total = 0
            for eval_record in eval_records:
                temp_json = json.loads(eval_record.extra_data)
                for val in temp_json[key].values():
                    total += val
            eval_score += round(((total / eval_struct[key]['TOTAL']) * eval_struct[key]['WEIGHT']) / len(eval_records), 2)
            total_score += eval_score
    
    return total_score, eval_score
    
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
    interviews = Interview.query.order_by(Interview.date).all()

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
        position_data = str(request.form.get("sg_level")).split(';')
        now = datetime.now()
        date = datetime.strptime(now.strftime("%Y-%m-%d"), "%Y-%m-%d").date()

        weight_struct = json.dumps({
            "education": int(request.form.get("weight_edu", 10)),
            "experience": int(request.form.get("weight_exp", 10)),
            "training": int(request.form.get("weight_trn", 10)),}
        )

        iv = Interview(
            id=iid,
            base_edu=int(request.form.get("baseline_education", 1)),
            base_exp=int(request.form.get("baseline_experience", 1)),
            base_trn=int(request.form.get("baseline_training", 1)),
            date=date,
            type=interview_type,
            status="open",
            position_title=position_data[0],
            sg_level=position_data[1],
            weight_struct = weight_struct
        )
        db.session.add(iv)
        db.session.commit()

        flash(f"Interview {iid} created", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("create_interview.html")

@app.route("/admin/close_interview/<iid>")
@admin_required
def close_interview(iid):
    interview = Interview.query.filter_by(
         id=iid,
    ).all()[0]

    interview.status = "close"
    db.session.commit()
    flash(f"Interview {iid} successfully closed", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/update_interview/<iid>", methods=["GET", "POST"])
@admin_required
def update_interview(iid):
    th = TableHandler()
    ed_labels = th.parse_table("table", "education")
    ex_labels = th.parse_table("table", "experience")
    tr_labels = th.parse_table("table", "training")
    interview = Interview.query.filter_by(
         id=iid,
    ).all()[0]

    if interview.status == "close":
        flash(f"The interview is already closed you can't do that", "error")
        return redirect(url_for("admin_dashboard"))
    
    weight_struct = json.loads(interview.weight_struct)
    if request.method == "POST":
        
        interview.base_edu = int(request.form.get("baseline_education", 1))
        interview.base_exp=int(request.form.get("baseline_experience", 1))
        interview.base_trn=int(request.form.get("baseline_training", 1))

        weight_struct = json.dumps({
            "education": int(request.form.get("weight_edu", 10)),
            "experience": int(request.form.get("weight_exp", 10)),
            "training": int(request.form.get("weight_trn", 10)),}
        )

        interview.weight_struct = weight_struct
        
        db.session.commit()

        flash(f"Interview {iid} updated", "success")
        return redirect(url_for("admin_dashboard"))
    
    return render_template("update_interview.html", iid=iid,
                           interview=interview,
                           weight_struct=weight_struct,
                           ed_labels=ed_labels,
                           ex_labels=ex_labels,
                           tr_labels=tr_labels)

@app.route("/admin/delete_interview/<iid>")
@admin_required
def delete_interview(iid):
    interview = Interview.query.filter_by(
        id=iid,
        ).all()[0]

    db.session.delete(interview)
    db.session.commit()
    flash(f"Interview {iid} deleted", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/interview/<iid>")
@admin_required
def admin_interview_detail(iid):
    iv = Interview.query.get_or_404(iid)
    applicants = iv.applicants
    eval_tokens = iv.evaluator_tokens

    th = TableHandler()
    ed_labels = th.parse_table("table", "education")
    ex_labels = th.parse_table("table", "experience")
    tr_labels = th.parse_table("table", "training")

    applicant_structure = APPLICANT_STRUCTURE[iv.type]

    applicants_total_score : list[tuple] = []

    for applicant in applicants:
        applicants_total_score.append((applicant.code, applicant.name, sum(calculate_applicant_score(applicant_data=applicant, eval_struct=EVAL_STRUCTURE[iv.type]))))
    applicants_total_score = sorted(applicants_total_score, key= lambda x : -x[2])

    return render_template("admin_interview_detail.html",
                           interview=iv,
                           applicants=applicants,
                           applicant_structure=applicant_structure,
                           applicants_total_score=applicants_total_score,
                           eval_tokens=eval_tokens,
                           ed_labels=ed_labels,
                           ex_labels=ex_labels, 
                           tr_labels=tr_labels)

@app.route("/admin/applicant/<code>")
@admin_required
def applicant_detail(code):
    applicant = Applicant.query.get_or_404(code)
    extra_data = None
    if applicant.extra_data:
        try:
            extra_data = json.loads(applicant.extra_data)
        except Exception:
            extra_data = applicant.extra_data

    eval_records = Evaluation.query.filter_by(
         interview_id=applicant.interview_id,
         applicant_code=applicant.code
    ).all()

    eval_type = Interview.query.filter_by(id=applicant.interview_id).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]

    
    scores = []
    avg_eval = None
    applicant_structure = APPLICANT_STRUCTURE[applicant.interview.type]
    evaluation_scores = {}
    applicant_score = calculate_baseline_score(applicant, interview=applicant.interview)
    total_score = applicant_score.get('edu') + applicant_score.get('exp') + applicant_score.get('trn')

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
            avg_eval = round(((total / eval_struct[key]['TOTAL']) * eval_struct[key]['WEIGHT']) / len(eval_records), 2)
            evaluation_scores[key] = avg_eval
            total_score += avg_eval

    for eval_record in eval_records:
        overall = 0
        extra_data_json = json.loads(eval_record.extra_data)
        for key in eval_struct.keys():
            for field in eval_struct[key]['CATEGORY'].keys():
                overall = round(overall + extra_data_json[key][field], 2)
        scores.append(overall)



    return render_template("applicant_detail.html",
                           applicant=applicant,
                           applicant_score=applicant_score,
                           applicant_structure=applicant_structure,
                           extra_data=extra_data,
                           evaluation_scores=evaluation_scores,
                           total_score=total_score,
                           scores=scores,
                           avg_eval=avg_eval)

@app.route("/admin/applicant/<code>/download")
@admin_required
def download_applicant_data_file(code):
    applicant_data = Applicant.query.get_or_404(code)
    interview_data = Interview.query.get(applicant_data.interview_id)
    app_struct = APPLICANT_STRUCTURE[interview_data.type]
    eval_struct = EVAL_STRUCTURE[interview_data.type]
    weight_struct = json.loads(interview_data.weight_struct)

    eval_records = Evaluation.query.filter_by(
        interview_id=applicant_data.interview_id,
        applicant_code=applicant_data.code
    ).all()

    total_score, eval_score = calculate_applicant_score(applicant_data, eval_struct)
    doc_io = download_applicant_data(applicant_data, 
                                     calculate_baseline_score(applicant_data, interview_data), 
                                     interview_data, 
                                     eval_score, 
                                     total_score, 
                                     app_struct, 
                                     eval_struct, 
                                     weight_struct)
    # doc_io = download_pdf(code, Applicant(), Evaluation(), Interview(), EVAL_STRUCTURE=EVAL_STRUCTURE, APP_STRUCTURE=APPLICANT_STRUCTURE)
    # print(doc_io)

    return send_file(
        doc_io,
        as_attachment=True,
        download_name=f'APPLICANT {code}_DETAILS.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
@app.route("/admin/interview/<code>/download")
@admin_required
def download_interview_CAR(code):
    interview_data = Interview.query.get_or_404(code)
    applicant_data_temp = {'code' : [],
                      'name' : [],
                      'score' : [],
                      'eval_score' : [],
                      'total_score' : [],
                      }
    for applicant in interview_data.applicants:
        applicant_data_temp['code'].append(applicant.code)
        applicant_data_temp['name'].append(applicant.name)
        
        score_data_temp = []
        app_data_json = json.loads(applicant.extra_data)

        base_line_score = calculate_baseline_score(applicant, interview_data)
        for key in base_line_score.keys():
            score_data_temp.append(base_line_score[key])

        for key in app_data_json.keys():
            score_data_temp.append(app_data_json[key])

        applicant_data_temp['score'].append(score_data_temp)
        total_score, eval_score = calculate_applicant_score(applicant, EVAL_STRUCTURE[interview_data.type])
        applicant_data_temp['eval_score'].append(eval_score)
        applicant_data_temp['total_score'].append(total_score)
    
    combined = list(zip(
        applicant_data_temp['code'],
        applicant_data_temp['name'],
        applicant_data_temp['score'],
        applicant_data_temp['eval_score'],
        applicant_data_temp['total_score']
    ))

    sorted_packed_data = sorted(combined, key=lambda x : -x[4])

    applicant_data = {
        'code' : [],
        'name' : [],
        'score' : [],
        'eval_score' : [],
        'total_score' : [],
    }

    for data in sorted_packed_data:
        applicant_data['code'].append(data[0])
        applicant_data['name'].append(data[1])
        applicant_data['score'].append(data[2])
        applicant_data['eval_score'].append(data[3])
        applicant_data['total_score'].append(data[4])

    doc_io = download_CAR(applicant_data, interview_data)
    return send_file(
        doc_io,
        as_attachment=True,
        download_name=f'{interview_data.id}_CAR_.docx',
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
            for field in eval_struct[key]['CATEGORY'].keys():
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
    
    weight_struct = json.loads(interview_obj.weight_struct)
    # Text fields default to empty strings
    name           = request.form.get("name", "").strip()
    address        = request.form.get("address", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    email_addr     = request.form.get("email_address", "").strip()
    sex            = request.form.get("sex", "Female").strip()

    # Birthday parsing with a safe default of None
    bstr = request.form.get("birthday", "").strip()
    if bstr:
        try:
            bd = datetime.strptime(bstr, "%Y-%m-%d").date()
        except ValueError:
            bd = None
    else:
        bd = None

    # Numeric fields default to 0
    age      = int(request.form.get("age", 0))
    raw_edu  = int(request.form.get("education", 0))
    raw_exp  = int(request.form.get("experience", 0))
    raw_trn  = int(request.form.get("training", 0))

    p = Applicant(
        code=code,
        interview_id=iid,
        name=name,
        address=address,
        contact_number=contact_number,
        email_addr=email_addr,
        birthday=bd,
        age=age,
        sex=sex,
        raw_edu=raw_edu,
        raw_exp=raw_exp,
        raw_trn=raw_trn,
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


@app.route("/admin/update_applicant/<code>", methods=["GET", "POST"])
@admin_required
def update_applicant(code):
    applicant = Applicant.query.filter_by(
         code = code
    ).all()[0]
    interview = applicant.interview

    if interview.status == "close":
        flash(f"The interview is already closed you can't do that", "error")
        return redirect(url_for("admin_dashboard"))

    th = TableHandler()
    ed_labels = th.parse_table("table", "education")
    ex_labels = th.parse_table("table", "experience")
    tr_labels = th.parse_table("table", "training")

    applicant_structure = APPLICANT_STRUCTURE[interview.type]
    weight_struct = json.loads(interview.weight_struct)
    if request.method == 'POST':
        # Strings default to empty
        applicant.name           = request.form.get("name", "").strip()
        applicant.address        = request.form.get("address", "").strip()
        applicant.contact_number = request.form.get("contact_number", "").strip()
        applicant.email_addr     = request.form.get("email_address", "").strip()
        applicant.sex            = request.form.get("sex", "").strip()

        # Birthday: parse only if present, else leave as None (or set a default date)
        bstr = request.form.get("birthday", "").strip()
        if bstr:
            try:
                applicant.birthday = datetime.strptime(bstr, "%Y-%m-%d").date()
            except ValueError:
                applicant.birthday = None
        else:
            applicant.birthday = None

        # Numbers default to zero
        applicant.age = int(request.form.get("age", 0))

        raw_edu_temp = int(request.form.get("education", 0))
        raw_exp_temp = int(request.form.get("experience", 0))
        raw_trn_temp = int(request.form.get("training", 0))

        applicant.raw_edu = raw_edu_temp
        applicant.raw_exp = raw_exp_temp
        applicant.raw_trn = raw_trn_temp

        calculated_score = {}
        try:
            for field in applicant_structure.keys():
                calculated_score[field] = round((float(request.form.get(field, 0)) /  applicant_structure[field]['MAX_SCORE']) * applicant_structure[field]['WEIGHT'], 2)
        except ValueError:  
            flash("TRF rating must be numeric.", "error")
            return redirect(url_for("admin_interview_detail", iid=interview.id))
        # Store the TRF in extra_data as JSON
        applicant.extra_data = json.dumps(calculated_score)
        flash(f"Updated applicant {code}", "success")
        db.session.commit()
        return redirect(url_for("admin_interview_detail", iid=interview.id))


    return render_template("update_applicant.html",
                           interview=interview,
                           applicant=applicant,
                           applicant_structure=applicant_structure,
                           ed_labels=ed_labels,
                           ex_labels=ex_labels,
                           tr_labels=tr_labels,
                           extra_data_json=json.loads(applicant.extra_data))


@app.route("/admin/delete_applicant/<code>", methods=["GET", "POST"])
@admin_required
def delete_applicant(code):
    applicant = Applicant.query.filter_by(
        code=code,
    ).all()[0]
    if applicant.interview.status == "close":
        flash(f"Interview {applicant.interview.id} is already closed you can't do that", "error")
        return redirect(url_for("admin_dashboard"))
    flash(f"Applicant {applicant.code} data is deleted", "success")
    iid_temp = applicant.interview.id
    db.session.delete(applicant)
    db.session.commit()
    return redirect(url_for("admin_interview_detail", iid=iid_temp))

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

            interview = Interview.query.filter_by(id=et.interview_id).first()
            if interview.status == "close":
                flash(f"The interview is already closed you can't do that", "error")
                return render_template("evaluator_login.html")
            
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
    applicants = iv.applicants

    # print(evaluation.interview.type)
    eval_type = Interview.query.filter_by(id=iid).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]
    # For each applicant, get only the evaluation record for the current evaluator.
    my_scores = {}
    for a in applicants:
        eval_rec = Evaluation.query.filter_by(
            interview_id=iid,
            evaluator_token=tk,
            applicant_code=a.code
        ).first()
        if eval_rec:
            extra_data_json = json.loads(eval_rec.extra_data)
            overall = 0
            for key in eval_struct.keys():
                for field in eval_struct[key]['CATEGORY'].keys():
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
    applicant = Applicant.query.get_or_404(code)
    if applicant.interview_id != iid:
        flash("Invalid applicant for this interview.", "error")
        return redirect(url_for("evaluator_dashboard"))
    
    evaluation = Evaluation.query.filter_by(
        interview_id=iid,
        evaluator_token=tk,
        applicant_code=code
    ).first()

    eval_type = Interview.query.filter_by(id=iid).first().type
    eval_struct = EVAL_STRUCTURE[eval_type]
    if request.method == "POST":
        try:
            extra_data = {}
            for key in eval_struct.keys():
                extra_data[key] = {}
                for field in eval_struct[key]['CATEGORY'].keys():
                    extra_data[key][field] = float(request.form.get(f'{key}_{field}', 0))
        except ValueError:
            flash("Please enter valid numeric values.", "error")
            return redirect(url_for("evaluator_applicant_detail", code=code))
        # Validate that each score is between 0 and 1

        for key in eval_struct.keys():
            for field in eval_struct[key]['CATEGORY'].keys():
                if extra_data[key][field] <= 0 or extra_data[key][field] > eval_struct[key]['CATEGORY'][field]:
                    print("GAGO KA BA HANS")
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
                applicant_code=code,
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
            for field in eval_struct[key]['CATEGORY'].keys():
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
