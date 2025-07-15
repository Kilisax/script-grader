from dash import Dash, html, dcc, callback, Input, Output, no_update, State
import dash_mantine_components as dmc
import matplotlib.pyplot as plt
import matplotlib
import io
import base64
import contextlib
import os
import re
from dash.exceptions import PreventUpdate

app = Dash(suppress_callback_exceptions=True)

matplotlib.use("Agg")  # Use a non-GUI backend

def execute_student_script(filename):
    output_buffer = io.StringIO()
    plot_sections = []
    code_output_chunks = []

    exec_namespace = {}

    # Backup the real plt.show
    original_show = plt.show

    def custom_show(*args, **kwargs):
        # Save current print output
        current_output = output_buffer.getvalue()
        output_buffer.truncate(0)
        output_buffer.seek(0)

        buf = io.BytesIO()
        fig = plt.gcf()
        fig.savefig(buf, format="png")
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        plot_sections.append({
            'output': current_output.strip(),
            'image': encoded
        })

    plt.show = custom_show  # Override show temporarily

    try:
        with contextlib.redirect_stdout(output_buffer):
            with open(filename, "r") as f:
                code = f.read()
            exec(code, exec_namespace, exec_namespace)

        # Capture final output (if not followed by plt.show)
        final_output = output_buffer.getvalue().strip()
        if final_output:
            code_output_chunks.append(final_output)

    except Exception as e:
        code_output_chunks.append(f"[ERROR]: {e}")
    finally:
        plt.show = original_show  # Restore show

    # Build Dash components
    components = []

    # Show a warning if no plt.show() was ever called
    if not plot_sections:
        components.append(html.Div(
            "⚠️ Hinweis: Es wurden keine plt.show() Aufrufe gefunden, daher keine Plots angezeigt.",
            style={'color': 'orange', 'marginBottom': '1em'}
        ))

    # Show each plot alongside its related print output
    for section in plot_sections:
        if section['output']:
            components.append(html.Pre(section['output']))
        components.append(html.Img(
            src=f'data:image/png;base64,{section["image"]}',
            style={'width': '600px', 'height': 'auto', 'display': 'block', 'marginBottom': '20px'}
        ))

    # Remaining print output (not linked to a plot)
    for leftover in code_output_chunks:
        components.append(html.Pre(leftover))

    return html.Div(components, style = {
        "overflowX": 'scroll'
    })

def display_python_code(filename):
    try:
        with open(filename, 'r') as f:
            code_content = f.read()
    except Exception as e:
        return html.Div([f"Error reading file: {e}"])

    return html.Pre(
        html.Code(code_content, id = "code_children"),
        style={
            'whiteSpace': 'pre-wrap',
            'wordBreak': 'break-word',
            'backgroundColor': '#f8f8f8',
            'padding': '10px',
            'borderRadius': '5px',
            'border': '1px solid #ccc',
            'fontFamily': 'monospace',
            'fontSize': '14px',
            'overflowY': 'scroll',
            'height': '90vh',  # Adjust as needed (90% of viewport height)
            'maxHeight': '100vh',
            'overflowX': 'auto'
        }
    )


theme = {
    "primaryColor": "blue",
    "primaryShade": {"light": 5, "dark": 7},
    "colors": {
        "blue": [
            "#e7f5ff",  # 0
            "#d0ebff",  # 1
            "#a5d8ff",  # 2
            "#74c0fc",  # 3
            "#4dabf7",  # 4
            "#339af0",  # 5
            "#228be6",  # 6
            "#1c7ed6",  # 7
            "#1971c2",  # 8
            "#1864ab",  # 9
        ]
    },
    "defaultRadius": "md",  # Options: 'xs', 'sm', 'md', 'lg', 'xl'
}

parent_folder = os.path.dirname(os.path.dirname(__file__))

selected_folder_path = os.path.join(parent_folder, "uebungen")
files_in_folder = [f for f in os.listdir(selected_folder_path) if os.path.isfile(os.path.join(selected_folder_path, f))]

matrikelnummern = []
aufgabenzahl = []
for file in files_in_folder:
    if file.endswith("py") or file.endswith("tex") or file.endswith("pdf"):
        matrikelnummern += [file.split("_A")[0]]
        aufgabenzahl += [int(file.split("_A")[1][0])]
matrikelnummern = sorted(list(set(matrikelnummern)))
aufgabenanzahl = max(aufgabenzahl)
abgaben_tab = dmc.Center(
    [
        dmc.Select(
            data=[{"value": str(i), "label": m.split("_U")[0]} for i,m in enumerate(matrikelnummern)], 
            id="matrikel_selection",
            label = "Matrikelnummer Auswählen"
        ),
        dmc.Select(
            data=[{"value": str(i), "label": str(i)} for i in range(1,aufgabenanzahl+1)], 
            id = "exercise_selection",
            label = "Aufgabe auswählen"
        )
    ]
)


# Ensure there is only one PDF in the musterloesung folder and display it
musterloesung_folder = os.path.join(parent_folder, "musterloesung")
python_solution_files = [
    f for f in os.listdir(musterloesung_folder)
    if os.path.isfile(os.path.join(musterloesung_folder, f)) and f.endswith(".py")
]

app.layout = dmc.MantineProvider(
    theme=theme,
    children=[
        html.Div(
            dmc.Tabs(
                [
                    dmc.TabsList(
                        [
                            dmc.TabsTab("Abgaben", value="abgaben"),
                            dmc.TabsTab("Musterlösung", value="musterloesung"),
                        ],
                        grow=True,
                    ),
                    dmc.TabsPanel([abgaben_tab, html.Div(id="abgaben_children")], value="abgaben"),
                    dmc.TabsPanel(
                        [
                            dmc.Center(
                                dmc.Select(
                                    data=[{"value": str(i), "label": str(i)} for i in range(1,len(python_solution_files)+1)], 
                                    id = "solution_selection",
                                    label = "Aufgabe auswählen"
                                )
                            ),
                            html.Div(id="solution_children")
                        ],
                    value="musterloesung")
                ],
                value="abgaben"
            )
        ),
        dcc.Store(
            data = {nummer: 0 for nummer in matrikelnummern},
            id = "points-memory"
        )
    ]
)


@callback(
    Output("solution_children", "children"),
    Input("solution_selection", "value"),
)
def update_solution_layout(exercise):
    if not exercise:
        raise PreventUpdate
    py_filename = python_solution_files[int(exercise)-1]
    full_py_filename = os.path.join(musterloesung_folder, py_filename)
    return dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Card(
                        [
                            dmc.Text("Code", fw = 800),
                            display_python_code(full_py_filename)

                        ],
                        withBorder=True,
                        shadow="sm",
                        radius="md",
                        w=650,
                    ),
                    dmc.Card(
                        [
                            dmc.Text("Output", fw = 800),
                            execute_student_script(full_py_filename),
                        ],
                        withBorder=True,
                        shadow="sm",
                        radius="md",
                        w=650,
                    )
                ],
                justify= "center",

            ),
        ],
        style = {"margin-bottom": "200px"}
    )
@callback(
    Output("abgaben_children", "children"),
    Input("matrikel_selection", "value"),
    Input("exercise_selection", "value"),
    prevent_initial_call=True
)
def update_abgaben_layout(matrikel, exercise):
    if not matrikel or not exercise:
        raise PreventUpdate
    py_filename = f"{matrikelnummern[int(matrikel)]}_A{exercise}.py"
    full_py_filename = os.path.join(selected_folder_path, py_filename)
    pdf_filename = f"{matrikelnummern[int(matrikel)]}_A{exercise}.pdf"
    tex_filename = f"{matrikelnummern[int(matrikel)]}_A{exercise}.tex"
    try:
        with open(full_py_filename, 'r') as f:
            code_content = f.read()
    except Exception as e:
        return html.Div([f"Error reading file: {e}"])    
    pattern = r"== (\d{1,2}) P =="
    matches = re.findall(pattern, code_content)
    # Extract all lines after the pattern appears
    lines_after_pattern = []
    if matches:
        lines = code_content.splitlines()
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                lines_after_pattern = lines[i + 1:]
                break
    if len(matches)>1:
        return html.Div(["Mehrere Zeilen gefunden in denen Punkte vergeben wurden, bitte manuell ändern"])
    elif not matches:
        points = 0
    else:
        points = int(matches[0])
    return dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Card(
                        [
                            dmc.Text("Code", fw = 800),
                            display_python_code(full_py_filename)

                        ],
                        withBorder=True,
                        shadow="sm",
                        radius="md",
                        w=650,
                    ),
                    dmc.Card(
                        [
                            dmc.Text("Output", fw = 800),
                            execute_student_script(full_py_filename),
                        ],
                        withBorder=True,
                        shadow="sm",
                        radius="md",
                        w=650,
                    )
                ],
                justify= "center",

            ),
            dmc.Stack(
                [
                    dmc.NumberInput(
                        value = points,
                        label = "Bewertung",
                        min = 0,
                        allowDecimal=False,
                        id = "points-input",
                    ),
                    dmc.Textarea(
                        lines_after_pattern,
                        autosize=True,
                        id = "comments-input",
                        w=550,
                    )
                ],
                align= "center",
            )
        ],
        style = {"margin-bottom": "200px"}
    )

@callback(
    Output("points-input", "value"),
    Output("code_children", "children"),
    Output("points-memory", "data"),
    Input("points-input", "value"),
    Input("comments-input", "value"),
    State("matrikel_selection", "value"),
    State("exercise_selection", "value"),
    State("points-memory", "data")
)
def update_python_file(points, comments, matrikel, exercise, current_points):
    if not matrikel or not exercise:
        return no_update, no_update, no_update

    py_filename = f"{matrikelnummern[int(matrikel)]}_A{exercise}.py"
    full_py_filename = os.path.join(selected_folder_path, py_filename)

    try:
        with open(full_py_filename, "r") as f:
            lines = f.readlines()

        pattern_points = r"== (\d{1,2}) P =="
        updated_points = False
        new_lines = []
        for i, line in enumerate(lines):
            if re.search(pattern_points, line):
                lines[i] = re.sub(pattern_points, f"== {points} P ==", line)
                new_lines = lines[:i+1]
                updated_points = True
                break

        if not updated_points:
            # Add points if not found
            new_lines = lines + [f"\n# == {points} P ==\n"]

        # Add updated comments after the grading line
        if comments:
            if isinstance(comments, list):
                comment_lines = [line if line.endswith("\n") else line + "\n" for line in comments]
            else:
                comment_lines = [line if line.endswith("\n") else line + "\n" for line in comments.splitlines()]
            # comment_lines = [line if line.endswith("\n") else line + "\n" for line in comments.splitlines()]
            new_lines.extend(comment_lines)

        with open(full_py_filename, "w") as f:
            f.writelines(new_lines)

        updated_code_content = "".join(new_lines)

    except Exception as e:
        print(f"Error updating file: {e}")
        return no_update, no_update, no_update

    current_points[matrikelnummern[int(matrikel)]] += points 
    return points, updated_code_content, current_points

# @callback(
#     Output("matrikel_selection", "data"),
#     Input("points-memory", "data")
# )
# def points_display(current_points):
#     print(current_points)
#     return [{"value": str(i), "label": f"{m.split('_U')[0]}  |  {current_points[m]}"} for i,m in enumerate(matrikelnummern)]

if __name__ == '__main__':
    app.run(debug=True)
