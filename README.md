# OOAD Intelligent Multi-Agent Assistant 🎯

An advanced AI-powered application designed to assist with Object-Oriented Analysis and Design (OOAD) concepts, implementations, and document analysis. The system utilizes multiple specialized agents to provide comprehensive support for OOAD-related tasks.

## Features

### 1. Specialized Agents 🤖

- **Concept Clarification Agent**: Explains OOAD concepts, principles, and theoretical questions
- **Code Snippet Generator Agent**: Generates example code, implementation patterns, and coding solutions
- **Design Assistant Agent**: Provides system design guidance, UML diagrams, and architectural recommendations
- **Document Analyzer Agent**: Processes and analyzes uploaded documents with OOAD-specific insights

### 2. Document Management 📄

- Supports multiple file formats:
  - Text files (.txt)
  - PDF documents (.pdf)
  - Word documents (.docx)
  - Images (.jpg, .jpeg, .png)
- Automatic document analysis and content extraction
- Persistent storage of documents and analyses
- Document version tracking and management

### 3. Query Management 💬

- Intelligent query routing to appropriate specialized agents
- Context-aware responses based on uploaded documents
- History tracking of queries and responses
- Quick access to recent queries and their results

### 4. Interactive Interface 🖥️

- Clean, user-friendly Streamlit interface
- Real-time response generation
- Document upload and management capabilities
- Comprehensive query history with deletion functionality

## Technical Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.x
- **Database**: SQLite
- **AI Integration**: Google's Generative AI (Gemini)
- **Document Processing**: 
  - PyPDF2 for PDF processing
  - python-docx for Word documents
  - Pillow for image processing

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/vakes/OOAD_Agent.git
   cd OOAD_Agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   export GOOGLE_API_KEY='your_api_key_here'  # On Windows: set GOOGLE_API_KEY=your_api_key_here
   ```

## Usage

1. Start the application:
   ```bash
   streamlit run app.py
   ```

2. Access the web interface through your browser (typically http://localhost:8501)

3. You can:
   - Ask OOAD-related questions directly
   - Upload documents for analysis
   - View and manage document history
   - Track query history

## Project Structure

```
OOAD_Agent/
├── app.py                 # Main application file
├── database_helper.py     # Database management and operations
├── ooad_assistant.db     # SQLite database file
├── .venv/                # Virtual environment
└── __pycache__/         # Python cache files
```

## Features in Detail

### Query Processing

- Automatic agent selection based on query content
- Context-aware responses incorporating document content
- Persistent storage of queries and responses
- Query categorization and routing

### Document Analysis

- Automatic content extraction from various file formats
- Initial document analysis for OOAD concepts and patterns
- Context-aware question answering based on document content
- Document metadata tracking and management

### Database Management

- SQLite-based persistent storage
- Document content and metadata storage
- Query and response history
- Analysis results storage and retrieval
