import operator
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain.messages import RemoveMessage
from langchain_fireworks import ChatFireworks
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Overwrite

from src.resubmission.prompt import chatbot_prompt, justification_prompt

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


class InsuranceAgent:
    def __init__(
        self,
        model="accounts/fireworks/models/gpt-oss-120b",
        message_window=3,  # For debugging/development purposes, replace with a more reasonable window for production
    ):
        self.llm = ChatFireworks(
            model=model,
            temperature=0.2,
            max_tokens=10000,
            model_kwargs={
                "stream": True
            },  # Using stream to escape Fireworks error "Requests with max_tokens > 4096 must have stream=true"
            request_timeout=(120, 120),
        )
        self.message_window = message_window

        graph = StateGraph(AgentState)

        graph.add_node("llm", self._call_llm)
        graph.add_node("replace_messages", self._replace_messages)

        graph.set_entry_point("llm")

        graph.add_edge("llm", "replace_messages")
        graph.add_edge("replace_messages", END)

        checkpointer = InMemorySaver()
        self.graph = graph.compile(checkpointer=checkpointer)

    def _delete_messages(self, state: AgentState):
        """"
        A LangGraph node function, currently not used.
        LangGraph handles calling this function as part of the graph execution, applies the deletion as a reducer.
        Args:
            state (AgentState): They entire state dictionary
        Returns:
            Dict: A dictionary with the messages to delete from the state."""
        messages = state["messages"]
        if len(messages) > self.message_window:
            keep = messages[:3] + messages[-self.message_window :]
            to_remove = [m for m in messages if m not in keep]
            return {"messages": [RemoveMessage(id=m.id) for m in to_remove]}

    def _replace_messages(self, state: AgentState):
        """
        A LangGraph node function, must follow a specific signature.
        LangGraph handles calling this function as part of the graph execution.
        Args:
            state (AgentState): They entire state dictionary
        Returns:
            Dict: A dictionary with the new conversation history to replace the existing state with it
        """
        messages = state["messages"]
        if len(messages) > self.message_window:
            replacement = messages[:3] + messages[-self.message_window :]
        # Bypass the reducer and replace the entire messages list
        return {"messages": Overwrite(replacement)}

    def _call_llm(self, state: AgentState):
        """
        A LangGraph node function, must follow a specific signature.
        LangGraph handles calling this function as part of the graph execution.
        Args:
            state (AgentState): They entire state dictionary
        Returns:
            Dict: A dictionary with updates only to merge into the state
        """
        response = self.llm.invoke(state["messages"])
        return {"messages": [response]}

    def _get_thread_config(self, thread_id: str):
        """Helper to create thread configuration."""
        return {"configurable": {"thread_id": thread_id}}

    def _print_history(self, thread):
        """Helper to print the message history for debugging."""
        messages = self.graph.get_state(thread).values.get("messages", [])
        for i in range(len(messages)):
            print(f"{i+1}- {messages[i].__class__.__name__}:\n{messages[i].content}\n")

    def _is_first_call(self, thread) -> bool:
        """Check if this is the first call in the thread."""
        messages = self.graph.get_state(thread).values.get("messages", [])
        return len(messages) == 0

    def _add_system_context(self, thread, policy: str, visit_info: str):
        """Helper to add system context messages on the first call."""
        self.graph.update_state(
            thread,
            {
                "messages": [
                    SystemMessage(content=policy),
                    SystemMessage(content=chatbot_prompt),
                    SystemMessage(
                        content="Patient's info and services provided during the visit: "
                        + visit_info
                    ),
                ]
            },
        )

    def _stream(self, state, thread):
        """Helper to stream LLM responses."""
        full_response = ""
        for chunk, metadata in self.graph.stream(
            state, thread, version="v1", stream_mode="messages"
        ):
            if chunk.content:
                full_response += chunk.content

        return full_response

    def respond(self, thread_id: str, policy: str, visit_info: str, user_input: str):
        thread = self._get_thread_config(thread_id)

        # Add system context on FIRST call only, Subsequent calls: only send to the llm the new user message
        if self._is_first_call(thread):
            self._add_system_context(thread, policy, visit_info)
        state = {"messages": [HumanMessage(content=user_input)]}

        response = self._stream(state, thread)
        self._print_history(thread)
        return response

    def justify(self, thread_id: str, policy, visit_info, claim_info: str):
        thread = self._get_thread_config(thread_id)

        # Add system context on FIRST call only, Subsequent calls: only send to the llm the new user message
        if self._is_first_call(thread):
            self._add_system_context(thread, policy, visit_info)
        state = {
            "messages": [SystemMessage(content=justification_prompt + str(claim_info))]
        }

        response = self._stream(state, thread)

        self._print_history(thread)
        return response


_agent = InsuranceAgent()


def get_agent_response(
    user_input,
    thread_id,
    policy="",
    visit_info="",
    service=None,  # Optional parameter, in justify route only,
):
    """
    Call this inside your Flask chat route.
    Example:
        answer = get_agent_response(msg, session_id, policy, visit_info)
    """
    if user_input:
        return _agent.respond(
            thread_id=thread_id,
            policy=policy,
            visit_info=visit_info,
            user_input=user_input,
        )
    else:
        return _agent.justify(
            thread_id=thread_id,
            policy=policy,
            visit_info=visit_info,
            claim_info=service,
        )
