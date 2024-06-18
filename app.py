import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
from langchain.chains import ConversationalRetrievalChain
from htmltemplates import css, bot_template, user_template

# Step 1: Extract text from PDF files
def get_pdf_text(pdf_files):
    text = ""
    for pdf in pdf_files:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Step 2: Split text into chunks
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Step 3: Create vector store using HuggingFaceEmbeddings
def get_vector_store(text_chunks):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

# Step 4: Set up conversation chain with Llama 2 from Ollama
def get_conversation_chain(vectorstore):
    llm = Ollama(model="llama2")
    # Check if the model is available
    try:
        llm.invoke("tell me a joke")
    except Exception as e:
        st.error(f"Failed to initialize the LLM model: {e}")
        return None
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
    )
    return conversation_chain

def handle_userinput(user_question):
    if st.session_state.conversation:
        response = st.session_state.conversation({'question': user_question})
        st.session_state.chat_history = response['chat_history']
        for i, message in enumerate(st.session_state.chat_history):
            if i % 2 == 0:  
                st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            else:
                st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
    else:
        st.error("Conversation is not initialized. Please upload and process your PDFs first.")

def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.header("Chat with multiple PDFs :books:")
    user_question = st.text_input("Ask a question about your document: ")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Your Documents")
        pdf_files = st.file_uploader("Upload your PDFs here and Click on 'Process'", accept_multiple_files=True)
        
        if st.button("Process"):
            with st.spinner("Processing..."):
                # Step 5: Process the PDFs
                raw_text = get_pdf_text(pdf_files)
                text_chunks = get_text_chunks(raw_text)
                vector_store = get_vector_store(text_chunks)
                conversation_chain = get_conversation_chain(vector_store)
                if conversation_chain:
                    st.session_state.conversation = conversation_chain
                else:
                    st.error("Failed to create conversation chain. Check the logs for more details.")

if __name__ == "__main__":
    main()