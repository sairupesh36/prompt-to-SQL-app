import streamlit as st
import mysql.connector
import pandas as pd
from dotenv import load_dotenv
import os
import faiss
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Load Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Initialize Gemini model and SentenceTransformer for embeddings
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-pro')
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Database connection configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "atliq_tshirts",
    "port": 3306
}

# Function to get table names
def get_tables():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = [table[0] for table in cursor.fetchall()]
    cursor.close()
    conn.close()
    return tables

# Function to get data from a table
def get_table_data(table_name):
    conn = mysql.connector.connect(**db_config)
    query = f"SELECT * FROM {table_name};"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Sample SQL queries and descriptions
sql_samples = [
    {"query": "SELECT SUM(price * stock_quantity) FROM t_shirts WHERE brand = 'Nike' AND color = 'Black';", "description": "Total cost of black Nike t-shirts."},
    {"query": "SELECT sum(stock_quantity) FROM t_shirts WHERE brand = 'Levi' AND color = 'White';", "description": "Stock quantity of white Levi t-shirts."},
    {"query": "SELECT SUM(price * stock_quantity) FROM t_shirts WHERE size = 'S';", "description": "Total price of small-sized t-shirts."},
    {"query": "SELECT sum(a.total_amount * ((100-COALESCE(discounts.pct_discount,0))/100)) as total_revenue from (select sum(price*stock_quantity) as total_amount, t_shirt_id from t_shirts where brand = 'Levi' group by t_shirt_id) a left join discounts on a.t_shirt_id = discounts.t_shirt_id;", "description": "Total revenue from Levi t-shirts considering discounts."}
]

# Create embeddings for the descriptions
descriptions = [sample["description"] for sample in sql_samples]
embeddings = embedding_model.encode(descriptions, convert_to_tensor=True)

# Build FAISS index
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings.cpu().detach().numpy())

# Function to retrieve SQL query based on user input
def get_sql_query(user_input):
    user_embedding = embedding_model.encode(user_input, convert_to_tensor=True)
    D, I = index.search(user_embedding.cpu().detach().numpy().reshape(1, -1), 1)
    return sql_samples[I[0][0]]["query"]

# Function to execute the SQL query
def read_sql_query(sql_query, db_config):
    conn = mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        port=db_config.get("port", 3306)
    )
    cur = conn.cursor()
    cur.execute(sql_query)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description] if cur.description else []
    cur.close()
    conn.close()
    return rows, columns

# Configure the Streamlit page
st.set_page_config(page_title="SQL Query Generator")
st.title("Prompt-to-SQL Query Generator")

# Display all tables side by side
tables = get_tables()
if tables:
    cols = st.columns(len(tables))
    for idx, table_name in enumerate(tables):
        with cols[idx]:
            st.subheader(f"Table: {table_name}")
            table_data = get_table_data(table_name)
            st.dataframe(table_data)
else:
    st.warning("No tables found in the database.")

# Input box for the user’s question
# st.header("Prompt-to-SQL Query Generator")
question = st.text_input("Enter your question regarding the table:")
submit = st.button("Submit")

if submit and question:
    prompt_for_sql = f"""
    Your task is to convert the following text into a SQL query.
    The SQL query must use only the column names mentioned in the prompt and must not include any commentary or explanation.
    Return only the SQL query without any extra text.
    Here are some examples of valid SQL queries:
    --- Query 1 ---
    SELECT sum(stock_quantity) FROM t_shirts WHERE brand = 'Nike' AND color = 'White' AND size = 'XS';
    --- Query 2 ---
    SELECT SUM(price*stock_quantity) FROM t_shirts WHERE size = 'S';
    --- Query 3 ---
    SELECT sum(a.total_amount * ((100-COALESCE(discounts.pct_discount,0))/100)) as total_revenue from (select sum(price*stock_quantity) as total_amount, t_shirt_id from t_shirts where brand = 'Levi' group by t_shirt_id) a left join discounts on a.t_shirt_id = discounts.t_shirt_id;
    --- Query 4 ---
    SELECT SUM(price * stock_quantity) FROM t_shirts WHERE brand = 'Levi';
    --- Query 5 ---
    SELECT sum(stock_quantity) FROM t_shirts WHERE brand = 'Levi' AND color = 'White';

    Now, convert the following text into a SQL query:
    {question}
    """

    try:
        sql_query = model.generate_content(prompt_for_sql).text
    except Exception as e:
        st.error(f"Error generating SQL query: {e}")
        st.stop()

    if not sql_query.strip().lower().startswith("select"):
        sql_query = get_sql_query(question)

    st.subheader("Generated SQL Query")
    st.code(sql_query, language="sql")

    try:
        result_rows, columns = read_sql_query(sql_query, db_config)
    except Exception as e:
        st.error(f"SQL execution error: {e}")
        st.stop()

    st.subheader("Query Result")
    if result_rows:
        df = pd.DataFrame(result_rows, columns=columns)
        st.table(df)
    else:
        st.write("No results returned from the query.")
