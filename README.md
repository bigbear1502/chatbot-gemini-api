# chatbot-gemini-api

AI Chat Assistant - Setup and Installation Guide
This is a simple Q&A chat application that uses React for the frontend and Python with the Gemini API for the backend.
Prerequisites

Node.js (v14 or higher)
npm or yarn
Python (v3.8 or higher)
Google API key for Gemini

Setting Up the Project
1. Frontend Setup (React + Vite)

        cd chatbot-frontend

      Install the necessary dependencies:
      
          bash npm install
      
      Start the development server:
      
          bash npm run dev
      The frontend should now be running at http://localhost:3000.

2. Backend Setup (Python + Flask + Gemini API)

        cd chatbot-backend

      Create a virtual environment and activate it:
      
          bash python -m venv venv
      
          # On Windows
          venv\Scripts\activate
          
          # On macOS/Linux
          source venv/bin/activate
      
      Install the dependencies:
      
          bash pip install -r requirements.txt
      
      Add your Google API key in .env file:
      
          GOOGLE_API_KEY=your_google_api_key_here
      
      Start the Flask server:
      
          bash python app.py
      The backend should now be running at http://localhost:5000.
