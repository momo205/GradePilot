# GradePilot: Autonomous Agent Implementation Plan

## 1. Executive Summary
GradePilot is a true **autonomous academic planning agent**. Unlike a simple "AI wrapper" that only responds to user prompts, GradePilot operates proactively. Once given a student's context, it continuously monitors deadlines, autonomously researches missing information, utilizes tools (like calendars and web scrapers), and dynamically adjusts study plans in the background without requiring constant user hand-holding.

## 2. Recommended Tech Stack
Given the heavy reliance on AI and document processing, this stack is highly recommended:

### Frontend (Website)
*   **Framework:** **Next.js (React)** - Excellent for routing, SEO, and fast page loads, making it easy to grow from a simple website into a full web app.
    *   **Styling:** **Vanilla CSS** with modern design principles (glassmorphism, vibrant gradients, micro-animations) to make the platform feel intuitive and responsive to agent actions. 
*   **State Management:** **Zustand** or React Context for managing user data across the app.

### Backend (Agent Logic & Infrastructure)
*   **Agent Framework:** **LangChain**, **LlamaIndex**, or a custom ReAct (Reasoning and Acting) loop in Python. This is crucial for giving the LLM the ability to decide *when* to use tools.
*   **Background Execution:** **Celery + Redis** or **RQ**. A true agent needs to run asynchronously and proactively (e.g., waking up every night to check the schedule and re-plan), not just when an HTTP request is made.
*   **API Framework:** **Python (FastAPI)** - Python is the industry standard for AI, OCR, and data processing. FastAPI will serve as the bridge between the frontend and the background agent.
*   **Databases:**
    *   **Relational:** **PostgreSQL** (via Supabase or Neon) - For standard app data (users, configured courses, hard deadlines).
    *   **Vector Database (Memory):** **pgvector** (Postgres extension), **Pinecone**, or **ChromaDB. This gives the agent *long-term memory*, allowing it to remember past study habits, user preferences, and semantic relationships between course materials over the entire semester.
*   **Storage:** **AWS S3** or **Google Cloud Storage** - For securely storing user-uploaded PDFs, notes, and images.

### Agentic Tools (APIs the Agent Controls)
*   **AI Engine:** **Google Gemini API** (Specifically Gemini 1.5 Pro) - The "brain" of the agent. Its massive context window and native multimodal capabilities allow it to ingest entire textbooks, reason over them, and decide which tools to call.
*   **Web Search & Scraping Tools:** **Tavily Search API**, **Firecrawl**, or **Browserbase**. The agent decides *when* a topic in the notes is insufficiently explained, searches the web, reads the results, and incorporates the findings into the study plan.
*   **Calendar Integration:** **Google Calendar API** - The agent operates directly on the user's calendar, pushing new blocks and deleting old ones as it reacts to changes.
*   **Communication Tool:** **Resend** or **Twilio** - The agent can proactively decide to email or text the user if it detects they are falling behind schedule.

---

## 3. Feature Recommendations ("Blah Blah" Features)
To make GradePilot truly stand out for your project, consider adding these features to your roadmap:

1.  **Syllabus Auto-Parser:** Students just upload their course syllabus PDF at the start of the semester. GradePilot automatically extracts all key dates, grading weightings, and textbook requirements, instantly populating their calendar.
2.  **Spaced Repetition Flashcards:** Automatically convert PDF notes into interactive flashcards (like Anki or Quizlet) that adapt to what the student gets wrong.
3.  **Built-in Pomodoro Timer:** A study timer on the dashboard that tracks actual study time vs. planned study time, providing analytics on how focused the student was.
4.  **WhatsApp / SMS Nudges:** Use the Twilio API to send students a friendly text message 30 minutes before a study session or when a deadline is fast approaching.
5.  **"Cram Mode" vs "Chill Mode":** Let users adjust the intensity of the schedule based on their current stress level or unexpected life events.
6.  **Collaborative Study Groups:** Allow users to share their AI-generated study guides and resource links with classmates in the same course.

---

## 4. Step-by-Step Implementation Phases

### Phase 1: Blueprint & Infrastructure Foundation (Weeks 1-3)
*   **Actionable Steps:**
    *   Create UI/UX wireframes emphasizing the "Agent Activity" feed (showing the user what the agent is thinking/doing in the background).
    *   Initialize the Next.js frontend and FastAPI backend.
    *   Set up PostgreSQL for structured data and configure `pgvector` for the agent's memory.
    *   Set up the **Celery/Redis worker queue** so the agent can run long, multi-step thought processes continuously in the background.

### Phase 2: User Context & State Initialization (Weeks 4-5)
*   **Actionable Steps:**
    *   Build the Upload Hub for users to dump PDFs, syllabi, and images.
    *   Implement basic document processing: extract text, chunk it, embed it using an embedding model, and store it in the Vector Database so the agent can query it later.
    *   Collect user availability constraints (e.g., "I only study between 5 PM and 10 PM").

### Phase 3: Building the Autonomous Agent Loop (Weeks 6-8)
*   **Actionable Steps:**
    *   Implement the core ReAct (Reasoning and Acting) loop using LangChain/LlamaIndex or raw Gemini API tool calling.
    *   **Give the Agent Tools:** Write simple Python functions the LLM can trigger (e.g., `search_web_for_topic(query)`, `create_calendar_event(time, task)`, `read_document_chunk(topic_id)`).
    *   Develop the **Planning System:** The agent surveys the upcoming month, identifies gaps in knowledge, and formulates a step-by-step preparation plan.

### Phase 4: Proactive Execution & Dynamic Rescheduling (Weeks 9-10)
*   **Actionable Steps:**
    *   Implement cron jobs that wake the agent up daily.
    *   The agent pulls the user's state: "Did they mark yesterday's study block as complete?"
    *   If no, the agent uses its `update_calendar()` tool to shift the workload forward, prioritizing higher-value tasks to prevent cramming.
    *   If a concept in a PDF is contradictory or vague, the agent autonomously decides to use the web search tool to find clarificaton before building the quiz.

### Phase 5: Practice Evaluation & Memory Feedback (Weeks 11-12)
*   **Actionable Steps:**
    *   The agent generates practice quizzes and evaluates user answers.
    *   **Memory Update:** The agent writes the evaluation results back to its long-term memory (e.g., "Student struggles with Chapter 3 concepts").
    *   The agent incorporates this memory into future planning, automatically scheduling review sessions for weak areas without being explicitly told to do so.
    *   Finalize UI, ensure smooth transitions, and deploy the system.
