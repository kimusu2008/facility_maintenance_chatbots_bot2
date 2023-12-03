import streamlit as st
import asyncio
import os
import requests
import json
from autogen import AssistantAgent, UserProxyAgent, GroupChatManager, GroupChat
import autogen
import openai
import re

st.set_page_config(layout="wide")

st.write("""# Work Order Planner: Facility Manager's Bot """)

tab1, tab2 = st.tabs(["Show Main Conversations", "Show All Conversations"])

class TrackGroupChatManager(GroupChatManager):
    def _process_received_message(self, message, sender, silent):

        with tab1:
            if ( ('UserProxyAgent' in str(sender)) & ~(('exitcode' in str(message)) or ('if the task is done' in str(message)))  ):            
                with st.chat_message('Requestor', avatar="👨🏻‍💼"):
                    st.markdown(''' :blue[{}]'''.format(message))
            
            elif( ('AssistantAgent' in str(sender)) & ~('pandas' in str(message)) ):
                with st.chat_message('Assistant', avatar="🤖"):
                    st.markdown(':green[{}]'.format(re.sub(r'\[.*?\]', '', message)) )
        
        with tab2:
            if ( 'UserProxyAgent' in str(sender) ):            
                with st.chat_message('Requestor', avatar="👨🏻‍💼"):
                    st.markdown(''' :blue[{}]'''.format(message))
            
            elif( 'AssistantAgent' in str(sender) )  :
                with st.chat_message('Assistant', avatar="🤖"):
                    st.markdown(':green[{}]'.format(re.sub(r'\[.*?\]', '', message)) )

        return super()._process_received_message(message, sender, silent)


selected_model = None
selected_key = 'sk'

st.markdown("""
<style>
    [data-testid=stSidebar] {
        background-color: #FFA500;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("LLM Model Selection")
    selected_model = st.selectbox("Model", ['gpt-3.5-turbo', 'gpt-4-32k'], index=1)
    #uploaded_file = st.file_uploader("Choose an Image ...", type="jpg")

config_list = [
    {
        'model': selected_model,
        'api_key': 'f84978cd0c4f4006beabfbc6aadf8c06',
        "base_url": "https://cog-keslq7urc6ly4.openai.azure.com/",
        "api_type": "azure",
        "api_version": "2023-05-15"
    }
]

user_input = st.chat_input("Hello, Site Admin, please provide your request...")  

with st.container():

    if user_input:
        if not selected_key or not selected_model:
            st.warning(
                'You must provide valid OpenAI API key and choose preferred model', icon="⚠️")
            st.stop()

        termination_msg = (lambda x: isinstance(x, dict) and "TERMINATE" == str(x.get("content", ""))[-9:].upper()) or (lambda x: x.get("content", "").rstrip().endswith("TERMINATE")) or x.get("content", "").strip() == ""

        site_admin = autogen.UserProxyAgent(
           name="site_admin",
           system_message="A human site_admin who works with planner, and helpdesk_asset to plan resource allocation, I will execute codes suggested by planner too. Reply `TERMINATE` in the end when the task is completed",
           code_execution_config={"last_n_messages": 3, "work_dir": "groupchat_bot2", "use_docker": False},
           #code_execution_config = False,
           human_input_mode="NEVER",
           max_consecutive_auto_reply = 4,
           #llm_config={"config_list": config_list, "temperature": 0},
           llm_config=False,
           default_auto_reply="Reply `TERMINATE` if the task is done.",
           is_termination_msg=termination_msg,)

        planner = autogen.AssistantAgent(
            name="planner",  # the default assistant agent is capable of solving problems with code
            system_message="""A planner who suggests codes for reading CSV files and analyzing data in CSV files to answer the inquiry raised by site_admin.

                The are two databases 1) Agent list in the 'Agent List.csv' database 2) Historical and new work orders in the 'WO_Nov_bot2.csv' database.
                
                The 'WO_Nov_bot2.csv' work order database has the latest historical and new work order issues. Treat the data in this CSV file as our database, and make sure you import the required Python libraries such as Pandas, fuzzywuzzy, and datetime.
                The 'WO_Nov_bot2.csv' work order database has the following columns and their definitions:
                - assetName: name of the asset in terms of asset type
                - assetSkills: required skill to maintain each asset
                - assetFloor: floor location of assets
                - assetBuildingFloorLocation: detailed location of assets
                - workOrderNumber: it's an incremental number in the CSV file
                - subject: maintenance issue that needs resolution
                - status: current status of resolution; it's either resolved, ongoing, or not yet started
                - actualStartDateTime: actual start date of resolution; if the job status is not yet started, keep the value empty
                - workOrderPrimaryAgentName: Technician assigned to the job
                - createdDate: the job created date and time; when converting the data type of createdDate, please use .strftime('%Y-%m-%d')
                - createdBy: the requester's name
                - totalWorkTime: if a job's status is resolved, this is the duration of maintenance work in minutes
                - resolutionType: resolution status
                - resolvedDate: resolution date
                - satisfactionRating: rating from the requester
                - resolutionNotes: remarks from the maintenance work order

                The 'Agent List.csv' technician database has the detiled information of all on site technicians. Treat the data in this CSV file as our database, and make sure you import the required Python libraries such as Pandas, fuzzywuzzy, and datetime.
                The 'Agent List.csv' technician database has the following columns and their definitions:
                - Skills: required skill to maintain each asset, this field is a matching column with assetSkills in the 'WO_Nov_bot2.csv' work order database
                - AgentName: Technician assigned to the job, this field is a matching column with workOrderPrimaryAgentName in the 'WO_Nov_bot2.csv' work order database


                There are two separate tasks, do not try to resolve both tasks if site_admin only asks for one task. 

                Task 1:
                    site_admin will request analytics results of the 'WO_Nov_bot2.csv' work order database and 'Agent List.csv' technician database, so generate query codes in python that can answer such questions. Please convert all string values to lowercase first using the .lower() method.

                Task 2: 
                    To identify new work orders in the 'WO_Nov_bot2.csv' work order database, and fill in the empty workOrderPrimaryAgentName value based on two conditions:
                        - Condition #1: For new work orders, the 'assetSkills' column value in the 'WO_Nov_bot2.csv' work order database needs to match with the 'Skills' column value in the 'Agent List.csv' technician database
                        - Condition #2: Make sure the agents in the technician database are not occupied as of now, check the 'createdDate' of historical work orders in the 'WO_Nov_bot2.csv' work order database, and compare it against the current date, to ensure the available agents are free . Only select non occupied agent, if there are more than one agent, just randomly select one.
                
                    Finally, for the new work orders, update the 'WO_Nov_bot2.csv' work order database by filling up the 'workOrderPrimaryAgentName' column values.
                    When comparing strings, use the fuzzywuzzy library with a fuzzy matching percentage of 75% for column names matching. Please convert all string values to lowercase first using the .lower() method.
                    When updating the 'WO_Nov_bot2.csv' database, it means updating the CSV file with new rows. Please do not use the append method; instead, use the loc or concat method to add new records to the dataframe.

                
                You will suggest the codes and provide the code to 'helpdesk_asset' for review. The site_admin will execute the code, you will not execute the code.
            """,
            #code_execution_config={"last_n_messages": 2, "work_dir": "groupchat", "use_docker": False},
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=termination_msg,)


        helpdesk_asset = autogen.AssistantAgent(
            name="helpdesk_asset",
            system_message="""The primary focus of the Help Desk is centered around Asset Listing.

                As a capable assistant, your role is to ensure that the code suggested by the planner is executed by site_admin. You should possess strong expertise in evaluating the results of the code execution for the site_admin without suggesting code to the planner. 

                site_admin will execute the code.

                There are two tasks, Your responsibilities include interacting with the site_admin and planner to accomplish these two tasks:

                    Task 1:
                        site_admin will request analytics results of the 'WO_Nov_bot2.csv' work order database and 'Agent List.csv' technician database, so generate query codes in python that can answer such questions.

                    Task 2: 
                        First, to identify new work orders in the 'WO_Nov_bot2.csv' work order database, and fill in the empty workOrderPrimaryAgentName value based on two conditions:
                            - Condition #1: For new work orders, the 'assetSkills' column value in the 'WO_Nov_bot2.csv' work order database needs to match with the 'Skills' column value in the 'Agent List.csv' technician database
                            - Condition #2: Make sure the agent in the 'Agent List.csv' technician database is not occupied the 'createdDate' of the new work orders. Only select non occupied agent, if there are more than one agent, just randomly select one.
                        Second, for the new work orders, update the 'WO_Nov_bot2.csv' work order database by filling up the 'workOrderPrimaryAgentName' column values.

                Once the tasks is concluded, update site_admin about the request status, and print out 'TERMINATE' in your response and terminate this conversation.
                
                It is essential to conclude the conversation if the planner recommends terminating the loop.
                
                Your primary responsibility is to assist the planner and site_admin in determining which agents should be assigned to which work orders. 
                
                Please refrain from providing actual code solutions to the planner, and there is no need for data validation or error logging.
                
                Please refrain from recommending codes to the planner.
            """,
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=termination_msg,)


        groupchat = GroupChat(agents=[site_admin, helpdesk_asset, planner], messages=[], max_round=30)
        manager = TrackGroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list, "temperature": 0})

        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Define an asynchronous function
        async def initiate_chat():
            await site_admin.a_initiate_chat(
                manager,
                message=user_input,
            )

        # Run the asynchronous function within the event loop
        #asyncio.run(initiate_chat())
        loop.run_until_complete(initiate_chat())


