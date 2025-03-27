## Faved POC - Influencer Submission Evaluator

A Python-based tool for evaluating influencer submissions against brand briefs using OpenAI's GPT-4 and vision models. The system supports multiple types of submissions including text scripts, images, and videos.

### Features

- **Multi-format Support**: Evaluates different types of submissions:
  - Text scripts
  - Images (Milanote boards)
  - YouTube videos
- **Brief Summarization**: Automatically generates concise summaries of brand briefs
- **Prompt Generation**: Creates evaluation questions based on brief content
- **Vector Search**: Uses Pinecone for semantic search to match submissions with relevant briefs
- **Structured Output**: Provides detailed feedback in JSON format
- **CLIP Integration**: Uses OpenAI's CLIP model for image understanding
- **YouTube Integration**: Automatically extracts and processes video transcripts

### How It Works

The system uses a single Pinecone index (`influencer-submission`) with different namespaces to organize content:

- `brief`: Stores brief embeddings generated using OpenAI's text-embedding model
- `text-submission`: Stores text submission embeddings
- `image-submission`: Stores image embeddings (generated using CLIP, padded to match dimensions)
- `video-submission`: Stores video transcript embeddings

When evaluating a submission, it:

1. Generates the appropriate embedding for the submission
2. Stores it in its type-specific namespace
3. Queries the `brief` namespace to find the most relevant brief
4. Uses GPT-4 to evaluate the match

The evaluation process uses carefully crafted prompts that:

- Adapt questions based on submission type (text/image/video)
- Include general evaluation criteria for all submissions
- Generate structured feedback with specific corrections and highlights
- Provide a clear ACCEPT/REJECT decision

Why Vector Search?
Converting content (briefs and submissions) into vectors enables:

- Efficient semantic matching without keyword limitations
- Instant retrieval from thousands of briefs
- Consistent evaluation across different content types
- Easy scaling as the number of briefs and submissions grows

### Prerequisites

- Python 3.8+
- OpenAI API key
- Pinecone API key
- Required Python packages (see `requirements.txt`)

### Environment Setup

1. Clone the repository
2. Create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:

```
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_pinecone_env
```

### Directory Structure

```
.
├── data/
│   ├── briefs/           # Brand brief text files
│   ├── submissions/      # Test files for development
│   ├── summaries/        # Generated brief summaries
│   └── results/          # Evaluation results
├── scripts/
│   ├── generate_prompts.py
│   ├── summarise_briefs.py
│   ├── vectorstore.py
│   ├── evaluate.py
│   ├── evaluate_image.py
│   ├── evaluate_video.py
│   ├── evaluate_text.py
│   └── delete_index.py   # Utility to delete Pinecone index
└── requirements.txt
```

### Usage

### 1. Generate Prompts

```bash
python scripts/generate_prompts.py
```

Generates evaluation questions based on brand briefs.

### 2. Summarize Briefs

```bash
python scripts/summarise_briefs.py
```

Creates concise summaries of all brand briefs.

### 3. Evaluate Submissions

#### Text Submissions

```bash
python scripts/evaluate_text.py
```

Evaluates text-based submissions.

#### Image Submissions

```bash
python scripts/evaluate_image.py
```

Evaluates Milanote board screenshots.

#### Video Submissions

```bash
python scripts/evaluate_video.py
```

Evaluates YouTube video submissions.

### 4. Delete Index

If you need to reset or remove the Pinecone index:

```bash
python scripts/delete_index.py
```

This will delete the `influencer-submission` index and all its namespaces.

### Output Format

Evaluation results are saved in JSON format with:

- Question-specific feedback
- Corrections needed
- What went well
- Final decision (ACCEPT/REJECT)

### License

MIT License

### Author

Zahara Miriam
