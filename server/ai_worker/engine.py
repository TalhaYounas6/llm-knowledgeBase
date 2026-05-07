import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from markitdown import MarkItDown

load_dotenv(dotenv_path="../.env")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)

schema_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are an expert librarian maintaining a personal knowledge wiki.
    Your job is to read the provided raw text and generate a structured Markdown file.
    
    RULES:
    1. Start with a YAML frontmatter block containing 'tags:' and 'date:'.
    2. Write a 2-sentence summary at the top.
    3. Break the main points into clear bullet points.
    4. CRITICAL: Identify any key concepts, technologies, or entities and wrap them in double brackets like [[This]] so they become wikilinks.
    """),
    ("human", "Here is the raw text to process:\n\n{raw_text}")
])

chain = schema_prompt | llm

def extract_text_from_file(file_path):
    print(f"Extracting text from {os.path.basename(file_path)}...")
    md = MarkItDown()
    try:
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def processDocument(file_path):
    text_document = extract_text_from_file(file_path)

    if not text_document:
        raise Exception("Could not extract text from document.")
    
    print("AI is analyzing and writing markdown...")
    response = chain.invoke({"raw_text": text_document})
    
    return response.content