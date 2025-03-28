# Faved POC - Influencer Submission Evaluator

A modern web application for evaluating influencer submissions against brand briefs using AI. The system provides instant feedback on text scripts, images, and YouTube videos using OpenAI's GPT-4 and CLIP models.

## Core Features

- **Modern Web Interface**: Clean, responsive UI built with Next.js and styled-components
- **Real-time Evaluation**: Instant feedback with engaging loading states and clear results display
- **Multi-format Support**:
  - Text scripts and content
  - Images from Milanote boards
  - YouTube videos with automatic transcript analysis
- **AI-Powered Analysis**:
  - GPT-4 for detailed content evaluation
  - CLIP for image understanding
  - Semantic search for brief matching
- **Vector Database**: Pinecone for efficient content matching and retrieval

## Tech Stack

- **Frontend**: Next.js, TypeScript, styled-components
- **Backend**: FastAPI, Python 3.8+
- **AI/ML**: OpenAI GPT-4, CLIP, Embeddings
- **Database**: Pinecone Vector Database
- **APIs**: OpenAI, YouTube Transcript API

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.8+
- OpenAI API key
- Pinecone API key and environment
- uv (Python package installer)

### Environment Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/faved_poc.git
cd faved_poc
```

2. Set up the backend:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies using uv
cd backend
uv sync

# Create .env file in project root
echo "OPENAI_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=your_env_here" > ../.env
```

3. Set up the frontend:

```bash
cd frontend
npm install
```

### Data Setup

The system requires brand briefs to be available in the `data/brief` directory. The initialization process handles:

1. **Brief Summaries**: Automatically generates concise summaries of each brief
2. **Evaluation Prompts**: Creates standardized evaluation questions based on brief content
3. **Vector Store**: Initializes Pinecone with brief embeddings for semantic search

The system will automatically:

- Process briefs on first run
- Generate required files in `data/summaries/`
- Create evaluation prompts in `data/brief_prompt_questions.json`
- Initialize the Pinecone vector store

To reset the system:

```bash
# Remove generated files (if needed)
rm -f data/summaries/briefs_summaries.txt data/summaries/briefs_summaries.json data/brief_prompt_questions.json

# The system will regenerate everything on next startup
```

### Running the Application

1. Start the backend server:

```bash
cd backend
uvicorn main:app --reload
```

The backend will:

- Check configuration status
- Process briefs if needed (with progress indicators)
- Initialize the vector store
- Start the API server at http://localhost:8000

2. Start the frontend development server:

```bash
cd frontend
npm run dev
```

The web interface will be available at http://localhost:3000

## Testing the API Endpoints

You can test the API endpoints directly using the Swagger UI or curl:

### Swagger UI

Visit http://localhost:8000/docs for interactive API documentation and testing.

### Example API Calls

1. Text Evaluation:

```bash
curl -X POST http://localhost:8000/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your content here"}'
```

2. Image Evaluation:

```bash
curl -X POST http://localhost:8000/image \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://your-milanote-board-url"}'
```

3. Video Evaluation:

```bash
curl -X POST http://localhost:8000/video \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=example"}'
```

## Project Structure

```
.
├── frontend/               # Next.js frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   └── styles/       # Styled components
│   └── package.json
├── backend/               # FastAPI backend application
│   ├── api/              # API routes and handlers
│   ├── config.py         # Configuration management
│   ├── main.py          # FastAPI application setup
│   └── utils.py         # Shared utilities and initialization logic
├── data/                 # Data directory
│   ├── brief/           # Brand brief text files
│   └── summaries/       # Generated summaries and embeddings
└── requirements.txt      # Python dependencies
```

## Core Application Flow

1. **Frontend**:

   - User selects submission type
   - Enters content (text/image URL/video URL)
   - Receives real-time feedback with engaging loading states
   - Views structured evaluation results

2. **Backend**:

   - Processes incoming submissions
   - Generates appropriate embeddings
   - Matches with relevant briefs
   - Returns detailed evaluation in consistent JSON format

3. **Evaluation Results**:
   - Question-specific feedback
   - Corrections and highlights
   - Clear ACCEPT/REJECT decision
   - Summary of key points

## AI/ML Pipeline

The system uses a sophisticated AI pipeline for processing and evaluating submissions:

1. **Brief Processing**:

   - Automatically summarizes brand briefs using GPT-4
   - Generates embeddings for semantic matching
   - Stores vectors in Pinecone for efficient retrieval

2. **Evaluation System**:

   - **Text Evaluation**: Uses GPT-4 for deep content analysis
   - **Image Evaluation**: Combines CLIP for visual understanding with GPT-4 for analysis
   - **Video Evaluation**: Processes YouTube transcripts and evaluates content context

3. **Matching System**:

   - Uses embeddings to find the most relevant brief for each submission
   - Ensures evaluations are contextually appropriate
   - Maintains semantic understanding across different content types

4. **Prompt Generation**:
   - Automatically generates evaluation questions from briefs
   - Categories: script, video, image, and general
   - Ensures consistent evaluation criteria across submissions

## Backend Architecture

The backend system is built with FastAPI and follows a modular architecture:

1. **Initialization Process**:

   - Checks for required directories and files
   - Processes briefs and generates summaries if needed
   - Creates evaluation prompts automatically
   - Initializes vector store with brief embeddings

2. **API Endpoints**:

   - `/text`: Evaluates text submissions against matching briefs
   - `/image`: Processes Milanote boards using CLIP and GPT-4
   - `/video`: Handles YouTube video analysis with transcript processing
   - `/test/init`: Monitors system initialization status

3. **Data Management**:

   - Maintains brief summaries in both JSON and text formats
   - Stores evaluation prompts in structured JSON
   - Uses Pinecone for vector similarity search
   - Handles concurrent processing of submissions

4. **Error Handling**:
   - Graceful degradation if services are unavailable
   - Detailed error messages for debugging
   - Automatic retry mechanisms for API calls

## License

MIT License

## Author

Zahara Miriam
