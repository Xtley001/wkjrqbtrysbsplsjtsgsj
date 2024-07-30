import streamlit as st
import google.generativeai as genai
import os
import PyPDF2 as pdf
from docx import Document
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to get response from Gemini API
def get_gemini_response(input_text):
    model = genai.GenerativeModel('gemini-pro')
    try:
        response = model.generate_content(input_text)
        if response and response.text:
            return response.text
        else:
            st.error("Received an empty response from the model.")
            return "{}"  # Return empty JSON
    except Exception as e:
        st.error(f"Error while getting response from API: {str(e)}")
        return "{}"  # Return empty JSON

# Function to extract text from uploaded PDF file
def input_pdf_text(uploaded_file):
    reader = pdf.PdfReader(uploaded_file)
    text = []
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text.append(page.extract_text())
    return text

# Function to extract text from uploaded Word document
def input_word_text(uploaded_file):
    doc = Document(uploaded_file)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return text

# Function to split text into manageable chunks
def split_text(text, max_chunk_size=2000):
    """Split text into chunks with a maximum size."""
    chunks = []
    while len(text) > max_chunk_size:
        chunk = text[:max_chunk_size]
        text = text[max_chunk_size:]
        chunks.append(chunk)
    chunks.append(text)
    return chunks

# Prompt Template for generating explanations, examples, and mini tests
input_prompts = {
    "Mathematics": """
    You are an expert in mathematics. Your task is to explain the content on the given page, provide a relevant example, and create a mini test with solutions.
    
    Page Content: {page_content}
    
    I want the response in the following structured format:
    {{"Explanation": "", "Example": "", "Mini Test": "", "Test Solution": ""}}
    """,
    "Statistics": """
    You are an expert in statistics. Your task is to explain the content on the given page, provide a relevant example, and create a mini test with solutions.
    
    Page Content: {page_content}
    
    I want the response in the following structured format:
    {{"Explanation": "", "Example": "", "Mini Test": "", "Test Solution": ""}}
    """,
    "Computer Science": """
    You are an expert in computer science. Your task is to explain the content on the given page, provide a relevant example, and create a mini test with solutions.
    
    Page Content: {page_content}
    
    I want the response in the following structured format:
    {{"Explanation": "", "Example": "", "Mini Test": "", "Test Solution": ""}}
    """
}

# Streamlit App
st.set_page_config(page_title="Interactify")
st.title("Interactify")

# Dropdown for subject selection
subject = st.selectbox("Select Subject", ["Mathematics", "Statistics", "Computer Science"])

# File uploader for slides (PDF, Word, or text) input
uploaded_file = st.file_uploader("Upload Your Document (PDF, DOCX, TXT)...", type=["pdf", "docx", "txt"])

# Text area for user question
user_question = st.text_area("Type your question about the document content:")

# Text input for page range
page_range_input = st.text_input("Enter page ranges (e.g., 78-79):")

# Initialize session state for history
if 'history' not in st.session_state:
    st.session_state.history = []

# Submit button for processing the document
submit = st.button("Submit")

if submit:
    if uploaded_file:
        try:
            # Extract text from the uploaded file
            if uploaded_file.type == "application/pdf":
                document_text = input_pdf_text(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                document_text = input_word_text(uploaded_file)
            elif uploaded_file.type == "text/plain":
                document_text = uploaded_file.read().decode("utf-8").split('\n')
            else:
                st.error("Unsupported file type!")
                st.stop()

            # Process page ranges
            page_ranges = []
            if page_range_input:
                try:
                    ranges = page_range_input.split(',')
                    for r in ranges:
                        start, end = map(int, r.split('-'))
                        page_ranges.append(range(start - 1, end))
                except ValueError:
                    st.error("Invalid page range format! Use the format 'start-end'.")
                    st.stop()
            else:
                page_ranges = [range(len(document_text))]

            # Process selected pages
            generated_content = []
            st.markdown("### Generated Content:")
            
            for range_set in page_ranges:
                for page_num in range_set:
                    if page_num < len(document_text):
                        st.markdown(f"#### Page {page_num + 1}")
                        page_content = document_text[page_num]

                        # Prepare prompt with extracted page text
                        input_prompt = input_prompts[subject]
                        input_prompt_filled = input_prompt.format(page_content=page_content)
                        
                        # Get response from Gemini API
                        response = get_gemini_response(input_prompt_filled)
                        
                        # Display raw response for debugging
                        st.markdown("**Raw Response:**")
                        st.write(response)
                        
                        try:
                            # Parse response
                            response_json = json.loads(response)
                            
                            # Display and collect Explanation, Example, Mini Test, and Test Solution
                            explanation = response_json.get("Explanation", "No explanation available.")
                            example = response_json.get("Example", "No example available.")
                            mini_test = response_json.get("Mini Test", "No mini test available.")
                            test_solution = response_json.get("Test Solution", "No test solution available.")
                            
                            st.markdown("**Explanation:**")
                            st.write(explanation)
                            
                            st.markdown("**Example:**")
                            st.write(example)
                            
                            st.markdown("**Mini Test:**")
                            st.write(mini_test)
                            
                            st.markdown("**Test Solution:**")
                            st.write(test_solution)
                            
                            # Collect generated content in JSON format
                            page_content_json = {
                                "Page": page_num + 1,
                                "Explanation": explanation,
                                "Example": example,
                                "Mini Test": mini_test,
                                "Test Solution": test_solution
                            }
                            generated_content.append(page_content_json)
                        except json.JSONDecodeError:
                            st.error("Failed to decode JSON response from the model.")
                        
                    else:
                        st.warning(f"Page {page_num + 1} is out of range.")
            
            # Add generated content to history
            st.session_state.history.append(generated_content)
            
            # Provide option to copy generated content
            st.markdown("### Copy Generated Content")
            generated_content_str = json.dumps(generated_content, indent=4)
            st.code(generated_content_str)
            if st.button("Copy to Clipboard"):
                st.experimental_set_query_params(text=generated_content_str)
                st.success("Content copied to clipboard!")

            # Process user question
            if user_question:
                question_prompt = f"Based on the content of the document, answer the following question:\n{user_question}"
                response = get_gemini_response(question_prompt)
                st.markdown("### Answer to Your Question:")
                st.write(response)
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
    else:
        st.warning("Please upload your document.")

# Display history
if st.session_state.history:
    st.markdown("### History")
    for i, content in enumerate(st.session_state.history, start=1):
        with st.expander(f"History {i}"):
            st.json(content)

# Footer
st.markdown("---")
st.markdown("© 2024 by Christley")
