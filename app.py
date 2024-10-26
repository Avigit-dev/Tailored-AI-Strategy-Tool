import os
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
import tempfile

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

# Generate PDF functions for Strategy Tool and Maturity Assessment
def generate_assessment_pdf(responses, user_info, y_axis_range):
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))  # Set landscape orientation
    width, height = landscape(A4)  # Get dimensions for landscape

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
        c.showPage()
        topic_name = topic['name']
        topic_questions = topic['questions']

        # Define question numbers and maturity levels based on the responses
        question_numbers = [f"Q{i+1}" for i in range(len(topic_questions))]
        maturity_levels = [responses[q['id']] for q in topic_questions]

        plt.figure(figsize=(8, 4))
        plt.subplots_adjust(left=0.2, right=0.8, bottom=0.2, top=0.8)

        # Set y-axis ticks with user-defined range
        plt.yticks(range(y_axis_range[0], y_axis_range[1] + 1))

        # Create bar plot with question numbers and maturity levels
        plt.bar(question_numbers, maturity_levels, color='#E96C25')
        plt.xlabel("Question Number")
        plt.ylabel("Maturity Level")

        # Set x-axis labels
        plt.xticks(rotation=45, ha="right")

        # Add the topic title to the plot
        plt.title(f"Maturity Levels for {topic_name}")

        # Add legend for each question
        legend_labels = [q['question'] for q in topic_questions]
        plt.legend(legend_labels, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            plt.savefig(tmp_file.name, format='PNG')
            tmp_file_path = tmp_file.name
        plt.close()

        # Center the plot image (both horizontally and vertically)
        image_height = width * 0.8 * (height / width)
        y_coordinate = (height - image_height) / 2
        c.drawImage(tmp_file_path, width * 0.1, y_coordinate, width=width * 0.8, preserveAspectRatio=True, anchor='c')

        os.remove(tmp_file_path)

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

# Strategy Tool Module
def strategy_tool():
    # Load and display the background image
    st.image(background_image, use_column_width=True)

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
    else:
        st.warning("Please select a goal.")
        return

    # Static text
    st.markdown("<div class='dropdown-text'>through the strategic initiatives in</div>", unsafe_allow_html=True)

    # Dropdown for tools based on method selection
    if method:
        tools, use_cases, partners = get_tools_and_use_cases(goal, method)
        tool = st.selectbox('', tools, label_visibility='collapsed')
    else:
        st.warning("Please select a method.")
        return

    # Static text
    st.markdown("<div class='dropdown-text'>and success will be evaluated by</div>", unsafe_allow_html=True)
    if tool:
        kpi = st.selectbox('', dynamic_logic_with_use_cases[goal]['kpis'], label_visibility='collapsed')
    else:
        st.warning("Please select a tool.")
        return

    # Close the horizontal layout for dropdowns
    st.markdown("</div>", unsafe_allow_html=True)

    # Display use cases and partners based on selections
    st.write(f"### Recommended Use Cases for {goal}:")
    st.write(f"**Use Cases**: {', '.join(use_cases)}")

    st.write(f"### Suitable Partners:")
    st.write(f"**Partners**: {', '.join(partners)}")

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
                print(f"Error: {e}")
            # Generate PDF
            pdf_output = generate_pdf(goal, method, tool, kpi, use_cases, partners)
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
                        # Define the y-axis range for the assessment report
                        y_axis_range = (0, 5)  # Fixed range for maturity levels from 0 to 5

                        # Generate PDF report
                        pdf_output = generate_assessment_pdf(
                            st.session_state.responses,
                            {
                                'Name': name,
                                'Email': email,
                                'Company': company,
                                'Phone': phone
                            },
                            y_axis_range  # Pass the y_axis_range as the third argument
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
