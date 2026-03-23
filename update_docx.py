import docx
import copy

try:
    doc = docx.Document('app/download/sample3.docx')
    for table in doc.tables:
        found = False
        for row in table.rows:
            for cell in row.cells:
                if '{answer_explain}' in cell.text:
                    found = True
                    break
            if found: break
            
        if found:
            # Helper to copy row
            def copy_row(source_row):
                new_row = copy.deepcopy(source_row._tr)
                source_row._tr.addnext(new_row)
                return docx.table._Row(new_row, table)
            
            # add row for accepted_answers
            new_row1 = copy_row(table.rows[-1])
            new_row1.cells[0].text = '인정답안'
            new_row1.cells[1].text = '{accepted_answers}'
            
            # add row for scoring_criteria
            new_row2 = copy_row(table.rows[-1])
            new_row2.cells[0].text = '채점기준'
            new_row2.cells[1].text = '{scoring_criteria}'
            
            doc.save('app/download/sample3.docx')
            print('Successfully updated sample3.docx')
            break
except Exception as e:
    print('Error:', str(e))
