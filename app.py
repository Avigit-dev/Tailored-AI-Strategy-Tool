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
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
from reportlab.lib.units import inch

# Add Sidebar Navigation
st.sidebar.title("Navigation")
app_mode = st.sidebar.selectbox("Choose the app mode", ["Strategy Tool", "Maturity Assessment"])

# Initialize session state variables
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'pdf_output' not in st.session_state:
    st.session_state.pdf_output = None
if 'assessment_submitted' not in st.session_state:
    st.session_state.assessment_submitted = False
if 'assessment_pdf' not in st.session_state:
    st.session_state.assessment_pdf = None
if 'contact_submitted' not in st.session_state:
    st.session_state.contact_submitted = False
if 'responses' not in st.session_state:
    st.session_state.responses = {}

# Load images
@st.cache_resource
def load_image(image_path):
    return Image.open(image_path)

background_image = load_image("Background_Tool.png")
logo_image = load_image("efeso_logo.png")

# Paths to images
background_image_path = "Background_Tool.png"
logo_path = "efeso_logo.png"

# Load the dynamic logic structure from an external JSON file
@st.cache_data
def load_dynamic_logic():
    with open('dynamic_logic_with_use_cases.json', 'r') as file:
        return json.load(file)

dynamic_logic_with_use_cases = load_dynamic_logic()

# Load the maturity assessment questions from an external JSON file
@st.cache_data
def load_maturity_questions():
    with open('maturity_questions.json', 'r') as file:
        return json.load(file)

maturity_questions = load_maturity_questions()

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

# Function to add data to Google Sheets for the Strategy Tool
def add_data_to_google_sheet(user_data):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["google_service_account"], scope
        )
        client = gspread.authorize(credentials)
        sheet = client.open("client_inputs_strategytoolrnd").sheet1

        if not sheet.get_all_values():
            headers = list(user_data.keys())
            sheet.append_row(headers)

        sheet.append_row(list(user_data.values()))
        return True
    except Exception as e:
        st.error(f"An error occurred while saving your data: {e}")
        print(f"Error while saving data: {e}")
        return False

# Function to add data to Google Sheets for the Maturity Assessment
def add_assessment_data_to_google_sheet(user_data):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["google_service_account"], scope
        )
        client = gspread.authorize(credentials)
        sheet = client.open("Maturity_Assessment_Responses").worksheet("AssessmentData")

        if not sheet.get_all_values():
            headers = list(user_data.keys())
            sheet.append_row(headers)

        sheet.append_row(list(user_data.values()))
        return True
    except Exception as e:
        st.error(f"An error occurred while saving your data: {e}")
        print(f"Error while saving data: {e}")
        return False

# Generate PDF functions (unchanged)
def generate_pdf(goal, method, tool, kpi, use_cases, partners):
    # Your existing generate_pdf implementation
    pass

def generate_assessment_pdf(responses, user_info):
    # Your existing generate_assessment_pdf implementation
    pass

# Strategy Tool Module (unchanged)
def strategy_tool():
    # Your existing strategy_tool implementation
    pass

# Maturity Assessment Module (Fixed version)
def maturity_assessment():
    st.title("Maturity Assessment")

    # Load and display images
    st.image(background_image, use_column_width=True)
    st.image(logo_image, use_column_width=False, width=300)

    scale = maturity_questions['scale']

    # Display the questionnaire first if responses haven't been collected
    if not st.session_state.assessment_submitted:
        with st.form(key="assessment_form", clear_on_submit=False):
            st.write("### Please complete the assessment")
            
            responses = {}
            for topic in maturity_questions['topics']:
                st.header(topic['name'])
                for question in topic['questions']:
                    q_id = question['id']
                    st.write(question['question'])
                    response = st.radio(
                        label=f"Question {q_id}",  # Providing a non-empty label
                        options=[1, 2, 3, 4, 5],
                        format_func=lambda x: f"{x} - {scale[str(x)]}",
                        key=f"q_{q_id}",
                        horizontal=True
                    )
                    responses[q_id] = response
            
            submit_assessment = st.form_submit_button("Submit Assessment")
            if submit_assessment:
                st.session_state.responses = responses
                st.session_state.assessment_submitted = True
                st.rerun()

    # After assessment is submitted, show contact form if contact info hasn't been submitted
    elif not st.session_state.contact_submitted:
        st.write("### Please provide your contact information to view your results and download the report")
        with st.form(key="contact_form", clear_on_submit=False):
            name = st.text_input("Full Name", key="name")
            email = st.text_input("Email Address", key="email")
            company = st.text_input("Company Name", key="company")
            phone = st.text_input("Phone Number", key="phone")
            
            submit_contact = st.form_submit_button("Submit Contact Information")
            if submit_contact:
                if name and email and company and phone:
                    # Prepare data for saving
                    user_data = {
                        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'Name': name,
                        'Email': email,
                        'Company': company,
                        'Phone': phone,
                        **st.session_state.responses
                    }
                    
                    # Save to Google Sheets
                    if add_assessment_data_to_google_sheet(user_data):
                        # Generate the PDF report
                        pdf_output = generate_assessment_pdf(st.session_state.responses, {
                            'Name': name,
                            'Email': email,
                            'Company': company,
                            'Phone': phone
                        })
                        st.session_state.assessment_pdf = pdf_output
                        st.session_state.contact_submitted = True
                        st.rerun()
                else:
                    st.error("Please fill in all the contact information fields.")

    # After both assessment and contact info are submitted, show download option
    else:
        st.success("Thank you for completing the assessment!")
        if st.session_state.assessment_pdf is not None:
            st.download_button(
                label="Download Assessment Report",
                data=st.session_state.assessment_pdf,
                file_name="maturity_assessment_report.pdf",
                mime="application/pdf"
            )
        
        # Add a reset button
        if st.button("Start New Assessment"):
            for key in ['assessment_submitted', 'contact_submitted', 'responses', 'assessment_pdf']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# Main application logic
if app_mode == "Strategy Tool":
    strategy_tool()
elif app_mode == "Maturity Assessment":
    maturity_assessment()