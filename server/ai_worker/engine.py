import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from markitdown import MarkItDown

# load_dotenv(dotenv_path="../.env")

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0.2
# )

schema_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are an expert Knowledge Manager and Archivist building a highly interconnected Obsidian knowledge base.
Your task is to analyze the provided text, determine its nature (e.g., article, research paper, meeting note, book excerpt, tutorial), and extract a comprehensive, well-structured markdown note.

DO NOT output a brief summary. I need detailed extraction of the core value, concepts, and data.

Strict Rules for Obsidian Integration:
1. WIKILINKS: Liberally use [[wikilinks]] for all important concepts, entities, frameworks, tools, people, and recurring themes. (e.g., [[Machine Learning]], [[Elon Musk]], [[React Router]]).
2. YAML: Always start with YAML frontmatter including relevant tags, the date, and the inferred document type.
3. ADAPTABILITY: If a section below does not apply to the text (e.g., no "data" in a philosophical essay), omit that section or adapt it logically. Do not invent information.

REQUIRED STRUCTURE:
---
tags:
  - [Tag 1]
  - [Tag 2]
doc_type: [Inferred type, e.g., Research, Article, Tutorial, Meeting]
date: [YYYY-MM-DD]
---

# [A highly descriptive title based on the content]

## 1. The TL;DR / Executive Summary
[A dense 2-3 paragraph synthesis of what this document is about, why it was written, and its primary conclusion.]

## 2. Core Concepts & Entities
[List and explain the main ideas, frameworks, or entities discussed. Use bullet points and ensure every major concept is wrapped in [[wikilinks]].]

## 3. Deep Dive: Key Insights & Arguments
[The core of the note. Break down the main arguments, methodologies, steps, or narrative points. Use subheadings (###) if the text is long. Extract the "meat" of the document.]

## 4. Notable Specifics (Data, Quotes, or Code)
[Extract high-value specifics. If it's a paper, include metrics/tables. If it's an article, pull the best direct quotes. If it's a tutorial, extract the core code snippets or terminal commands.]

## 5. Context & Applications (The "So What?")
[Why does this document matter? How can this information be applied? What are the implications or next steps?]
    """),
    ("human", "Here is the raw text to process:\n\n{raw_text}")
])

# chain = schema_prompt | llm

def extract_text_from_file(file_path):
    print(f"Extracting text from {os.path.basename(file_path)}...")
    md = MarkItDown()
    try:
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def processDocument(file_path,userKey):
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=userKey,
    temperature=0.2
    )
    chain = schema_prompt | llm

    text_document = extract_text_from_file(file_path)

    if not text_document:
        raise Exception("Could not extract text from document.")
    
    print("AI is analyzing and writing markdown...")
    response = chain.invoke({"raw_text": text_document})
    
    return response.content