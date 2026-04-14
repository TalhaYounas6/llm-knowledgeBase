import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from markitdown import MarkItDown


load_dotenv()


OUTPUT_FOLDER = "./Wiki_Notes"


os.makedirs(OUTPUT_FOLDER,exist_ok=True)



llm = ChatGoogleGenerativeAI(
    model = "gemini-2.5-flash",
    temperature = 0.2
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

def extract_text_from_file (file_path):
    print(f"Reading document {file_path}")
    md = MarkItDown()
    try:
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        print(f"Error reading file {file_path}")
        return None


def processDocument (file_path):
    
    filename = os.path.basename(file_path)
    md_filename = os.path.splitext(filename)[0] + ".md"
    output_path = os.path.join(OUTPUT_FOLDER, md_filename)

    text_document = extract_text_from_file(file_path)

    if not text_document:
        return
    
    print("AI is reading")

    response = chain.invoke({"raw_text": text_document})

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.content)

    print("Done and saved.")    

# --- Test the Engine ---
# if __name__ == "__main__":
#     # A dummy piece of text to simulate a raw PDF or article
#     # sample_article = """
#     # React Native is a popular framework developed by Meta. It allows developers to 
#     # build mobile apps using JavaScript and React. Unlike standard web apps, it renders 
#     # using native components, which improves performance. It is often used alongside 
#     # backends built with Node.js and PostgreSQL.
#     # """
    
#     # input_file = r"C:\Users\Talha Younas\Downloads\Lec 10 - Artificial Neural Network.pdf"
#     # outputfile = "AI_Notes.md"
#     if os.path.exists(input_file):

#         processDocument(input_file, outputfile)
#     else:
#         print(f"{input_file} does not exist.")            