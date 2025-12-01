from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Optional
import shutil

# Data structure for the chat request
class ChatRequest(BaseModel):
    question: str
    context: str  # The text from the uploaded PDF/Doc

# Load environment variables
load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize FastAPI app
app = FastAPI(title="AI Study Buddy API", version="1.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pydantic models for request/response
class SummaryRequest(BaseModel):
    text: str
    summary_type: Optional[str] = "concise"  # concise, detailed, bullet_points

class QuizRequest(BaseModel):
    text: str
    num_questions: Optional[int] = 5
    question_type: Optional[str] = "mixed"  # mcq, true_false, mixed

class QuizQuestion(BaseModel):
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    type: str

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "AI Study Buddy API is running!",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/upload",
            "summarize": "/api/summarize",
            "generate_quiz": "/api/generate-quiz"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "ai_service": "Gemini AI"}

# File upload endpoint
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file (txt, pdf, docx) and extract text content
    """
    try:
        # Validate file type
        allowed_extensions = [".txt", ".pdf", ".docx"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save file temporarily
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text based on file type
        from utils import extract_text_from_file
        text_content = extract_text_from_file(file_path)
        
        # Clean up the file
        os.remove(file_path)
        
        return {
            "success": True,
            "filename": file.filename,
            "text_content": text_content,
            "text_length": len(text_content)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Summarization endpoint
@app.post("/api/summarize")
async def summarize_text(request: SummaryRequest):
    """
    Generate AI summary using Gemini AI
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create prompt based on summary type
        if request.summary_type == "concise":
            prompt = f"Provide a concise summary of the following text in 3-5 sentences:\n\n{request.text}"
        elif request.summary_type == "detailed":
            prompt = f"Provide a detailed summary of the following text, covering all key points:\n\n{request.text}"
        elif request.summary_type == "bullet_points":
            prompt = f"Summarize the following text in bullet points, highlighting the main ideas:\n\n{request.text}"
        else:
            prompt = f"Summarize the following text:\n\n{request.text}"
        
        # Generate summary
        response = model.generate_content(prompt)
        summary = response.text
        
        return {
            "success": True,
            "summary": summary,
            "original_length": len(request.text),
            "summary_length": len(summary),
            "summary_type": request.summary_type
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


# Quiz generation endpoint
@app.post("/api/generate-quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """
    Generate quiz questions using Gemini AI
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create prompt for quiz generation
        if request.question_type == "mcq":
            prompt = f"""Generate {request.num_questions} multiple-choice questions based on the following text.
For each question, provide:
1. The question
2. Four options (A, B, C, D)
3. The correct answer

Format each question as:
Q: [question]
A) [option]
B) [option]
C) [option]
D) [option]
Correct: [letter]

Text:
{request.text}"""
        
        elif request.question_type == "true_false":
            prompt = f"""Generate {request.num_questions} true/false questions based on the following text.
For each question, provide:
1. The statement
2. The correct answer (True or False)

Format each question as:
Q: [statement]
Correct: [True/False]

Text:
{request.text}"""
        
        else:  # mixed
            prompt = f"""Generate {request.num_questions} quiz questions (mix of multiple-choice and true/false) based on the following text.
For MCQ questions, provide:
Q: [question]
A) [option]
B) [option]
C) [option]
D) [option]
Correct: [letter]

For True/False questions, provide:
Q: [statement]
Correct: [True/False]

Text:
{request.text}"""
        
        # Generate quiz
        response = model.generate_content(prompt)
        quiz_text = response.text
        
        # Parse the quiz response (simplified parsing)
        from ai_services import parse_quiz_response
        questions = parse_quiz_response(quiz_text, request.question_type)
        
        return QuizResponse(questions=questions)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")

# Progress tracking endpoint (placeholder)
@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    """
    Get user's learning progress
    """
    # This will be connected to database in models.py
    return {
        "user_id": user_id,
        "total_notes": 0,
        "total_quizzes": 0,
        "average_score": 0,
        "message": "Progress tracking coming soon!"
    }

#chat endpoint
@app.post("/api/chat")
async def chat_with_document(request: ChatRequest):
    try:
        # We tell Gemini to act like a tutor using ONLY the provided text
        prompt = f"""
        You are an intelligent AI Study Buddy. Your goal is to help the student learn.
        
        Context from the student's notes:
        {request.context}
        
        Student's Question: 
        {request.question}
        
        Instructions:
        1. PRIORITIZE the Context above. Answer based on the notes whenever possible.
        2. If the student asks a general question (like "what else is important?" or "give me examples") that isn't in the notes, USE YOUR GENERAL KNOWLEDGE to help them.
        3. If you use general knowledge, start your answer with: "This isn't explicitly in your notes, but..."
        4. Be encouraging and concise.
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')# Or 'gemini-pro'
        response = model.generate_content(prompt)
        
        return {"answer": response.text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)