import os
import re
from typing import List, Dict, Any
from llama_index.core.schema import TextNode
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def build_prompt(user_query: str, context_nodes: List[TextNode], department_name: str = "General") -> str:
    context_blocks = []
    for node in context_nodes:
        source_name = node.metadata.get("source", "Unknown Document")
        page_num = node.metadata.get("page_number", "N/A")
        
        block = f"[Source: {source_name}, Page: {page_num}]\n{node.text}"
        context_blocks.append(block)

    context_text = "\n\n---\n\n".join(context_blocks)

    prompt = f"""
You are a polite, highly knowledgeable expert assistant for the {department_name} department. 
Your primary duty is to provide helpful, accurate answers to user queries based ONLY on the provided CONTEXT. Do not use outside knowledge or make assumptions.

Your task is to follow these steps precisely:
1. Analyze the user's query to understand their needs.
2. Review the CONTEXT for information that addresses the query.
3. Based on your analysis, provide an answer. 
4. CITE YOUR SOURCES. Every factual claim you make must include an inline citation matching the bracketed source tags in the CONTEXT.

--- START OF CONTEXT ---
{context_text}
--- END OF CONTEXT ---

User Query: "{user_query}"

--- DECISION RULES ---
- **RULE A (Answered):** If the CONTEXT contains the necessary information, provide a detailed answer. You MUST include inline citations like this: [Source: filename.pdf, Page: 4]. Your 'Status' MUST be "Answered". The 'Clarifying Questions' section MUST be left completely blank.
- **RULE B (Insufficient Information):** If the CONTEXT is missing the required information, is too vague, or does not address the query, politely explain what information is missing. Your 'Status' MUST be "Insufficient Information".
- **RULE C (Clarification):** IF AND ONLY IF your 'Status' is "Insufficient Information", you MUST provide a numbered list of follow-up questions under 'Clarifying Questions'.

Respond using the following format EXACTLY:

Answer:
<Your polite, detailed explanation here with inline citations [Source: X, Page: Y]. If information is missing, politely explain why.>

Status: <Answered / Insufficient Information>

Clarifying Questions:
<A numbered list of up to 3 questions ONLY if the Status is "Insufficient Information". This section MUST NOT BE SHOWN otherwise.>
"""
    return prompt.strip()

def query_llm_with_context(user_query: str, context_nodes: List[TextNode], department_name: str = "General", model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
    """
    Queries the Gemini API and parses the structured output.
    """
    prompt = build_prompt(user_query, context_nodes, department_name)

    try:
        client = genai.Client()

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        raw_output = response.text.strip()
        
        parsed_response = {
            "status": "sufficient",
            "answer": raw_output,
            "questions": []
        }

        if "Status: Insufficient Information" in raw_output:
            parsed_response["status"] = "insufficient"
            
            match = re.search(r"Clarifying Questions:\s*\n(.*?)(?=\n---|\Z)", raw_output, re.DOTALL)
            if match:
                questions_text = match.group(1).strip()
                questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
                parsed_response["questions"] = questions
                
            answer_part = raw_output.split("Status:")[0].replace("Answer:", "").strip()
            parsed_response["answer"] = answer_part
            
        else:
            answer_part = raw_output.split("Status:")[0].replace("Answer:", "").strip()
            parsed_response["answer"] = answer_part

        return parsed_response

    except Exception as e:
        error_message = f"Gemini API Error: {str(e)}"
        print(error_message)
        return {"status": "error", "answer": error_message, "questions": []}