# facility_maintenance_chatbots_bot2
Work Order Planner: Facility Manager's Bot

### To run this app locally:
Clone this repository
- Create a virtual environment: python -m venv venv
- Activate the virtual environment: . venv/bin/activate
- Install requirements: pip install -r requirements.txt

Sign up for an OpenAI API key and Azure OpenAI API key
- paste them into the codes:
  

OPENAI_API_KEY="sk-..."
Run the app: streamlit run app.py
The app should now be running on http://localhost:8501

Main Script: app_bot1_v.py
To run the script: streamlit run app_bot1_v.py

At the same time, run the databricks LLM proxy server (flask) api locally or in a server: python flask_llm_mpt.py

Feel free to tweak the OpenAI model and parameters in app_bot1_v.py to experiment with different conversational AI engines.



Features
The app allows you to:

Directly chat with the AI assistant
View chat history and clear full history
Override temperature setting
Compare different model responses
Contributing
Pull requests are welcome! Here are some ways you can contribute:

Try out different OpenAI models
Add support for other conversational AI APIs
Improve UI/UX
Fix bugs or add new features by opening issues
