import os
import streamlit as st
import google.generativeai as genai
from pathlib import Path
import tempfile
import PyPDF2
from PIL import Image
import io
from docx import Document
from typing import Optional, Tuple, Union, Dict, Any
import logging
from database_helper import DatabaseManager
import pickle

# Initialize database manager
db = DatabaseManager()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Configure Gemini API
def configure_api():
    """Configure the Gemini API with error handling"""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        st.error("Please set the GOOGLE_API_KEY environment variable")
        st.stop()
    genai.configure(api_key=api_key)


def read_image_file(file_path: str) -> Union[bytes, str]:
    """Read and process image file with error handling"""
    try:
        with Image.open(file_path) as image:
            # Convert image to RGB if it's not
            if image.mode != 'RGB':
                image = image.convert('RGB')
            # Create byte stream
            byte_stream = io.BytesIO()
            image.save(byte_stream, format='PNG')
            byte_stream.seek(0)
            return byte_stream.getvalue()
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return f"Error processing image: {str(e)}"


def read_file_content(file_path: str, file_type: str) -> Union[str, bytes]:
    """Read and return the content of different file types with enhanced error handling"""
    try:
        if file_type == "txt":
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        elif file_type == "pdf":
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return "\n".join(page.extract_text() for page in pdf_reader.pages)
        elif file_type == "docx":
            try:
                doc = Document(file_path)
                return "\n".join(paragraph.text for paragraph in doc.paragraphs)
            except ImportError:
                return "Error: python-docx package is not installed. Please install it using: pip install python-docx"
        elif file_type in ["jpg", "jpeg", "png"]:
            return read_image_file(file_path)
        else:
            return f"Error: Unsupported file type: {file_type}"
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return f"Error reading file: {str(e)}"


def process_uploaded_file(uploaded_file: Any) -> Tuple[Optional[Union[str, bytes]], Optional[str], Optional[int]]:
    """Process uploaded file and save to database"""
    if uploaded_file is None:
        return None, None, None

    try:
        file_type = uploaded_file.name.split('.')[-1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        content = read_file_content(tmp_file_path, file_type)

        try:
            os.unlink(tmp_file_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file: {e}")

        if isinstance(content, str) and content.startswith("Error"):
            return content, None, None

        # Save to database
        document_id = db.save_document(uploaded_file.name, file_type, content)

        return content, file_type, document_id

    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        return f"Error processing file: {str(e)}", None, None


def query_gemini_api(prompt: str, context: Optional[Union[str, bytes]] = None,
                     model_name: str = "gemini-pro") -> Dict[str, str]:
    """Query the Gemini API with enhanced error handling and rate limiting"""
    try:
        if isinstance(context, bytes):
            model = genai.GenerativeModel('gemini-pro-vision')
            image = {"mime_type": "image/jpeg", "data": context}  # Or appropriate mime type
            response = model.generate_content([prompt, image])
        else:
            model = genai.GenerativeModel(model_name)
            full_prompt = prompt if not context else f"""
            Context from uploaded file:
            {context}

            Query:
            {prompt}
            """
            response = model.generate_content(full_prompt)

        return {
            'status': 'success',
            'content': response.text
        }
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {
            'status': 'error',
            'content': f"Error communicating with AI model: {str(e)}"
        }


def analyze_query(query: str, file_content: Optional[Union[str, bytes]] = None,
                  file_type: Optional[str] = None) -> str:
    """Analyze the query and determine the most appropriate agent"""
    prompt = f"""
    Analyze this query and determine which specialized agent would be most appropriate.
    Query: {query}

    Choose from:
    1. Concept Clarification Agent - For explaining OOAD concepts, principles, and theoretical questions
    2. Code Snippet Generator Agent - For generating example code, implementation patterns, and coding solutions
    3. Design Assistant Agent - For system design, UML diagrams, and architectural recommendations

    Respond with only one of: "concept", "code", or "design"
    """

    if file_content:
        if isinstance(file_content, str):
            prompt += f"\nContext from document:\n{file_content[:1000]}..."
        else:
            prompt += "\nNote: Query includes an image file."

    response = query_gemini_api(prompt)
    return response['content'].strip().lower() if response['status'] == 'success' else "concept"


def get_agent_prompt(query: str, agent_type: str) -> str:
    """Generate appropriate prompt based on agent type"""
    prompts = {
        "concept": f"""
        Act as an OOAD expert. Explain the following concept clearly and concisely:
        {query}

        Provide:
        1. Clear definition with examples
        2. Key characteristics and principles
        3. Real-world applications
        4. Common misconceptions
        5. Best practices and pitfalls
        """,

        "code": f"""
        Generate a practical, production-ready implementation for this request:
        {query}

        Include:
        1. Complete, working code with error handling
        2. Step-by-step explanation of the implementation in java
        3. Best practices and potential pitfalls
        4. Usage examples and test cases
        5. Performance considerations
        """,
        "design": f"""
        Act as a senior software architect. Address this design request:
        {query}

        Provide:
        1. Comprehensive system design overview
        2. Key components and their interactions
        3. Design patterns and SOLID principles application
        4. Scalability and maintainability considerations
        5. Potential challenges and mitigation strategies
        """
    }
    return prompts.get(agent_type, prompts["concept"])


def display_response(response: Dict[str, str], agent_type: str):
    """Display the AI response with appropriate formatting"""
    if response['status'] == 'success':
        if agent_type == "code" and "```" in response['content']:
            # Split and display code blocks separately
            parts = response['content'].split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Non-code parts
                    if part.strip():
                        st.markdown(part)
                else:  # Code parts
                    st.code(part)
        else:
            st.markdown(response['content'])
    else:
        st.error(response['content'])


def document_analyzer_agent():
    """Document Analyzer Agent with database integration"""
    st.header("Document Analyzer")

    # Add back button
    if st.button("← Back to Main Interface"):
        st.session_state.doc_content = None
        st.session_state.doc_type = None
        st.session_state.file_name = None
        st.session_state.current_doc_id = None
        st.rerun()

    # Display document info
    doc_id = st.session_state.get('current_doc_id')
    if doc_id:
        document = db.get_document(doc_id)
        if document:
            st.info(f"Analyzing: {document['filename']}")

            if document['file_type'] in ["jpg", "jpeg", "png"]:
                st.image(document['content'], caption="Uploaded Image", use_column_width=True)

            # Get or perform initial analysis
            analysis = db.get_analysis(doc_id, 'initial')
            if not analysis:
                with st.spinner("Analyzing document..."):
                    analyze_prompt = """
                    Analyze this document and provide:
                    1. Brief content summary
                    2. Key topics and concepts identified
                    3. Relevant OOAD principles or patterns found
                    4. Suggested questions for deeper understanding
                    """
                    response = query_gemini_api(analyze_prompt, document['content'])
                    if response['status'] == 'success':
                        analysis = response['content']
                        db.save_analysis(doc_id, 'initial', analysis)

            st.markdown("### Document Analysis")
            st.markdown(analysis)

            # Query section
            st.markdown("### Ask Questions About the Document")
            query = st.text_input(
                "What would you like to know about this document?",
                placeholder="E.g., What are the main design patterns discussed?"
            )

            if st.button("Get Answer", disabled=not query):
                with st.spinner("Analyzing..."):
                    prompt = f"""
                    Based on the provided document content, please answer:
                    {query}

                    Provide a detailed and accurate answer using only the information 
                    from the document. If the answer requires OOAD expertise, include
                    relevant OOAD principles and best practices in the explanation.
                    """
                    response = query_gemini_api(prompt, document['content'])

                    if response['status'] == 'success':
                        # Save query and response
                        db.save_query(doc_id, query, response['content'], 'document_analysis')

                        st.markdown("### Answer")
                        st.markdown(response['content'])


def unified_query_interface():
    """Main query interface with database integration"""
    st.header("OOAD Intelligent Assistant")

    # Show recent documents
    recent_docs = db.get_recent_documents()
    if recent_docs:
        st.sidebar.markdown("### Recent Documents")

        if 'delete_document' not in st.session_state:
            st.session_state.delete_document = None

        for doc_id, filename, file_type, upload_date, _ in recent_docs:
            # Create a container for each document
            doc_container = st.sidebar.container()
            with doc_container:
                col1, col2 = st.columns([0.92, 0.08])

                # Document button in the main column
                with col1:
                    if st.button(f"📄 {filename}", key=f"doc_{doc_id}"):
                        st.session_state.doc_content = db.get_document(doc_id)['content']
                        st.session_state.doc_type = file_type
                        st.session_state.file_name = filename
                        st.session_state.current_doc_id = doc_id
                        st.rerun()

                # Delete button in the second column
                with col2:
                    if st.button("🗑️", key=f"delete_doc_{doc_id}"):
                        st.session_state.delete_document = doc_id
                        st.rerun()

    if st.session_state.delete_document is not None:
        try:
            if db.delete_document(st.session_state.delete_document):
                # If the deleted document was the current document, clear the session state
                if st.session_state.delete_document == st.session_state.get('current_doc_id'):
                    st.session_state.doc_content = None
                    st.session_state.doc_type = None
                    st.session_state.file_name = None
                    st.session_state.current_doc_id = None
            st.session_state.delete_document = None
            st.rerun()
        except Exception as e:
            st.error(f"Failed to delete document: {str(e)}")

    # Show recent queries in compact dropdown format
    recent_queries = db.get_recent_queries()
    if recent_queries:
        st.sidebar.markdown("### Recent Questions")

        # Initialize delete_query in session state if not present
        if 'delete_query' not in st.session_state:
            st.session_state.delete_query = None

        # Group queries by date
        current_date = None
        for query_id, query, response, agent_type, timestamp_str in recent_queries:
            try:
                date_part = timestamp_str.split()[0]
                time_part = timestamp_str.split()[1].split('.')[0]  # Remove microseconds if present
            except (IndexError, AttributeError):
                date_part = "Unknown Date"
                time_part = "Unknown Time"

            if current_date != date_part:
                if current_date is not None:
                    st.sidebar.markdown("---")
                current_date = date_part
                st.sidebar.caption(f":calendar: {date_part}")

            # Create a container for the query and delete button
            query_container = st.sidebar.container()
            with query_container:
                col1, col2 = st.columns([0.92, 0.08])

                # Query content in the main column
                with col1:
                    with st.expander(query[:50] + "..." if len(query) > 50 else query, expanded=False):
                        st.markdown(f"**Agent**: {agent_type}")
                        st.markdown(response)
                        st.caption(f"Asked at: {time_part}")

                # Delete button in the second column
                with col2:
                    if st.button("🗑️", key=f"delete_{query_id}"):
                        st.session_state.delete_query = query_id
                        st.rerun()

        # Handle deletion if delete button was clicked
        if st.session_state.delete_query is not None:
            try:
                db.delete_query(st.session_state.delete_query)
                st.session_state.delete_query = None
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete query: {str(e)}")

    # File upload section
    uploaded_file = st.file_uploader(
        "Upload a document to analyze:",
        type=["txt", "pdf", "docx", "jpg", "jpeg", "png"]
    )

    if uploaded_file:
        with st.spinner("Processing document..."):
            content, file_type, doc_id = process_uploaded_file(uploaded_file)
            if isinstance(content, str) and content.startswith("Error"):
                st.error(content)
            else:
                st.session_state.doc_content = content
                st.session_state.doc_type = file_type
                st.session_state.file_name = uploaded_file.name
                st.session_state.current_doc_id = doc_id
                st.rerun()
        return

    # Query section
    query = st.text_input(
        "Your question:",
        placeholder="E.g., What is encapsulation? OR Show me a Singleton pattern"
    )

    if st.button("Get Answer", disabled=not query):
        with st.spinner("Processing your query..."):
            try:
                agent_type = analyze_query(query)
                st.info(f"Query routed to: {agent_type.title()} Agent")

                prompt = get_agent_prompt(query, agent_type)
                response = query_gemini_api(prompt)

                if response['status'] == 'success':
                    # Save query and response
                    db.save_query(None, query, response['content'], agent_type)

                display_response(response, agent_type)

            except Exception as e:
                logger.error(f"Error in query processing: {e}")
                st.error(f"An error occurred while processing your query: {str(e)}")

def main():
    """Main application entry point with improved error handling"""
    try:
        st.set_page_config(
            page_title="OOAD Assistant",
            page_icon="🎯",
            layout="wide"
        )

        configure_api()

        # Initialize session state
        if 'doc_content' not in st.session_state:
            st.session_state.doc_content = None
            st.session_state.doc_type = None
            st.session_state.file_name = None
            st.session_state.delete_document = None

        st.title("Intelligent Multi-Agent AI Application for OOAD")

        if st.session_state.doc_content is not None:
            document_analyzer_agent()
        else:
            st.markdown("""
            Welcome to the OOAD Assistant! This application helps you with:
            - 📚 **Concept Understanding**: Clear explanations of OOAD principles
            - 💻 **Code Generation**: Production-ready implementation examples
            - 🎨 **Design Guidance**: Expert architectural recommendations
            - 📄 **Document Analysis**: Smart document processing and Q&A

            Get started by asking a question or uploading a document!
            """)

            unified_query_interface()

    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("An unexpected error occurred. Please try refreshing the page.")



if __name__ == "__main__":
    main()