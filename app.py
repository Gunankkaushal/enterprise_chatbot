import os
from dotenv import load_dotenv
from services.pdf_loader import load_and_split_pdf
from services.embedder import create_vector_store
from services.chatbot import load_chatbot
from services.database.db_connection import documents_collection
from services.database.db_connection import chat_collection
load_dotenv()


# STEP 1: Read PDFs
all_chunks = []

for file in os.listdir("uploads"):
    if file.endswith(".pdf"):
        path = os.path.join("uploads", file)

        chunks = load_and_split_pdf(path)

# Add department metadata
department = file.split("_")[0]

documents_collection.insert_one({
    "filename": file,
    "department": department
})

for chunk in chunks:
        chunk.metadata["department"] = "HR"

all_chunks.extend(chunks)


# STEP 2: Create FAISS Vector Store
create_vector_store(all_chunks)


# STEP 3: Load Chatbot
role = input("Enter Department (HR/Finance/IT): ")

qa_bot = load_chatbot(role)

# STEP 4: Chat Loop
print("Enterprise Knowledge Chatbot Ready")

while True:
    query = input("\nAsk Question: ")

    if query.lower() == "exit":
        break

    response = qa_bot.invoke(query)

    print("\nAnswer:")
    print(response["result"])

    chat_collection.insert_one({
    "department": role,
    "query": query,
    "response": response["result"]
})

    print("\nSources:")

    for doc in response["source_documents"]:
        print(doc.metadata)