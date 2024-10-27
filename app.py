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
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'topic_selection'
if 'selected_topics' not in st.session_state:
    st.session_state.selected_topics = set()
if 'completed_topics' not in st.session_state:
    st.session_state.completed_topics = set()
if 'show_dialog' not in st.session_state:
    st.session_state.show_dialog = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

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

# Generate PDF functions for Strategy Tool
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


# Generate PDF functions for Maturity Assessment
def generate_assessment_pdf(responses, user_info, y_axis_range):
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))  # Set landscape orientation
    width, height = landscape(A4)  # Get dimensions for landscape

    # Define logo dimensions and margins
    logo_width = 157.5
    logo_height = 60
    logo_margin_right = 30
    logo_margin_top = 20

    # Add the cover page without calling c.showPage()
    # Add the background image to the top of the cover page
    background_height = height * 0.4
    c.drawImage(background_image_path, 0, height - background_height, width=width, height=background_height, mask='auto')

    # Add the logo on the right side below the background image
    logo_position_y = height - background_height - logo_height - 30
    c.drawImage(logo_path, width - logo_width - logo_margin_right, logo_position_y, width=logo_width, height=logo_height, mask='auto')

    # Add the main title for the cover page
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.black)
    c.drawString(30, logo_position_y - 40, "Maturity Assessment Report")

    # Add user information on the cover page
    y_position = logo_position_y - 80
    c.setFont("Helvetica", 12)
    for key, value in user_info.items():
        c.drawString(30, y_position, f"{key}: {value}")
        y_position -= 20

    # Generate pages for each completed topic
    for topic_name in st.session_state.completed_topics:
        # Find the topic details
        topic = next((t for t in maturity_questions['topics'] if t['name'] == topic_name), None)
        if not topic:
            continue  # Skip if topic not found

        c.showPage()  # Start a new page
        topic_questions = topic['questions']

        # Add the logo at the top-right corner of each page
        c.drawImage(logo_path, width - logo_width - logo_margin_right, height - logo_height - logo_margin_top,
                    width=logo_width, height=logo_height, mask='auto')

        # Add the topic name as the page title
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.black)
        c.drawString(30, height - 60, f"Topic: {topic_name}")

        # Define question numbers and maturity levels based on the responses
        question_numbers = [f"Q{i+1}" for i in range(len(topic_questions))]
        maturity_levels = [responses.get(q['id'], 0) for q in topic_questions]

        # Set up the user session plot
        plt.figure(figsize=(4, 4))
        plt.subplots_adjust(left=0.2, right=0.8, bottom=0.3, top=0.8)

        # Set y-axis ticks with user-defined range
        plt.yticks(range(y_axis_range[0], y_axis_range[1] + 1))

        # Create bar plot with question numbers and maturity levels
        plt.bar(question_numbers, maturity_levels, color='#E96C25')
        plt.xlabel("Question Number")
        plt.ylabel("Maturity Level")
        plt.title(f"User Session Data - {topic_name}", fontsize=10, pad=20)

        # Save the user session plot to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            plt.savefig(tmp_file.name, format='PNG')
            user_plot_path = tmp_file.name
        plt.close()

        # Adjust the y-coordinate for the plot
        plot_margin_top = 100
        plot_height = height * 0.5
        plot_width = width * 0.45

        # Draw the user session plot on the left half of the page
        c.drawImage(user_plot_path, 30, height - plot_margin_top - plot_height,
                    width=plot_width, height=plot_height, preserveAspectRatio=True, mask='auto')

        # Remove the temporary file for the plot
        os.remove(user_plot_path)

        # Placeholder for the right half of the page
        placeholder_x = width / 2 + 30
        placeholder_y = height - plot_margin_top - plot_height
        c.setFillColor(colors.lightgrey)
        c.rect(placeholder_x, placeholder_y, plot_width, plot_height, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 12)
        c.drawString(placeholder_x + 10, placeholder_y + plot_height - 20, "Placeholder for Historical Data")

        # Add the legend below the plots
        legend_labels = [f"{question_numbers[i]} - {topic_questions[i]['question']}" for i in range(len(topic_questions))]
        legend_text = "\n".join(legend_labels)

        # Adjust y_position to place the legend
        legend_y_position = height - plot_margin_top - plot_height - 40
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        for line in legend_text.split("\n"):
            if legend_y_position < 50:  # Ensure the legend fits within the page
                break
            c.drawString(30, legend_y_position, line)
            legend_y_position -= 15

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer


# New helper functions for maturity assessment
def create_topic_tile(topic_name: str, description: str):
    # Create a clickable tile with consistent styling and fixed height
    tile_style = f"""
        <div style='
            background-color: #E96C25;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 10px;
            cursor: pointer;
            text-align: center;
            height: 200px;  /* Set a fixed height */
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: transform 0.2s;
        ' onclick='handle_tile_click("{topic_name}")'>
            <h3>{topic_name}</h3>
            <p style='font-size: 0.9em;'>{description}</p>
        </div>
    """
    return tile_style


def get_topic_description(topic_name: str) -> str:
    # Add descriptions for each topic
    descriptions = {
        "ERP Harmonization": "Assessment of your organization's ERP system unification and standardization efforts across departments and regions.",
        "Standardization of Processes": "Evaluation of business process documentation, standardization, and implementation across the organization.",
        "Integration Across Departments and Regions": "Analysis of cross-departmental collaboration and regional alignment with corporate processes.",
        "Optimization of Capex": "Assessment of capital expenditure planning, prioritization, and management processes.",
        "Improvement of Opex": "Evaluation of operational expense tracking, optimization, and cost reduction initiatives.",
        "KPI Monitoring and Management": "Analysis of KPI definition, monitoring, and utilization for decision-making processes."
    }
    return descriptions.get(topic_name, "Assess your organization's maturity in this area.")

def display_topic_tiles():
    st.title("Maturity Assessment Topics")
    st.write("Select a topic to begin its assessment:")
    
    # Get all topics
    topics = maturity_questions['topics']
    num_cols = 3  # Number of columns in the grid
    num_rows = (len(topics) + num_cols - 1) // num_cols  # Calculate the number of rows needed
    
    # Create a grid layout
    for row in range(num_rows):
        cols = st.columns(num_cols)
        for col_idx in range(num_cols):
            topic_idx = row * num_cols + col_idx
            if topic_idx < len(topics):
                topic = topics[topic_idx]
                topic_name = topic['name']
                with cols[col_idx]:
                    # Display the tile
                    st.markdown(
                        create_topic_tile(
                            topic_name,
                            get_topic_description(topic_name)
                        ),
                        unsafe_allow_html=True
                    )
                    
                    # Hidden button to capture clicks on the tile
                    if st.button(f"Select {topic_name}", key=f"btn_{topic_name}", 
                                 help="Click to start assessment"):
                        st.session_state.show_dialog = topic_name
                        
                    # If this topic is selected, display the dialog here
                    if st.session_state.show_dialog == topic_name:
                        # Reset the dialog state if needed
                        st.session_state.show_dialog = None
                        
                        # Display the dialog under the tile
                        with st.expander(f"Start Assessment for {topic_name}", expanded=True):
                            st.write(get_topic_description(topic_name))
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Start Assessment", key=f"start_{topic_name}"):
                                    st.session_state.current_page = 'assessment'
                                    st.session_state.current_topic = topic_name
                                    st.session_state.show_dialog = None  # Reset the dialog
                                    st.experimental_rerun()
                            with col2:
                                if st.button("Close", key=f"close_{topic_name}"):
                                    st.session_state.show_dialog = None
                                    st.experimental_rerun()


def display_topic_dialog():
    if st.session_state.show_dialog:
        topic_name = st.session_state.show_dialog
        with st.expander(topic_name, expanded=True):
            st.write(get_topic_description(topic_name))
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start Assessment", key=f"start_{topic_name}"):
                    st.session_state.current_page = 'assessment'
                    st.session_state.current_topic = topic_name
                    st.rerun()
            with col2:
                if st.button("Close", key=f"close_{topic_name}"):
                    st.session_state.show_dialog = None
                    st.rerun()

def display_topic_assessment(topic_name: str):
    st.title(f"{topic_name} Assessment")
    
    # Get questions for current topic
    topic_questions = next(
        (topic for topic in maturity_questions['topics'] 
         if topic['name'] == topic_name), 
        None
    )
    
    if not topic_questions:
        st.error(f"No questions found for topic: {topic_name}")
        return
    
    # Display user information form if not already filled
    if not st.session_state.user_info:
        with st.form("user_info_form"):
            st.write("### Please fill in your contact information")
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            company = st.text_input("Company Name")
            phone = st.text_input("Phone Number")
            
            if st.form_submit_button("Continue to Assessment"):
                if all([name, email, company, phone]):
                    st.session_state.user_info = {
                        'Name': name,
                        'Email': email,
                        'Company': company,
                        'Phone': phone
                    }
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")
    else:
        # Display assessment questions
        with st.form(key=f"assessment_form_{topic_name}"):
            st.write("### Assessment Questions")
            for question in topic_questions['questions']:
                q_id = question['id']
                st.write(question['question'])
                response = st.radio(
                    f"Select maturity level for question {q_id}",
                    options=[1, 2, 3, 4, 5],
                    format_func=lambda x: f"{x} - {maturity_questions['scale'][str(x)]}",
                    key=f"q_{q_id}"
                )
                st.session_state.responses[q_id] = response
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Submit and Continue to Other Topics"):
                    st.session_state.completed_topics.add(topic_name)
                    st.session_state.current_page = 'topic_selection'
                    st.rerun()
            with col2:
                if st.form_submit_button("Submit and Generate Final Report"):
                    st.session_state.completed_topics.add(topic_name)
                    generate_final_report()

def generate_final_report():
    if not st.session_state.completed_topics:
        st.error("Please complete at least one topic assessment before generating the report.")
        return

    # Generate PDF report only for completed topics
    pdf_output = generate_assessment_pdf(
        st.session_state.responses,
        st.session_state.user_info,
        (0, 5)
    )

    # Ensure we have a valid PDF output
    if pdf_output is None:
        st.error("Failed to generate the PDF report.")
        return

     # Debugging statement to confirm PDF generation
    st.write("PDF successfully generated, ready for download.")  # <-- Add this line here

    # Save to Google Sheets
    user_data = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **st.session_state.user_info,
        **st.session_state.responses
    }

    if add_assessment_data_to_google_sheet(user_data):
        st.session_state.assessment_pdf = pdf_output  # Store the entire buffer, not just the byte value
        st.session_state.assessment_submitted = True
        st.success("Assessment completed! You can now download your report.")
    else:
        st.error("Failed to save assessment data.")


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
            data=st.session_state.pdf_output.getvalue(),  # Extract byte content here
            file_name="strategy_report.pdf",
            mime="application/pdf"
        )


# Modified maturity_assessment function
def maturity_assessment():
    # Load and display images
    st.image(background_image, use_column_width=True)
    st.image(logo_image, use_column_width=False, width=300)
    
    # Handle different pages in the assessment flow
    if st.session_state.current_page == 'topic_selection':
        display_topic_tiles()
        display_topic_dialog()
        
        # Show option to generate final report if any topics completed
        if st.session_state.completed_topics:
            st.write("---")
            st.write("### Completed Assessments")
            st.write(f"You have completed assessments for: {', '.join(st.session_state.completed_topics)}")
            if st.button("Generate Final Report"):
                generate_final_report()
                
    elif st.session_state.current_page == 'assessment':
        display_topic_assessment(st.session_state.current_topic)
        
        # Add back button
        if st.button("Back to Topics"):
            st.session_state.current_page = 'topic_selection'
            st.rerun()
    
    # Move the download button code here to display it at the bottom
    if st.session_state.assessment_submitted:
        pdf_output = st.session_state.assessment_pdf  # Use the stored PDF output
        if pdf_output:
            st.download_button(
                label="Download Assessment Report",
                data=pdf_output.getvalue(),
                file_name="maturity_assessment_report.pdf",
                mime="application/pdf"
            )


# Main application logic
if app_mode == "Strategy Tool":
    strategy_tool()
elif app_mode == "Maturity Assessment":
    maturity_assessment()
