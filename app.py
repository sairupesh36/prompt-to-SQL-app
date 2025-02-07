from dotenv import load_dotenv
load_dotenv()
import os
import streamlit as st
import mysql.connector
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Load Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Initialize Gemini model and SentenceTransformer for embeddings
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-pro')
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

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
        user=db_config["username"],
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
st.header("Prompt-to-SQL Query Generator")

# Input box for the user’s question
question = st.text_input("Enter your question regarding the table:")
submit = st.button("Submit")

# MySQL database configuration
db_config = {
    "host": "localhost",
    "port": 3306,
    "database": "atliq_tshirts",
    "username": "root",
    "password": "root"
}

if submit and question:
    # Generate SQL query using Gemini model
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

    # Fallback to FAISS if Gemini model fails
    if not sql_query.strip().lower().startswith("select"):
        sql_query = get_sql_query(question)

    # Display the generated SQL query
    st.subheader("Generated SQL Query")
    st.code(sql_query, language="sql")

    # Execute the SQL query
    try:
        result_rows, columns = read_sql_query(sql_query, db_config)
    except Exception as e:
        st.error(f"SQL execution error: {e}")
        st.stop()

    # Display the results
    st.subheader("Query Result")
    if result_rows:
        df = pd.DataFrame(result_rows, columns=columns)
        st.table(df)
    else:
        st.write("No results returned from the query.")
