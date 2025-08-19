from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from typing import TypedDict, List, Optional, Annotated, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Qdrant
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_tavily import TavilySearch
from utils.langgraph_utils import *
import yaml

import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


LOG_FILE = r"D:\MediLearn_AI\logs\langgraph_flow.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger = logging.getLogger("pdf_loader")
logger.setLevel(logging.INFO)

# Only add handlers if not already set (prevents duplicate logs if rerun/imported)
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

web_search = TavilySearch(
    tavily_api_key="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", k=3
)


class State(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages]
    query_type: Optional[Literal["General", "Medical"]] = None
    rag_doc: Annotated[
        Optional[List[str]], "If LLM thinks query is related to medical field"
    ] = None
    web_doc: Annotated[
        Optional[List[str]],
        "If LLM thinks query is medical field but RAG documents are not enough",
    ] = None


# Node Classify Query
def classify_query(state: State) -> State:
    """This Function Checks weather the user message is related to Medical Field or General and categorize accordingly"""
    logger.info("Classifying the User Message..")

    # Get the latest user message
    latest_message = state.messages[-1].content

    class Classify(BaseModel):
        cls_msg: Annotated[
            Literal["General", "Medical"],
            Field(description='Classify the user message into "General" or "Medical"'),
        ]

    structured_cls_llm = llm.with_structured_output(Classify)
    response = structured_cls_llm.invoke(
        f"""
        Classify the following user message as either "General" or "Medical".
        
        Guidelines:
        - "Medical" if the message is about health, symptoms, diseases, treatments, medications, medical advice, or any health-related topic
        - "General" for all other topics like greetings, general questions, casual conversation, etc.
        
        User message: "{latest_message}"
        
        
        """
    )
    logger.info(f"Classified User message as {response.cls_msg}")
    state.query_type = response.cls_msg
    return state


def if_general(state: State) -> State:
    """This Function node is triggered if user message is general"""
    logger.info("Chatting in General Manner because User Message is general")

    # Pass the entire conversation context to maintain continuity
    response = llm.invoke(state.messages)
    state.messages.append(response)
    return state


def rag_search(state: State) -> State:
    """This Function node is triggered if user message is medical related"""
    logger.info("Searching Knowledge Base For User Medical related query")

    # Get the latest user message for search
    query = state.messages[-1].content

    query_embedding = model.encode("passage: " + query, normalize_embeddings=True)
    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=5,
        with_payload=True,
        score_threshold=0.85,
    )
    retrieved_docs = [point.payload["text"] for point in results]

    if state.rag_doc is None:
        state.rag_doc = []

    logger.info("Found Some Documents Related to User Message Adding it to state")
    state.rag_doc.extend(retrieved_docs)

    return state


def answer_with_rag(state: State) -> State:
    """This Node uses rag retrived docs and passes to llm"""
    logger.info("Answering the user query with retrieved documents")

    context = "\n".join(state.rag_doc)
    latest_query = state.messages[-1].content

    # Include conversation history for context
    conversation_context = "\n".join(
        [
            f"{'User' if i % 2 == 0 else 'Assistant'}: {msg.content}"
            for i, msg in enumerate(state.messages[:-1])
        ]
    )

    prompt = f"""Previous conversation:
{conversation_context}

Answer the current medical query using the context below:
Context: {context}

Current Query: {latest_query}

Use simple yet medical language in a well-articulated manner that's easy to understand and provide utmost detail."""

    resp = llm.invoke(prompt)
    state.messages.append(resp)
    return state


def search_web(state: State) -> State:
    """Web search when RAG docs are insufficient"""
    logger.info(
        "No information was available in knowledge base for user message doing web search"
    )

    try:
        query = state.messages[-1].content
        results = web_search.invoke(query)

        # ✅ FIXED: Access the 'results' key which contains the list
        web_docs = []
        if isinstance(results, dict) and "results" in results:
            for r in results[
                "results"
            ]:  # Access results['results'], not results directly
                if isinstance(r, dict) and "content" in r:
                    web_docs.append(r["content"])

        # ✅ FIXED: Proper state update
        current_web_docs = state.web_doc or []
        updated_web_docs = current_web_docs + web_docs

        logger.info(f"Found {len(web_docs)} web search results")
        return state.model_copy(update={"web_doc": updated_web_docs})

    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return state.model_copy(update={"web_doc": []})


def answer_with_web(state: State) -> State:
    """Answer using web search results"""
    logger.info("Answering with web searched documents")

    context = "\n".join(state.web_doc)
    latest_query = state.messages[-1].content

    # Include conversation history for context
    conversation_context = "\n".join(
        [
            f"{'User' if i % 2 == 0 else 'Assistant'}: {msg.content}"
            for i, msg in enumerate(state.messages[:-1])
        ]
    )

    prompt = f"""Previous conversation:
{conversation_context}

Answer the current medical query using these web search results:
Context: {context}

Current Query: {latest_query}

Please provide a comprehensive and accurate medical response."""

    resp = llm.invoke(prompt)
    state.messages.append(resp)
    return state


def is_medical(state: State):
    """Check if query is medical"""
    logger.info("Checking if user message is medical or not")
    return state.query_type == "Medical"


def docs_found(state: State):
    """Check if RAG documents were found"""
    logger.info("Checking if knowledge base has any info related to user message..")
    return state.rag_doc is not None and len(state.rag_doc) > 0


# Graph Construction
workflow = StateGraph(State)

# Add nodes
workflow.add_node("classify_query", classify_query)
workflow.add_node("if_general", if_general)
workflow.add_node("rag_search", rag_search)
workflow.add_node("answer_with_rag", answer_with_rag)
workflow.add_node("search_web", search_web)
workflow.add_node("answer_with_web", answer_with_web)

# Add edges
workflow.add_edge(START, "classify_query")
workflow.add_conditional_edges(
    "classify_query", is_medical, {False: "if_general", True: "rag_search"}
)
workflow.add_conditional_edges(
    "rag_search", docs_found, {True: "answer_with_rag", False: "search_web"}
)
workflow.add_edge("search_web", "answer_with_web")
workflow.add_edge("answer_with_rag", END)
workflow.add_edge("answer_with_web", END)
workflow.add_edge("if_general", END)

# Initialize checkpointer for memory management
checkpointer = InMemorySaver()

# Compile graph with checkpointer
graph = workflow.compile(checkpointer=checkpointer)


def main():
    """Main chat loop with proper memory management"""
    print("MediLearn AI Chatbot with Memory")
    print("Type 'exit' or 'quit' to end the conversation\n")

    # Initialize configuration for thread management
    thread_id = "user_session_1"
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye! Take care!")
            break

        if not user_input:
            continue

        try:
            # Create user message
            user_message = HumanMessage(content=user_input)

            # Run graph with proper configuration - LangGraph will manage state
            result = graph.invoke({"messages": [user_message]}, config=config)

            # Bot reply
            bot_reply = result["messages"][-1].content
            print(f"Bot: {bot_reply}\n")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            print(f"Sorry, I encountered an error: {e}\n")


# def get_conversation_history(thread_id: str):
#     """Get conversation history for a specific thread"""
#     config = {"configurable": {"thread_id": thread_id}}
#     state = graph.get_state(config)

#     if state.values and "messages" in state.values:
#         return state.values["messages"]
#     return []


# def clear_conversation_history(thread_id: str):
#     """Clear conversation history for a specific thread"""
#     config = {"configurable": {"thread_id": thread_id}}
#     # Note: InMemorySaver doesn't have a direct clear method
#     # You might need to restart the application or use a different checkpointer
#     # for production use cases
#     pass


# if __name__ == "__main__":
#     main()
