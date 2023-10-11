from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.attributes import flag_modified
import random
import string


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sheet.db'
db = SQLAlchemy(app)


class Sheet(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(256))
    search_string = db.Column(db.String(256))
    columns = db.Column(db.JSON)
    data = db.Column(db.JSON)


# push context manually to app
with app.app_context():
    db.create_all()


@app.route('/')
def root():
    sheet_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


@app.route('/sheet/<sheet_id>', methods=['GET', 'POST'])
def sheet_view(sheet_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    
    if request.method == 'POST':
        # Handle your operations here like saving cell, add/remove row/col, search
        pass

    if not sheet:
        # Create a new sheet if it doesn't exist
        sheet = Sheet(
            id=sheet_id,
            title="New spreadsheet",
            search_string="",
            columns=[
                {
                    "id": "1",
                    "name": "Column 1",
                },
                {
                    "id": "2",
                    "name": "Column 2",
                },
                {
                    "id": "3",
                    "name": "Column 3",
                }
            ],
            data=[
                {
                    "id": "1",
                    "1": "Cell 1",
                    "2": "Cell 2",
                    "3": "Cell 3",
                },
                {
                    "id": "2",
                    "1": "Cell 1",
                    "2": "Cell 2",
                    "3": "Cell 3",
                },
                {
                    "id": "3",
                    "1": "Cell 1",
                    "2": "Cell 2",
                    "3": "Cell 3",
                },
            ]
        )
        db.session.add(sheet)
        db.session.commit()

    # Filter data based on search string
    if sheet.search_string:
        sheet.data = [row for row in sheet.data if sheet.search_string.lower() in str(row.values()).lower()]

    footer_values = compute_footer_values(sheet)

    return render_template(
        'sheet.html',
        sheet=sheet,
        footer_values=footer_values
    )


def compute_footer_values(sheet):
    """
    Compute footer values for each column.

    This works by iterating over each column and checking if all values in the
    column are numeric. If so, the sum of all values is returned. Otherwise,
    the number of non-empty values is returned.
    """
    footer_values = []
    for column in sheet.columns:
        col_id = column['id']
        values = [row[col_id] if col_id in row else "" for row in sheet.data]
        
        if all(str(value).replace(".", "", 1).isdigit() for value in values if value):
            footer_values.append({
                "type": "sum",
                "value": sum([float(value) for value in values if value])
            })
        else:
            footer_values.append({
                "type": "count",
                "value": len([value for value in values if value])
            })

    return footer_values


# POST route for updating search string
@app.route('/sheet/<sheet_id>/search', methods=['POST'])
def update_search(sheet_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    # Update search string
    sheet.search_string = request.form.get('search_string')
    db.session.commit()

    # Re-generate sheet view
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


# POST route for updating sheet title
@app.route('/sheet/<sheet_id>/title', methods=['POST'])
def update_title(sheet_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    # Update sheet title
    sheet.title = request.form.get('sheet_title')
    db.session.commit()

    # Re-generate sheet view
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


@app.route('/sheet/<sheet_id>/row/<row_id>/column/<column_id>', methods=['POST'])
def update_cell(sheet_id, row_id, column_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    new_data = []
    for row in sheet.data:
        print(row['id'], row_id)
        if row['id'] == row_id:
            print("Found row")
            print(column_id)
            row[column_id] = request.form.get('cell_value')
        new_data.append(row)

    print(new_data)
    sheet.data = list(new_data)
    flag_modified(sheet, "data")

    # Update sheet
    db.session.commit()

    # Re-generate sheet view
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


# POST endpoint for adding a new row
@app.route('/sheet/<sheet_id>/row', methods=['POST'])
def add_row(sheet_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404
    
    # Generate random ID
    row_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))

    # Create new row
    new_row = {
        "id": row_id
    }
    for column in sheet.columns:
        new_row[column['id']] = ""

    # Add new row to sheet
    sheet.data.append(new_row)
    flag_modified(sheet, "data")

    # Update sheet
    db.session.commit()

    # Re-generate sheet view
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


# DELETE endpoint for removing a row
@app.route('/sheet/<sheet_id>/row/<row_id>', methods=['DELETE'])
def remove_row(sheet_id, row_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    # Remove row from sheet
    sheet.data = [row for row in sheet.data if row['id'] != row_id]
    flag_modified(sheet, "data")

    # Update sheet
    db.session.commit()

    # Re-generate sheet view
    return sheet_view(sheet_id)


# POST endpoint for adding a new column
@app.route('/sheet/<sheet_id>/column', methods=['POST'])
def add_column(sheet_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    # Generate random ID
    column_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))

    # Create new column
    new_column = {
        "id": column_id,
        "name": request.form.get('column_name') or "New column"
    }

    # Add new column to sheet
    sheet.columns.append(new_column)
    flag_modified(sheet, "columns")

    # Update sheet
    db.session.commit()

    # Re-generate sheet view
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


# POST update for updating a column header
@app.route('/sheet/<sheet_id>/column/<column_id>', methods=['POST'])
def update_column(sheet_id, column_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    # Update column name
    for column in sheet.columns:
        if column['id'] == column_id:
            column['name'] = request.form.get('column_name')
            break
    flag_modified(sheet, "columns")

    # Update sheet
    db.session.commit()

    # Re-generate sheet view
    return redirect(url_for('sheet_view', sheet_id=sheet_id))


# DELETE endpoint for removing a column
@app.route('/sheet/<sheet_id>/column/<column_id>', methods=['DELETE'])
def remove_column(sheet_id, column_id):
    sheet = db.session.execute(db.select(Sheet).filter_by(id=sheet_id)).scalar_one_or_none()
    if not sheet:
        return "Sheet not found", 404

    # Remove column from sheet
    sheet.columns = [column for column in sheet.columns if column['id'] != column_id]
    flag_modified(sheet, "columns")

    # Update sheet
    db.session.commit()

    # Re-generate sheet view
    return sheet_view(sheet_id)


if __name__ == '__main__':
    app.run(debug=True)
