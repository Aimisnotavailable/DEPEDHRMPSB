import json
from io import BytesIO
from docxtpl import DocxTemplate
from docx import Document
from scripts.path import DOC_PATH
from scripts.table_handler import TableHandler

def delete_excess_rows(input_path: str, output_path: str, ad_size: int, header_rows: int = 1):
    doc = Document(input_path)
    rows_to_keep = header_rows + ad_size
    # Remove rows from bottom up to avoid index shift
    total_rows = 0
    for table in doc.tables:
        rows = len(table.rows) - 1
        for row in table.rows:
                if total_rows > rows_to_keep:
                        table._tbl.remove(row._tr)
                total_rows += 1
    doc.save(output_path)

def download_applicant_data(applicant_data, applicant_baseline_scores, interview_data, eval_score, total_score, app_struct, eval_struct, weight_struct):
    # 1. Load & render your template
    file_type = "RATING-SHEET"
    edu_data = TableHandler().parse_table('table', 'education')
    exp_data = TableHandler().parse_table('table', 'experience')
    trn_data = TableHandler().parse_table('table', 'training')

    doc = DocxTemplate(f'{DOC_PATH}\{file_type}\{str(interview_data.type)}_{file_type}.docx')
    context = {
            'ad' : {'code' : applicant_data.code, 'name' : str(applicant_data.name).upper(), 'contact_number' : str(applicant_data.contact_number)},
            'id' : {'type' : str(interview_data.type).upper(), 'title' : str(interview_data.position_title).upper(), 'sg_level' : interview_data.sg_level},
            's' : {'edu' : applicant_baseline_scores.get('edu', 0), 'exp' : applicant_baseline_scores.get('exp', 0), 'trn' : applicant_baseline_scores.get('trn', 0), 'ed' : json.loads(applicant_data.extra_data), 'ev' : eval_score, 'ts' : total_score},
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

def download_CAR(applicant_data, interview, f_type="with_name"):
    # 1. Load & render your template
    file_type = "CAR_" + f_type
#     edu_data = TableHandler().parse_table('table', 'education')
#     exp_data = TableHandler().parse_table('table', 'experience')
#     trn_data = TableHandler().parse_table('table', 'training')
    
    code = applicant_data.get('code', [])
    name = applicant_data.get('name', [])
    score = applicant_data.get('score', [])
    eval_score = applicant_data.get('eval_score', [])
    total_score = applicant_data.get('total_score', [])

    delete_excess_rows(f'{DOC_PATH}/CAR/{str(interview.type)}_{file_type}.docx', 'temp.docx', len(code))

    doc = DocxTemplate('temp.docx')
    context = {
            'ad' : {"name" : name, "code" : code, "score" : score, "eval_score" : eval_score, "total_score" : total_score},
            'id' : {'type' : interview.position_title}
    }

    # doc.render(context)
    # doc.save(f'{applicant_data.       code}_{interview_data.type}.docx')
    doc.render(context)

    # 2. Write into a BytesIO buffer
    buf = BytesIO()
    doc.save(buf)       # DocxTemplate.save() accepts a file-like object
    buf.seek(0)         # rewind to the start

    # 3. send_file from that buffer
    return buf