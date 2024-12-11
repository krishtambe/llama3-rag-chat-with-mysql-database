import streamlit as st
import requests
from mysql.connector import connect, Error

# Function to call Ollama's local server
def call_ollama(prompt, model="llama3.2:latest"):
    try:
        response = requests.post(
            "http://localhost:11434/",
            json={"model": model, "prompt": prompt}
        )
        response.raise_for_status()
        return response.json().get("response", "Error: No response from Ollama.")
    except requests.exceptions.RequestException as e:
        return f"Error: Unable to connect to Ollama server. {e}"

# Function to connect to the database
def connect_database(username, port, host, password, database):
    try:
        connection = connect(
            user=username,
            password=password,
            host=host,
            port=port,
            database=database
        )
        st.session_state.db = connection
        st.session_state.schema = get_database_schema()
        st.success("Database connected!")
    except Error as e:
        st.error(f"Error connecting to database: {e}")

# Function to fetch the database schema
def get_database_schema():
    if "db" in st.session_state:
        try:
            cursor = st.session_state.db.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            schema_info = []
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DESCRIBE {table_name};")
                columns = cursor.fetchall()
                schema_info.append(f"Table {table_name}:\n" + "\n".join([f"{col[0]} ({col[1]})" for col in columns]))
            return "\n\n".join(schema_info)
        except Error as e:
            return f"Error fetching schema: {e}"
    return "Please connect to the database first."

# Function to generate SQL from natural language
def get_query_from_llm(question):
    schema = st.session_state.schema
    prompt = f"""Below is the schema of the MySQL database. Write an SQL query based on the user's question.

{schema}

Question: {question}
SQL query:"""
    return call_ollama(prompt)

# Function to execute the query
def run_query(query):
    if "db" in st.session_state:
        try:
            cursor = st.session_state.db.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            return f"Error executing query: {e}"
    return "Please connect to the database first."

# Function to generate a response from the query result
def get_response_for_query_result(question, query, result):
    schema = st.session_state.schema
    prompt = f"""Below is the schema of the MySQL database and the result of the query. Write a natural language response.

{schema}

Question: {question}
SQL query: {query}
Result: {result}
Response:"""
    return call_ollama(prompt)

# Streamlit layout
st.set_page_config(page_icon="🤖", page_title="Local AI Agent for MySQL", layout="centered")

st.title("Chat with Your MySQL Database")

# Sidebar for database connection
with st.sidebar:
    st.header("Connect to Database")
    host = st.text_input("Host", value="localhost")
    port = st.text_input("Port", value="3306")
    username = st.text_input("Username", value="root")
    password = st.text_input("Password", type="password")
    database = st.text_input("Database", value="rag_test")
    connect_btn = st.button("Connect")

    if connect_btn:
        connect_database(username, port, host, password, database)

# Chat input and display
if "chat" not in st.session_state:
    st.session_state.chat = []

question = st.chat_input("Ask a question about your MySQL database")

if question:
    if "db" not in st.session_state or "schema" not in st.session_state:
        st.error("Please connect to the database first.")
    else:
        st.session_state.chat.append({"role": "user", "content": question})
        
        # Generate SQL query
        query = get_query_from_llm(question)
        st.write(f"Generated SQL: `{query}`")
        
        # Execute SQL query
        result = run_query(query)
        st.write(f"Query Result: `{result}`")
        
        # Generate response
        response = get_response_for_query_result(question, query, result)
        st.session_state.chat.append({"role": "assistant", "content": response})

# Display chat history
for chat in st.session_state.chat:
    st.chat_message(chat["role"]).markdown(chat["content"])
