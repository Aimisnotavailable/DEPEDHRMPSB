import json
from io import BytesIO
from docxtpl import DocxTemplate
from scripts.path import DOC_PATH
from scripts.table_handler import TableHandler

def download_pdf(applicant_data, interview_data, eval_score, total_score, app_struct, eval_struct, weight_struct):
    # 1. Load & render your template
    edu_data = TableHandler().parse_table('table', 'education')
    exp_data = TableHandler().parse_table('table', 'experience')
    trn_data = TableHandler().parse_table('table', 'training')

    doc = DocxTemplate(f'{DOC_PATH}\{str(interview_data.type)}_RATING-SHEET.docx')
    context = {
            'ad' : {'code' : applicant_data.code, 'name' : str(applicant_data.name).upper(), 'contact_number' : str(applicant_data.contact_number)},
            'id' : {'type' : str(interview_data.type).upper(), 'title' : str(interview_data.position_title).upper(), 'sg_level' : interview_data.sg_level},
            's' : {'edu' : applicant_data.score_edu, 'exp' : applicant_data.score_exp, 'trn' : applicant_data.score_trn, 'ed' : json.loads(applicant_data.extra_data), 'ev' : eval_score, 'ts' : total_score},
            'lbl' : {'edu' : edu_data[str(applicant_data.raw_edu)], 'exp' : exp_data[str(applicant_data.raw_exp)], 'trn' : trn_data[str(applicant_data.raw_trn)],},
            'as' : {'labels' : [key for key in app_struct.keys()]}
    }

    # doc.render(context)
    # doc.save(f'{applicant_data.code}_{interview_data.type}.docx')
    doc.render(context)

    # 2. Write into a BytesIO buffer
    buf = BytesIO()
    doc.save(buf)       # DocxTemplate.save() accepts a file-like object
    buf.seek(0)         # rewind to the start

    # 3. send_file from that buffer
    return buf