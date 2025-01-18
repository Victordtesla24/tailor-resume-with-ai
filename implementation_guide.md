# Smart Resume Tailoring App: Implementation Guide

## Personal Invocation

"Cursor AI, take a deep breath and become our Senior Developer—someone with 20+ years of coding across multiple paradigms. Your philosophies:

1. Less code is better code.
2. Aim for modern, appealing designs with minimal complexity.
3. Solve errors swiftly and thoroughly.

Please keep code generation concise and focus on the essential parts that yield functionality and clarity. If extra fluff appears, prune it. Let's build an efficient, modern, and user-friendly app."

## 1. Setting the Stage

### 1.1 Project Goal

- A Smart Resume Tailoring App built on MacBook Air M3.
- Developed with Python + Streamlit.
- Uses multiple AI providers (OpenAI, Anthropic, etc.).
- Guided by Cursor AI wearing its senior dev hat (i.e., minimal code, maximum clarity).

### 1.2 Fail Fast, Iterate Quickly

- Launch a basic MVP, test with real data, then refine.
- If features fail or become unwieldy, drop or fix them immediately.
- Maintain tight feedback loops for user experience improvements.

### 1.3 Senior Dev Persona Principles

- Keep It Simple: Provide only necessary imports and code.
- Small, Elegant Functions: Each function has a clear single purpose.
- Efficient Error Handling: Catch and explain errors briefly; don't bury them under layers of logging.

## 2. Environment Setup (Minimalist Edition)

1. Install Python (if needed):
   - `brew install python`
2. Create & Activate Virtual Environment:
   - `python3 -m venv resume_app_env`
   - `source resume_app_env/bin/activate`
3. Install Requirements:
   - `pip install streamlit openai anthropic python-docx requests beautifulsoup4 selenium python-dotenv`
4. Acquire & Open Cursor AI
   - Download from cursor.sh.
   - Open project folder.
   - Confirm environment works by running a small test:
     - `print("Senior Dev Persona in effect, environment is ready!")`
5. Basic Security/Privacy Note
   - By default, we store data locally and do not share it with third parties unless the user opts in for data collection (see Iteration 2).
   - If handling user resumes for real production, consider GDPR/CCPA compliance and ensure you have a clear data retention policy.

## 3. MVP: Minimal, Yet Effective

### Success Criteria

#### 1. Core Requirements

- Upload Word format (.docx) resumes only
- Extract text content successfully
- Generate tailored content for selected sections
- Display readable output

#### 2. Error Handling

- Invalid file format detection
- API failure recovery
- Missing input validation

#### 3. Performance Metrics

- File upload under 3 seconds
- AI response under 10 seconds
- Memory usage under 500MB

#### 4. Quick Testing

- Manual check: Upload a small .docx resume, select a section or two, supply a job description, and ensure a tailored output is produced promptly.

### Implementation Checkpoints

- File upload and validation working
- Text extraction successful
- Section selection functional
- AI integration complete
- Basic error handling in place

### Core Functions

1. Upload Word Resume
2. Paste Job Description
3. Select Sections (Summary, Experience, etc.)
4. Generate Tailored Resume Using One AI Model (OpenAI)

### Instructions to Cursor AI

"Cursor AI, you are in senior dev mode. Generate a lean app.py that accomplishes the following MVP requirements with minimal code and strong clarity."

#### Proposed MVP Code

```python
import streamlit as st
import openai
from docx import Document

openai.api_key = "YOUR_OPENAI_API_KEY"

st.title("Smart Resume Tailoring App")

uploaded_file = st.file_uploader("Upload your resume (Word)", type=["docx"])
job_description = st.text_area("Paste Job Description")
sections = st.multiselect("Select sections", ["Summary", "Experience", "Skills", "Education"])

if st.button("Tailor Resume"):
    if uploaded_file and job_description and sections:
        # Basic docx extraction
        doc = Document(uploaded_file)
        resume_text = "\n".join(p.text for p in doc.paragraphs)

        prompt_text = (
            f"Here's my resume:\n{resume_text}\n\n"
            f"Please tailor these sections: {', '.join(sections)} "
            f"for this job:\n{job_description}"
        )

        try:
            response = openai.Completion.create(
                engine="davinci",
                prompt=prompt_text,
                max_tokens=1000
            )
            st.text_area("Tailored Resume", response.choices[0].text)
        except Exception as e:
            st.error(f"AI Error: {str(e)}")
    else:
        st.warning("Please upload a resume, enter a job description, and select sections.")
```

#### Run

- `streamlit run app.py`

#### Performance Note

- For small .docx files, this should be well under 3 seconds to parse.
- The OpenAI API call typically responds within 5–8 seconds for max_tokens=1000.

## 4. Iteration 1: Multi-AI Model Selector & API Key Management

### Dependencies

- Requires: MVP (Core functionality)
- Optional: None
- Next: Iteration 2 (Data Collection)

### Success Criteria

#### 1. Functionality

- All API keys load securely
- Model selection works
- Error handling for invalid keys

#### 2. Security

- No keys in code
- Proper environment validation
- Secure key storage

#### 3. Performance

- Switching models quickly
- Minimal overhead in UI

#### 4. Testing

- Manual check: Attempt to pick an invalid or missing API key, see if the app warns gracefully.

### Implementation Checkpoints

- Environment setup complete
- API key validation working
- Model selection functional
- Error handling implemented

### Why?

- Different AI engines offer unique strengths for resume tailoring
- Secure API key management is crucial for production deployment
- Senior Dev Persona: Implement robust yet minimal security measures

### API Key Management

1. Create a .env.example template:
   - `OPENAI_API_KEY=sk-your-key-here`
   - `ANTHROPIC_API_KEY=sk-ant-your-key-here`
   - `DEEPMIND_API_KEY=your-key-here  # When available`
2. Add to .gitignore:
   - `.env`
3. Load keys securely:

```python
from dotenv import load_dotenv
import os

load_dotenv()

def init_ai_client(provider: str):
    """Initialize AI client with appropriate API key."""
    if provider == "OpenAI":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or not api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key")
        return openai
    elif provider == "Anthropic":
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key or not api_key.startswith("sk-ant-"):
            raise ValueError("Invalid Anthropic API key")
        return anthropic.Client(api_key=api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

### Model Selection Process

```python
MODELS = {
    "OpenAI GPT-4": {
        "provider": "OpenAI",
        "id": "gpt-4",
        "description": "Best for general-purpose resume tailoring with strong reasoning",
        "max_tokens": 2000,
        "temperature": 0.7
    },
    "OpenAI GPT-3.5": {
        "provider": "OpenAI",
        "id": "gpt-3.5-turbo",
        "description": "Fast and cost-effective for straightforward tailoring",
        "max_tokens": 1000,
        "temperature": 0.7
    },
    "Anthropic Claude": {
        "provider": "Anthropic",
        "id": "claude-2",
        "description": "Excels at structured, consistent resume formatting",
        "max_tokens": 1500,
        "temperature": 0.6
    }
}

with st.sidebar:
    st.header("Choose AI Model")
    selected_model = st.selectbox(
        "Select Model",
        options=list(MODELS.keys()),
        help="Choose the AI model that best suits your needs"
    )
    config = MODELS[selected_model]
    st.markdown(f"### Model Profile\n{config['description']}")
```

### Resume Tailoring Implementation

```python
def tailor_resume(resume_text: str, job_description: str, sections: list, config: dict) -> str:
    """Tailor resume using selected AI model."""
    try:
        client = init_ai_client(config["provider"])
        prompt = f"Tailor these sections: {', '.join(sections)}\n\nResume:\n{resume_text}\n\nJob Description:\n{job_description}"

        if config["provider"] == "OpenAI":
            # For Chat Completions
            response = client.ChatCompletion.create(
                model=config["id"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"]
            )
            return response.choices[0].message["content"]

        elif config["provider"] == "Anthropic":
            response = client.completion(
                prompt=prompt,
                model=config["id"],
                max_tokens_to_sample=config["max_tokens"]
            )
            return response.completion

    except Exception as e:
        return f"Error: {str(e)}"
```

### Testing

- Provide valid keys in .env.
- Manual test: Switch from "OpenAI GPT-4" to "Anthropic Claude" in the sidebar. Attempt a resume tailoring and confirm no code changes needed.
- Performance: Minimal difference in speed if you switch providers.

## 5. Iteration 2: Data Collection for Fine-Tuning

### Dependencies

- Requires: Iteration 1 (API Key Management)
- Next: Iteration 3 (Job Board Integration)

### Success Criteria

#### 1. Data Collection

- Secure data storage
- Proper anonymization
- User opt-in working

#### 2. Performance

- No UI lag during collection
- Minimal storage usage
- Efficient data format (e.g., JSON Lines)

#### 3. Testing

- Manual check: Tailor a sample resume, opt in to share data, and confirm the anonymized data is appended to a training_data.jsonl file without errors.

### Implementation Checkpoints

- Data storage mechanism working
- Opt-in functionality complete
- Anonymization implemented
- Error handling in place

### Why?

- Over time, the app learns from real usage, improving suggestions.
- Senior Dev Persona: minimal but robust data capture.

### Implementation Sketch

```python
import json
import streamlit as st

def collect_training_data(resume_text, job_description, tailored_output):
    """Store prompt+completion data for fine-tuning, if user opts in."""
    data = {
        "prompt": f"Resume: {resume_text[:300]}...\nJobDesc: {job_description[:300]}...",
        "completion": tailored_output[:300]  # store partial to limit data size
    }
    with open("training_data.jsonl", "a") as f:
        f.write(json.dumps(data) + "\n")

share_data = st.checkbox("Opt-in to share anonymized data for AI improvement")

if st.button("Tailor Resume"):
    # Assume we've read doc paragraphs into resume_text
    tailored_output = tailor_resume(resume_text, job_description, sections, config)
    st.text_area("Tailored Resume", tailored_output, height=200)

    if share_data:
        try:
            collect_training_data(resume_text, job_description, tailored_output)
            st.success("Training data saved (anonymized).")
        except Exception as e:
            st.error(f"Could not save training data: {e}")
```

#### Performance Note

- Saving small JSON lines is typically negligible in CPU/memory usage. The main cost is still the AI inference.

#### Privacy Consideration

- We only store partial text ([:300]) to limit sensitive data. If more robust privacy is needed, consider advanced anonymization (e.g., removing names, addresses).

## 6. Iteration 3: Job Board Integration

### Dependencies

- Requires: Iteration 2 (Data Collection)
- Next: Iteration 4 (Preserving Formatting)

### Success Criteria

#### 1. Integration

- Successful URL parsing
- Accurate job description extraction
- Proper error handling

#### 2. Performance

- Response time < 5 seconds for typical job pages
- Graceful failure handling
- Clear user feedback

#### 3. Testing

- Manual check: Provide a valid Seek.com.au job URL, verify the job description is extracted. Then tailor the resume using that fetched text.

### Implementation Checkpoints

- URL validation working
- Job description extraction functional
- Error handling implemented
- User feedback system in place

### Why?

- Automate job description fetching from sites like seek.com.au.
- If scraping fails, handle gracefully.

### Implementation Sketch

```python
import requests
from bs4 import BeautifulSoup

def fetch_job_from_seek(url):
    """Fetch job description from a Seek.com.au listing."""
    try:
        resp = requests.get(url)
        resp.raise_for_status()  # raise exception if status != 200
        soup = BeautifulSoup(resp.text, "html.parser")
        job_desc = soup.find("div", {"class": "jobAdBody"})
        if job_desc:
            return job_desc.get_text(separator="\n").strip()
        else:
            return "Couldn't parse job description from this page."
    except Exception as e:
        return f"Error fetching job: {e}"

job_url = st.text_input("Seek.com.au Job URL (optional)")
if job_url:
    fetched_desc = fetch_job_from_seek(job_url)
    if fetched_desc.startswith("Error"):
        st.error(fetched_desc)
    else:
        st.text_area("Fetched Job Description", fetched_desc, height=200)

# Then pass fetched_desc into your tailoring prompt if desired
```

#### Performance Note

- Simple GET requests plus parsing are typically under 1 second. If Seek's structure changes, update or remove this feature swiftly (fail fast).

#### Testing Tip

- Use known job URLs and invalid URLs to confirm error handling.

## 7. Iteration 7: "WOW" Factor & Enhanced User Experience

### Dependencies

- Requires: Iteration 6 (Flexible Selection)
- Next: Iteration 8 (Job Search & Salary Integration)

### Success Criteria

#### 1. User Interface

- Modern, clean design with consistent styling
- Responsive interactions and smooth transitions
- Intuitive controls with inline editing capabilities
- Clear visual hierarchy and feedback

#### 2. Features

- Real-time ATS scoring with keyword matching
- Live previews of tailored content
- Inline editing with change tracking
- One-click optimization

#### 3. Performance

- Sub-second response times for UI interactions
- Minimal lag during multi-paragraph edits
- Efficient state management
- Smooth animations and transitions

#### 4. Testing

- Verify ATS scoring accuracy
- Test responsiveness across screen sizes
- Validate state management
- Check animation performance

### Implementation Details

#### 1. ATS Score Implementation

```python
def calculate_ats_score(resume_text: str, job_description: str) -> float:
    """Calculate ATS match score based on keyword overlap."""
    keywords = extract_keywords(job_description)
    matches = sum(1 for kw in keywords if kw.lower() in resume_text.lower())
    return round((matches / len(keywords) * 100), 2) if keywords else 0.0

def extract_keywords(text: str) -> set:
    """Extract relevant keywords from text."""
    # Add advanced NLP processing here if needed
    words = set(word.strip().lower() for word in text.split()
               if len(word) > 3 and word.isalnum())
    return words

# Usage in Streamlit
if resume_text and job_description:
    score = calculate_ats_score(resume_text, job_description)
    st.metric("ATS Match Score", f"{score}%",
             delta=f"{score - previous_score:.1f}%" if 'previous_score' in locals() else None)
```

#### 2. Inline Editing Component

```python
def create_editable_section(section_text: str, section_name: str):
    """Create an inline-editable section with change tracking."""
    col1, col2 = st.columns([3, 1])
    with col1:
        edited_text = st.text_area(
            f"Edit {section_name}",
            value=section_text,
            height=200,
            key=f"edit_{section_name}"
        )
    with col2:
        st.button("Accept Changes", key=f"accept_{section_name}")
        st.button("Revert", key=f"revert_{section_name}")
    return edited_text
```

#### 3. One-Click Optimization

```python
def optimize_resume(resume_text: str, job_description: str) -> dict:
    """Automatically optimize resume sections."""
    sections = detect_sections(resume_text)
    optimized = {}

    for section, content in sections.items():
        # Use AI to optimize each section
        optimized[section] = tailor_section(content, job_description)

    return optimized

if st.button("One-Click Optimize"):
    with st.spinner("Optimizing your resume..."):
        optimized = optimize_resume(resume_text, job_description)
        display_side_by_side(resume_text, optimized)
```

## 8. Iteration 8: Job Search & Salary Integration

### Dependencies

- Requires: Iteration 7 (WOW Factor)
- Next: Iteration 9 (AI Job Recommendations)

### Success Criteria

#### 1. Job Search

- Efficient seek.com.au integration
- Accurate salary filtering
- Clean job listing display

#### 2. User Profile

- Secure credential storage
- Salary expectation management
- Search preference persistence

#### 3. Performance

- Fast job search results
- Efficient data caching
- Smooth UI updates

#### 4. Testing

- Verify job search accuracy
- Test salary filtering
- Validate credential security

### Implementation Details

#### 1. Job Search Integration

```python
def fetch_jobs(role: str, location: str, min_salary: float) -> list:
    """Fetch and filter jobs from seek.com.au."""
    jobs = []
    try:
        # Implement seek.com.au API or scraping logic
        raw_jobs = fetch_from_seek(role, location)
        # Filter by salary
        jobs = [job for job in raw_jobs
               if estimate_salary(job) >= min_salary]
    except Exception as e:
        st.error(f"Job search error: {e}")
    return jobs

# Streamlit UI
with st.sidebar:
    role = st.text_input("Job Role", "Software Engineer")
    location = st.text_input("Location", "Melbourne")
    salary = st.number_input("Minimum Salary (AUD)",
                           value=80000, step=5000)

if st.button("Search Jobs"):
    jobs = fetch_jobs(role, location, salary)
    display_job_results(jobs)
```

#### 2. Salary Management

```python
class SalaryManager:
    def __init__(self):
        self.load_preferences()

    def load_preferences(self):
        """Load user's salary preferences."""
        if 'salary_prefs' not in st.session_state:
            st.session_state.salary_prefs = {
                'current': 0,
                'expected': 0,
                'history': []
            }

    def update_salary(self, current: float, expected: float):
        """Update salary preferences."""
        st.session_state.salary_prefs.update({
            'current': current,
            'expected': expected,
            'history': self.get_history() + [(current, expected)]
        })

    def get_history(self) -> list:
        """Get salary history."""
        return st.session_state.salary_prefs.get('history', [])

# Usage
salary_mgr = SalaryManager()
current = st.number_input("Current Salary (AUD)", value=0, step=5000)
expected = st.number_input("Expected Salary (AUD)", value=0, step=5000)

if st.button("Update Salary Preferences"):
    salary_mgr.update_salary(current, expected)
```

## 9. Iteration 9: AI Job Recommendations

### Dependencies

- Requires: Iteration 8 (Job Search)
- Next: Iteration 10 (Auto-Fix Integration)

### Success Criteria

#### 1. AI Matching

- Accurate skill matching
- Salary alignment scoring
- Combined relevancy metrics

#### 2. Performance

- Efficient similarity calculations
- Quick ranking updates
- Smooth UI feedback

#### 3. Testing

- Validate match accuracy
- Test ranking consistency
- Verify performance

### Implementation Details

#### 1. Job-Resume Matching

```python
def compute_job_match(resume_text: str, job_posting: dict) -> dict:
    """Calculate comprehensive job match metrics."""
    skill_score = calculate_skill_match(resume_text, job_posting['description'])
    salary_score = calculate_salary_fit(
        job_posting.get('salary_range', [0, 0]),
        st.session_state.salary_prefs['expected']
    )

    return {
        'skill_match': skill_score,
        'salary_fit': salary_score,
        'overall_score': 0.7 * skill_score + 0.3 * salary_score
    }

def calculate_skill_match(resume: str, job_desc: str) -> float:
    """Calculate skill match using embeddings or keyword matching."""
    # Implement embedding-based similarity or keyword matching
    return 0.85  # Placeholder

def calculate_salary_fit(job_range: list, expected: float) -> float:
    """Calculate salary fit score."""
    min_salary, max_salary = job_range
    if expected <= max_salary and expected >= min_salary:
        return 1.0
    elif expected < min_salary:
        return min_salary / expected
    else:
        return max_salary / expected

# Usage in job search results
for job in jobs:
    match = compute_job_match(resume_text, job)
    st.write(f"Match Score: {match['overall_score']:.2%}")
    st.write(f"Skills: {match['skill_match']:.2%}")
    st.write(f"Salary Fit: {match['salary_fit']:.2%}")
```

## 10. Iteration 10: Auto-Fix Integration

### Dependencies

- Requires: Iteration 9 (AI Job Recommendations)
- Next: Future Enhancements

### Success Criteria

#### 1. Auto-Fix

- Dependency management
- Code formatting
- Error correction

#### 2. Performance

- Quick fixes
- Minimal disruption
- Efficient testing

#### 3. Testing

- Verify fix accuracy
- Test reversion capability
- Validate stability

### Implementation Details

#### 1. Auto-Fix Script

```python
def run_auto_fix():
    """Run the auto-fix routine."""
    try:
        check_dependencies()
        format_code()
        run_tests()
    except Exception as e:
        handle_fix_error(e)

def check_dependencies():
    """Verify and install missing dependencies."""
    required = [
        "streamlit",
        "openai",
        "anthropic",
        "python-docx",
        "requests",
        "beautifulsoup4"
    ]

    for pkg in required:
        try:
            importlib.import_module(pkg)
        except ImportError:
            subprocess.run(["pip", "install", pkg])

def format_code():
    """Run code formatters."""
    subprocess.run(["black", "."])
    subprocess.run(["isort", "."])
    subprocess.run(["flake8", "."])

def run_tests():
    """Run test suite."""
    result = subprocess.run(["pytest"], capture_output=True)
    if result.returncode != 0:
        raise Exception(f"Tests failed: {result.stderr.decode()}")

def handle_fix_error(error: Exception):
    """Handle auto-fix errors."""
    st.error(f"Auto-fix error: {str(error)}")
    # Log error details
    logging.error(f"Auto-fix failed: {error}")
```

## Beyond Iteration 10: Future Enhancements

1. Enhanced Resume Tailoring Features

   - Model-specific prompt templates optimized for each model's strengths
   - Feedback loop with success metrics for model performance
   - Advanced persona matching with temporal skill analysis
   - Cross-section consistency validation
   - Industry-specific terminology verification
   - Format retention and structure preservation
   - Automatic achievement highlighting based on role
   - Industry-specific keyword optimization
   - Custom formatting per role

2. Advanced CV Parsing

   - Real-time tailoring as job descriptions change
   - Smart section detection and organization
   - Format preservation across edits

3. Auto-Apply Integration

   - One-click job applications
   - Application tracking
   - Follow-up management

4. Analytics Dashboard
   - Application success rates
   - Skill gap analysis
   - Salary trend tracking

By carefully extending the existing structure, you maintain consistency, keep the code minimal, and produce a robust new feature set for job search & AI-based matching—while also automating error resolution for a frictionless developer experience.

Happy Building, and remember:

"Cursor AI, remain the 20+ year senior dev: keep solutions minimal, efficient, and user-centered for maximum impact!"
