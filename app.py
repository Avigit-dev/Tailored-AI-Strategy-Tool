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
        # Open your Google Sheet by name
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

# Generate PDF functions for Strategy Tool and Maturity Assessment
def generate_pdf(goal, method, tool, kpi, use_cases, partners):
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

def generate_assessment_pdf(responses, user_info):
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Add the background image to the top of the page
    background_height = height * 0.4
    c.drawImage(background_image_path, 0, height - background_height, width=width, height=background_height, mask='auto')

    # Add the logo in the top-right corner
    logo_width = 157.5
    logo_height = 60
    c.drawImage(logo_path, width - logo_width - 30, height - background_height - logo_height - 10, width=logo_width, height=logo_height, mask='auto')

    # Add the heading below the logo
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(30, height - background_height - logo_height - 40, "Maturity Assessment Report")

    # Add user information
    y_position = height - background_height - logo_height - 60
    c.setFont("Helvetica", 12)
    for key, value in user_info.items():
        c.drawString(30, y_position, f"{key}: {value}")
        y_position -= 20

    # Add histograms for each topic
    for topic in maturity_questions['topics']:
        c.showPage()  # Start a new page for each topic
        topic_name = topic['name']
        topic_questions = topic['questions']
        
        # Generate the histogram plot
        question_numbers = [q['id'] for q in topic_questions]
        maturity_levels = [responses[q_id] for q_id in question_numbers]
        
        plt.figure(figsize=(8, 4))
        plt.bar(question_numbers, maturity_levels, color='#E96C25')
        plt.xlabel("Question Number")
        plt.ylabel("Maturity Level")
        plt.title(f"Maturity Levels for {topic_name}")
        
        # Save the plot to a temporary buffer and add it to the PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='PNG')
        plt.close()
        
        img_buffer.seek(0)
        c.drawImage(img_buffer, inch, height / 2, width=width - 2 * inch, preserveAspectRatio=True, anchor='c')
        
        # Add the topic title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30, height - 60, f"Topic: {topic_name}")
        
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

# Strategy Tool Module
def strategy_tool():
    # [Strategy Tool code remains exactly the same]
    # ... [Previous strategy_tool implementation]

# Maturity Assessment Module
def maturity_assessment():
    st.title("Maturity Assessment")

    # Load and display images
    st.image(background_image, use_column_width=True)
    st.image(logo_image, use_column_width=False, width=300)

    scale = maturity_questions['scale']

    # Check if assessment is already submitted
    if not st.session_state.assessment_submitted:
        # Create assessment form
        with st.form(key="maturity_assessment_form"):
            st.write("### Please fill in your contact information")
            name = st.text_input("Full Name", key="name")
            email = st.text_input("Email Address", key="email")
            company = st.text_input("Company Name", key="company")
            phone = st.text_input("Phone Number", key="phone")

            st.write("### Assessment Questions")
            for topic in maturity_questions['topics']:
                st.subheader(topic['name'])
                for question in topic['questions']:
                    q_id = question['id']
                    st.write(question['question'])
                    response = st.radio(
                        f"Select maturity level for question {q_id}",
                        options=[1, 2, 3, 4, 5],
                        format_func=lambda x: f"{x} - {scale[str(x)]}",
                        key=f"q_{q_id}"
                    )
                    st.session_state.responses[q_id] = response

            submit_button = st.form_submit_button("Submit Assessment")

            if submit_button:
                if name and email and company and phone:
                    # Prepare user data
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
                        # Generate PDF report
                        pdf_output = generate_assessment_pdf(
                            st.session_state.responses,
                            {
                                'Name': name,
                                'Email': email,
                                'Company': company,
                                'Phone': phone
                            }
                        )
                        st.session_state.assessment_pdf = pdf_output
                        st.session_state.assessment_submitted = True
                        st.success("Assessment submitted successfully!")
                    else:
                        st.error("Failed to save assessment data.")
                else:
                    st.error("Please fill in all contact information fields.")

    # Show download button if assessment is submitted
    if st.session_state.assessment_submitted and st.session_state.assessment_pdf is not None:
        st.success("Your assessment has been completed!")
        st.download_button(
            label="Download Assessment Report",
            data=st.session_state.assessment_pdf,
            file_name="maturity_assessment_report.pdf",
            mime="application/pdf"
        )

# Main application logic
if app_mode == "Strategy Tool":
    strategy_tool()
elif app_mode == "Maturity Assessment":
    maturity_assessment()
