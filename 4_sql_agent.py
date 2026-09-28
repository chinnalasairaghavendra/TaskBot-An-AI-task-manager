from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
import streamlit as st

load_dotenv()

db=SQLDatabase.from_uri("sqlite:///my_tasks.db")
db.run("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT CHECK (status IN('pending','in progress','completed')) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
    )
""")
llm=ChatGroq(model="openai/gpt-oss-120b")
toolkit=SQLDatabaseToolkit(db=db,llm=llm)
tools=toolkit.get_tools()
memory=InMemorySaver()
system_prompt="""You are a task management assisstant that interacts with a SQL database containing 'tasks' table.
TASK RULES:
1. Limit SELECT queries upto 10 results max with ORDER BY created_at DESC
2. After CREATE/UPDATE/DELETE, confirm with the select queries
3. If user requests a list of tasks ,present the output in a structured table markdown format to ensure a clean display on the browser

CRUD OPERATIONS:
    CREATE: INSERT INTO tasks(title, description, status)
    UPDATE: UPDATE tasks SET status=? WHERE id=? or title=?
    READ: SELECT * from tasks WHERE ... LIMIT 10
    DELETE: DELETE from tasks WHERE id=? OR title=?
    
Table Schema: id,title,desription,status(pending,in progress,completed), created_at.""" 

@st.cache_resource
def get_agent():
    agent=create_agent(model=llm,
                    tools=tools,
                    checkpointer=memory,
                    system_prompt=system_prompt)
    return agent

agent=get_agent()
st.subheader("TaskBot-Manage your tasks")

if 'messages' not in st.session_state:
    st.session_state.messages=[]

for message in st.session_state.messages:
    st.chat_message(message["role"]).markdown(message["content"])
prompt=st.chat_input("Ask me to manage your tasks")
if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("ai"):
        with st.spinner("Processing..."):
            response=agent.invoke({"messages":[{"role":"user","content":prompt}]},{"configurable":{"thread_id":"1"}})
            result=response["messages"][-1].content
            st.session_state.messages.append({"role":"ai","content":result})
            st.markdown(result)
    
