import dash
from dash import html, dcc, Input, Output, State, callback, ctx, no_update
import dash_ag_grid as dag
import pandas as pd
import requests
import json

import urllib.parse

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

API_URL = "http://127.0.0.1:8000"

# Fetch schema for dropdowns
def get_schema():
    try:
        response = requests.get(f"{API_URL}/schema")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

schema = get_schema()
current_table = "users"
table_columns = schema.get(current_table, [])

# Generate Column Defs dynamically
column_defs = [{"field": col, "checkboxSelection": (col == "id"), "headerCheckboxSelection": (col == "id")} for col in table_columns]
column_defs.append({
    "headerName": "Actions",
    "field": "actions",
    "cellRenderer": "markdown",
})

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

def get_grid_layout():
    return html.Div([
        html.Div([
            html.H2("MyLogo", style={"marginRight": "20px", "fontSize": "1.5rem"}),
            html.Button("Reports", className="tab-button active"),
            html.Button("Extract", className="tab-button"),
        ], className="header"),

        html.Div([
            dcc.Dropdown(
                id="filter-column",
                options=[{"label": col, "value": col} for col in table_columns],
                placeholder="Select Column",
                style={"width": "200px"}
            ),
            dcc.Dropdown(
                id="filter-operator",
                options=[
                    {"label": "Equals", "value": "eq"},
                    {"label": "Not Equals", "value": "neq"},
                    {"label": "Greater Than", "value": "gt"},
                    {"label": "Less Than", "value": "lt"},
                    {"label": "Like", "value": "like"},
                    {"label": "In", "value": "in"},
                    {"label": "Between", "value": "between"},
                ],
                placeholder="Operator",
                style={"width": "150px"}
            ),
            dcc.Input(id="filter-value", placeholder="Value", className="filter-input"),
            html.Button("Filter", id="filter-btn", className="btn-primary"),
            html.Button("Hide Selected", id="hide-selected-btn", className="btn-secondary", style={"marginLeft": "auto"}),
        ], className="filter-container"),

        html.Div([
            dag.AgGrid(
                id="data-grid",
                columnDefs=column_defs,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                dashGridOptions={"rowSelection": "multiple"},
                style={"height": "500px", "width": "100%"},
            )
        ], className="grid-container"),
        
        dcc.Store(id="refresh-trigger", data=0),
    ])

def get_detail_layout(row_id):
    # Fetch row data
    row_data = {}
    try:
        # We don't have a direct "get by id" endpoint that returns just the dict for the frontend easily 
        # without using the execute endpoint or the new mutate endpoint logic?
        # Actually we can use the execute endpoint with a filter.
        plan = {
            "table": current_table,
            "filters": [{"column": "id", "operator": "eq", "value": int(row_id)}]
        }
        response = requests.post(f"{API_URL}/execute", json=plan)
        if response.status_code == 200:
            data = response.json()
            if data:
                row_data = data[0]
    except Exception as e:
        print(f"Error fetching row: {e}")

    form_inputs = []
    for key, value in row_data.items():
        input_type = "text"
        if isinstance(value, (int, float)):
            input_type = "number"
        
        form_inputs.append(html.Div([
            html.Label(key.capitalize(), className="form-label"),
            dcc.Input(
                id={"type": "edit-input", "index": key},
                value=value,
                type=input_type,
                className="form-control",
                disabled=(key == "id")
            )
        ], className="form-group"))

    return html.Div([
        html.H2("Row Details"),
        html.Div(form_inputs, style={"maxWidth": "600px", "margin": "0 auto", "backgroundColor": "white", "padding": "20px", "borderRadius": "8px", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"}),
        html.Div([
            html.Button("Save", id="save-btn", className="btn-primary"),
            html.Button("Delete", id="delete-btn", className="btn-danger", style={"marginLeft": "10px"}),
            html.Button("Cancel", id="cancel-btn", className="btn-secondary", style={"marginLeft": "10px"}),
        ], style={"marginTop": "20px", "textAlign": "center"}),
        dcc.Store(id="current-row-id", data=row_id),
        html.Div(id="dummy-output", style={"display": "none"})
    ], style={"padding": "20px"})

@callback(Output("page-content", "children"), Input("url", "pathname"), Input("url", "search"))
def display_page(pathname, search):
    if pathname == "/details":
        # Parse ID from search params
        query_params = urllib.parse.parse_qs(search.lstrip("?"))
        row_id = query_params.get("id", [None])[0]
        if row_id:
            return get_detail_layout(row_id)
        return html.Div("No ID provided")
    return get_grid_layout()

# Grid Callbacks
@callback(
    Output("data-grid", "rowData"),
    Input("filter-btn", "n_clicks"),
    Input("refresh-trigger", "data"),
    State("filter-column", "value"),
    State("filter-operator", "value"),
    State("filter-value", "value"),
)
def update_table(n_clicks, refresh, col, op, val):
    plan = {"table": current_table}
    if col and op and val:
        try:
            if op == "between":
                val = [v.strip() for v in val.split(",")]
                try: val = [float(v) for v in val]
                except: pass
            else:
                try: val = float(val)
                except: pass
        except: pass 
        plan["filters"] = [{"column": col, "operator": op, "value": val}]
    
    try:
        response = requests.post(f"{API_URL}/execute", json=plan)
        if response.status_code == 200:
            data = response.json()
            for row in data:
                row["actions"] = "**[View / Edit]**"
            return data
    except Exception as e:
        print(f"Error fetching data: {e}")
    return []

@callback(
    Output("url", "href"),
    Input("data-grid", "cellClicked"),
    prevent_initial_call=True
)
def navigate_to_detail(cell_clicked):
    if not cell_clicked:
        return no_update
    
    col_id = cell_clicked.get("colId")
    row_data = cell_clicked.get("data")
    
    if col_id == "actions" and row_data:
        return f"/details?id={row_data['id']}"
    
    return no_update

# Detail Page Callbacks
@callback(
    Output("url", "href", allow_duplicate=True),
    Input("save-btn", "n_clicks"),
    Input("delete-btn", "n_clicks"),
    Input("cancel-btn", "n_clicks"),
    State("current-row-id", "data"),
    State({"type": "edit-input", "index": dash.ALL}, "value"),
    State({"type": "edit-input", "index": dash.ALL}, "id"),
    prevent_initial_call=True
)
def handle_detail_actions(save_clicks, delete_clicks, cancel_clicks, curr_id, values, ids):
    trigger = ctx.triggered_id
    
    if trigger == "cancel-btn":
        return "/"
        
    if trigger == "save-btn":
        data = {}
        for val, id_dict in zip(values, ids):
            key = id_dict["index"]
            data[key] = val
        if "id" in data: del data["id"]
            
        mutation = {
            "table": current_table,
            "operation": "update",
            "data": data,
            "filters": [{"column": "id", "operator": "eq", "value": curr_id}]
        }
        try:
            requests.post(f"{API_URL}/mutate", json=mutation)
        except Exception as e:
            print(f"Error saving: {e}")
        return "/"
        
    if trigger == "delete-btn":
        mutation = {
            "table": current_table,
            "operation": "delete",
            "filters": [{"column": "id", "operator": "eq", "value": curr_id}]
        }
        try:
            requests.post(f"{API_URL}/mutate", json=mutation)
        except Exception as e:
            print(f"Error deleting: {e}")
        return "/"
        
    return no_update

if __name__ == "__main__":
    app.run(debug=True, port=8050)


