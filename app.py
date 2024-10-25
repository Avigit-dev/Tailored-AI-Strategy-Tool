import streamlit as st
st.set_page_config(layout='wide')
import io
import json
import logging
from typing import List, Tuple
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from textwrap import wrap
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Add Caching
@st.cache_data
def load_dynamic_logic():
    with open('dynamic_logic_with_use_cases.json', 'r') as file:
        return json.load(file)

dynamic_logic_with_use_cases = load_dynamic_logic()

@st.cache_resource
def load_image(image_path):
    return Image.open(image_path)

background_image = load_image("Background_Tool.png")
logo_image = load_image("efeso_logo.png")

# Load the logo and background image (Ensure the updated files are in the same directory as app.py)
logo_path = "efeso_logo.png"
background_image_path = "Background_Tool.png"

# Load the dynamic logic structure from an external JSON file
with open('dynamic_logic_with_use_cases.json', 'r') as file:
    dynamic_logic_with_use_cases = json.load(file)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to get available methods, tools, and KPIs based on the selected goal
def get_available_options(goal: str) -> List[str]:
    if goal in dynamic_logic_with_use_cases:
        return dynamic_logic_with_use_cases[goal]['methods']
    else:
        logger.warning(f"Goal '{goal}' not found in dynamic logic structure.")
        return []

def get_tools_and_use_cases(goal: str, method: str) -> Tuple[List[str], List[str], List[str]]:
    if goal in dynamic_logic_with_use_cases and method in dynamic_logic_with_use_cases[goal]['tools']:
        tools_data = dynamic_logic_with_use_cases[goal]['tools'][method]
        tools = tools_data['tools']
        use_cases = tools_data['use_cases']
        partners = tools_data['partners']
        return tools, use_cases, partners
    else:
        logger.error(f"Method '{method}' not found under goal '{goal}'.")
        return [], [], []

# Initialize session state variables
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'pdf_output' not in st.session_state:
    st.session_state.pdf_output = None

# Load and display the background image
background = Image.open(background_image_path)
st.image(background, use_column_width=True)

# Streamlit App Custom Styling
st.markdown(f"""
    <style>
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 2.5em;
            color: #333;
            margin-right: 20px;
        }}
        .dropdown-text {{
            font-weight: bold;
            font-size: 1.2em;
            color: #333;
        }}
        .stButton button {{
            background-color: #E96C25;
            color: white;
        }}
        .stDownloadButton button {{
            background-color: #E96C25;
            color: white;
        }}
        .full-width {{
            width: 100%;
        }}
        .horizontal-container {{
            display: flex;
            flex-direction: row;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .horizontal-container > div {{
            flex: 1;
            min-width: 150px;
        }}
        .orange-text {{
            color: #E96C25;
        }}
    </style>
""", unsafe_allow_html=True)

# Display the header with title and logo
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("<h1>Tailored AI Strategy Tool</h1>", unsafe_allow_html=True)
with col2:
    st.image(logo_path, use_column_width=False, width=300)

# Create a horizontal layout for the sentence and dropdowns
st.markdown("<div class='horizontal-container'>", unsafe_allow_html=True)

# Dropdown for selecting a goal
st.markdown("<div class='dropdown-text'>Our R&D Transformation goal is to:</div>", unsafe_allow_html=True)
goal = st.selectbox('', list(dynamic_logic_with_use_cases.keys()), label_visibility='collapsed')

# Static text
st.markdown("<div class='dropdown-text'>which will be accomplished by</div>", unsafe_allow_html=True)

# Dropdown for methods based on goal selection
if goal:
    methods = get_available_options(goal)
    method = st.selectbox('', methods, label_visibility='collapsed')

# Static text
st.markdown("<div class='dropdown-text'>through the strategic initiatives in</div>", unsafe_allow_html=True)

# Dropdown for tools based on method selection
if method:
    tools, use_cases, partners = get_tools_and_use_cases(goal, method)
    tool = st.selectbox('', tools, label_visibility='collapsed')

# Static text
st.markdown("<div class='dropdown-text'>and success will be evaluated by</div>", unsafe_allow_html=True)
kpi = st.selectbox('', dynamic_logic_with_use_cases[goal]['kpis'], label_visibility='collapsed')

# Close the horizontal layout for dropdowns
st.markdown("</div>", unsafe_allow_html=True)

# Display use cases and partners based on selections
st.write(f"### Recommended Use Cases for {goal}:")
st.write(f"**Use Cases**: {', '.join(use_cases)}")

st.write(f"### Suitable Partners:")
st.write(f"**Partners**: {', '.join(partners)}")

# Function to add data to Google Sheets
def add_data_to_google_sheet(user_data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["google_service_account"], scope
    )
    client = gspread.authorize(credentials)
    # Open your Google Sheet by name
    sheet = client.open("client_inputs_strategytoolrnd").sheet1
    # Append the data
    sheet.append_row(list(user_data.values()))

# Contact information form
with st.form("contact_form"):
    st.write("### Please provide your contact information to download the report")
    name = st.text_input("Name")
    email = st.text_input("Email")
    company = st.text_input("Company")
    phone = st.text_input("Phone Number")
    submitted = st.form_submit_button("Submit")
    if submitted:
        if name and email and company and phone:
            # Collect data
            user_data = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'name': name,
                'email': email,
                'company': company,
                'phone': phone,
                'goal': goal,
                'method': method,
                'tool': tool,
                'kpi': kpi,
                'use_cases': ', '.join(use_cases),
                'partners': ', '.join(partners)
            }
            # Save to Google Sheets
            try:
                add_data_to_google_sheet(user_data)
                st.success("Your data has been saved.")
            except Exception as e:
                st.error(f"An error occurred while saving your data: {e}")
            # Generate PDF
            pdf_output = generate_pdf()
            st.session_state.pdf_output = pdf_output
            st.session_state.form_submitted = True
            st.success("Your report is ready for download.")
        else:
            st.error("Please fill in all the contact information fields before downloading the report.")

# Display the download button if the form has been submitted
if st.session_state.form_submitted and st.session_state.pdf_output:
    st.download_button(
        label="Click here to download your report",
        data=st.session_state.pdf_output,
        file_name="strategy_report.pdf",
        mime="application/pdf"
    )

# Download button for the report in PDF format
def generate_pdf():
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Add the background image to the top 40% of the page
    background_height = height * 0.4
    c.drawImage(background_image_path, 0, height - background_height, width=width, height=background_height, mask='auto')

    # Add the logo on the right side below the background image
    logo_width = 157.5  # Increased by 5%
    logo_height = 60
    c.drawImage(logo_path, width - logo_width - 30, height - background_height - logo_height - 10, width=logo_width, height=logo_height, mask='auto')

    # Add the heading on the left side below the logo
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(30, height - background_height - logo_height - 40, "Tailored AI Strategy Report")

    # Decrease gap after heading by 5%
    gap_after_heading = 40 * 0.95

    # Add the statement with chosen inputs and wrap text to stay within page edges
    c.setFont("Helvetica-Bold", 14)
    y_position = height - background_height - logo_height - gap_after_heading - 80
    statement_parts = [
        ("Our R&D Transformation goal is to ", colors.black),
        (goal, colors.HexColor('#E96C25')),
        (", which will be accomplished by ", colors.black),
        (method, colors.HexColor('#E96C25')),
        (", through the strategic initiatives in ", colors.black),
        (tool, colors.HexColor('#E96C25')),
        (", and success will be evaluated by ", colors.black),
        (kpi, colors.HexColor('#E96C25')),
        (".", colors.black)
    ]

    x_position = 30
    max_width = width - 60  # Leave some margin on both sides
    for text, color in statement_parts:
        text_width = c.stringWidth(text, "Helvetica-Bold", 14)
        if x_position + text_width > max_width:
            y_position -= 20
            x_position = 30
        c.setFillColor(color)
        c.drawString(x_position, y_position, text)
        x_position += text_width

    # Add recommended use cases and partners
    y_position -= 40
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawString(30, y_position, "Recommended Use Cases:")
    y_position -= 20
    c.drawString(30, y_position, ', '.join(use_cases))

    y_position -= 40
    c.drawString(30, y_position, "Suitable Partners:")
    y_position -= 20
    c.drawString(30, y_position, ', '.join(partners))

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer
