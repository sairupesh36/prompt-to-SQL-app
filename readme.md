# TEXT TO SQL

This project is a Streamlit application that generates and executes SQL queries based on user input. It uses Google's Gemini model for natural language processing and FAISS for semantic search.

## Setup Instructions

Follow these steps to set up and run the application:

### 1. Create a Virtual Environment and Install Requirements

1. Open your command prompt (CMD) or terminal.
2. Navigate to your project directory.
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
5. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Create a `.env` File and Add the Gemini API Key

1. In your project directory, create a file named `.env`.
2. Open the `.env` file and paste the following line, replacing `YOUR_GEMINI_API_KEY` with your actual Gemini API key:
   ```env
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY
   ```

### 3. Set Up the MySQL Database

1. Open MySQL Workbench.
2. Connect to your local MySQL instance (usually named `Local instance MySQL80`).
3. Import your database:
   - Go to **File > Open SQL Script** and select your SQL database file.
   - Execute the script to create the database and tables.
4. In the **Schemas** section, right-click on your database and select **Set as Default Schema**.

### 4. Run the Streamlit Application

1. In your command prompt (make sure the virtual environment is activated), run the following command:
   ```bash
   streamlit run app.py
   ```
2. This will launch the Streamlit application in your default web browser.

 
