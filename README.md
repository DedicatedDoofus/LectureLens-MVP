# LectureLens

LectureLens is a minimum viable product for the AI entrepreneurship project. It analyzes a timestamped online-lecture transcript and gives an instructor evidence-based suggestions for improving engagement, questioning, clarity, and observable participation.

## 1. Problem and market need

Online instructors often receive attendance information but very little actionable feedback about how a lesson flowed. A teacher may know that a learner struggled, but not exactly where a question, explanation, or activity could have made the lesson more interactive. LectureLens turns a transcript into small, practical coaching actions that can be tried in the next lesson.

The first target user is an instructor or tutor who teaches one-on-one or small-group programming lessons. The product can later expand to office hours, tutoring centers, corporate training, and asynchronous course review.

## 2. Core MVP functionality

1. The user selects a built-in sample, pastes a transcript, or uploads a `.txt` transcript.
2. The user selects an analysis focus: all areas, engagement, questioning, clarity, or participation.
3. LectureLens sends the transcript and focus to a Gemini model with a prompt-engineered coaching instruction.
4. The model returns structured data containing scores, strengths, evidence-based recommendations, confidence labels, and a next-lesson action plan.
5. The interface renders the result as a dashboard that is easy to explain during a live demo.

The app intentionally treats “attention” as an uncertain observable signal. It does not claim to read a student’s mind or diagnose motivation. It only discusses transcript evidence such as questions, pauses, explicit uncertainty, and completed responses.

## 3. Prompt engineering patterns

### Persona and constraints

The system prompt defines the model as a supportive instructional coach. It requires the model to use observable evidence, separate evidence from interpretation, avoid unsupported claims about internal attention, and provide one concrete action for the next lesson.

### Few-shot prompting

The system prompt includes a miniature example showing how a vague “Does that make sense?” check can be converted into a timestamped recommendation with a specific retrieval question. This gives the model a clear example of the desired level of specificity.

### Iterative refinement

The prompt asks the model to perform the task in stages: identify evidence, draft opportunities, remove unsupported conclusions, prioritize the highest-value actions, and check that each recommendation includes the fields needed by the interface.

### Structured output

The Gemini Interactions API is called with a JSON Schema. This is not counted as one of the two required course patterns by itself; it is an implementation technique that makes the AI output dependable for a UI.

## 4. Run the MVP on Windows

Open PowerShell in this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

For live Gemini analysis, copy `env.example` to `.env` and add your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey). Google lists `gemini-3.5-flash-lite` as a free-tier model, although account access and rate limits can vary. Do not submit or share your key.

Then launch the UI:

```powershell
streamlit run app.py
```

If no key is configured, the app automatically uses a deterministic local demo mode. The built-in sample is designed so the live presentation can still show the full user flow.

## 5. Technical architecture

```text
Streamlit UI
    ↓ transcript + focus
Prompt builder
    ↓ persona + few-shot example + refinement rules
Gemini Interactions API
    ↓ JSON Schema response
Recommendation dashboard
```

The project uses a local fallback so the interface remains usable for a classroom demonstration. In a production version, the fallback should be replaced or supplemented with an explicit API health check, authentication, transcript deletion controls, and a cost limit.
