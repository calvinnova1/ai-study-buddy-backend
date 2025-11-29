import re
import google.generativeai as genai
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def chunk_text(text: str, max_length: int = 4000) -> List[str]:
    """
    Split long text into smaller chunks for processing
    """
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def generate_summary(text: str, summary_type: str = "concise") -> str:
    """
    Generate summary using Gemini AI with different styles
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Handle long texts by chunking
        if len(text) > 4000:
            chunks = chunk_text(text, 4000)
            summaries = []
            
            for chunk in chunks:
                prompt = f"Summarize this text concisely:\n\n{chunk}"
                response = model.generate_content(prompt)
                summaries.append(response.text)
            
            # Combine chunk summaries
            combined = " ".join(summaries)
            final_prompt = f"Create a final {summary_type} summary from these summaries:\n\n{combined}"
            final_response = model.generate_content(final_prompt)
            return final_response.text
        
        # For shorter texts, direct summarization
        prompts = {
            "concise": f"Provide a concise summary of this text in 3-5 sentences:\n\n{text}",
            "detailed": f"Provide a detailed summary covering all key points:\n\n{text}",
            "bullet_points": f"Summarize in clear bullet points:\n\n{text}"
        }
        
        prompt = prompts.get(summary_type, prompts["concise"])
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        raise Exception(f"Summary generation failed: {str(e)}")

def generate_quiz(text: str, num_questions: int = 5, question_type: str = "mixed") -> str:
    """
    Generate quiz questions using Gemini AI
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        if question_type == "mcq":
            prompt = f"""Generate exactly {num_questions} multiple-choice questions from this text.

Format EXACTLY like this for each question:
Q: [Clear question here]
A) [First option]
B) [Second option]
C) [Third option]
D) [Fourth option]
Correct: [A/B/C/D]

Text to generate questions from:
{text}"""
        
        elif question_type == "true_false":
            prompt = f"""Generate exactly {num_questions} true/false questions from this text.

Format EXACTLY like this for each question:
Q: [Statement here]
Correct: [True/False]

Text to generate questions from:
{text}"""
        
        else:  # mixed
            mcq_count = num_questions // 2
            tf_count = num_questions - mcq_count
            
            prompt = f"""Generate {mcq_count} multiple-choice questions and {tf_count} true/false questions from this text.

For MCQ questions, format EXACTLY like this:
Q: [Clear question here]
A) [First option]
B) [Second option]
C) [Third option]
D) [Fourth option]
Correct: [A/B/C/D]

For True/False questions, format EXACTLY like this:
Q: [Statement here]
Correct: [True/False]

Text to generate questions from:
{text}"""
        
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        raise Exception(f"Quiz generation failed: {str(e)}")

def parse_quiz_response(quiz_text: str, question_type: str) -> List[Dict]:
    """
    Parse the AI-generated quiz text into structured format
    """
    questions = []
    
    # Split by question markers
    question_blocks = re.split(r'\n(?=Q:|\d+\.)', quiz_text.strip())
    
    for block in question_blocks:
        if not block.strip() or 'Q:' not in block:
            continue
        
        try:
            # Extract question
            question_match = re.search(r'Q:\s*(.+?)(?=\n[A-D]\)|Correct:|$)', block, re.DOTALL)
            if not question_match:
                continue
            
            question_text = question_match.group(1).strip()
            
            # Check if it's MCQ or True/False
            if re.search(r'[A-D]\)', block):
                # Multiple choice question
                options = []
                for letter in ['A', 'B', 'C', 'D']:
                    option_match = re.search(f'{letter}\)\s*(.+?)(?=\n[A-D]\)|Correct:|$)', block, re.DOTALL)
                    if option_match:
                        options.append(option_match.group(1).strip())
                
                # Extract correct answer
                correct_match = re.search(r'Correct:\s*([A-D])', block, re.IGNORECASE)
                if correct_match and len(options) == 4:
                    correct_letter = correct_match.group(1).upper()
                    letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                    correct_answer = options[letter_to_index[correct_letter]]
                    
                    questions.append({
                        "question": question_text,
                        "options": options,
                        "correct_answer": correct_answer,
                        "type": "mcq"
                    })
            
            else:
                # True/False question
                correct_match = re.search(r'Correct:\s*(True|False)', block, re.IGNORECASE)
                if correct_match:
                    correct_answer = correct_match.group(1).capitalize()
                    
                    questions.append({
                        "question": question_text,
                        "options": None,
                        "correct_answer": correct_answer,
                        "type": "true_false"
                    })
        
        except Exception as e:
            # Skip malformed questions
            continue
    
    return questions

def validate_quiz_questions(questions: List[Dict], min_questions: int = 3) -> bool:
    """
    Validate that generated quiz has minimum quality
    """
    if len(questions) < min_questions:
        return False
    
    for q in questions:
        if not q.get("question") or not q.get("correct_answer"):
            return False
        
        if q["type"] == "mcq":
            if not q.get("options") or len(q["options"]) != 4:
                return False
    
    return True

def regenerate_if_needed(text: str, num_questions: int, question_type: str, max_attempts: int = 2) -> List[Dict]:
    """
    Try to generate valid quiz, retry if needed
    """
    for attempt in range(max_attempts):
        quiz_text = generate_quiz(text, num_questions, question_type)
        questions = parse_quiz_response(quiz_text, question_type)
        
        if validate_quiz_questions(questions, min_questions=max(1, num_questions - 2)):
            return questions
    
    # Return whatever we got on last attempt
    return questions