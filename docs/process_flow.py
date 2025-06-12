from graphviz import Digraph

# --- 1. Create the main graph object ---
dot = Digraph(
    comment="Zenfi AI Process Flow",
    format="png",
    graph_attr={
        "rankdir": "TB",
        "splines": "ortho",
        "bgcolor": "#fdfdfd",
        "label": "Zenfi AI: User Request Process Flow",
        "labelloc": "t",
        "fontsize": "24",
        "fontname": "Helvetica, Arial, sans-serif",
        "concentrate": "true",  # Tries to merge parallel edges
    },
    node_attr={
        "style": "filled,rounded",
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "11",
    },
    edge_attr={
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "9",
        "color": "#444444",
    },
)

# --- 2. Define Node Styles ---
user_action_style = {
    "shape": "parallelogram",
    "fillcolor": "#e6f7ff",
    "color": "#007acc",
}
frontend_style = {"shape": "box", "fillcolor": "#d1f0ff", "color": "#0099e6"}
backend_style = {"shape": "box", "fillcolor": "#e6ffe6", "color": "#00994d"}
ai_core_style = {"shape": "box", "fillcolor": "#fff0e6", "color": "#ff6600"}
decision_style = {
    "shape": "diamond",
    "fillcolor": "#fffacd",
    "color": "#e6b800",
    "width": "2.5",
    "height": "1.2",
}
data_style = {"shape": "cylinder", "fillcolor": "#f2e6ff", "color": "#8000ff"}
final_output_style = {"shape": "ellipse", "fillcolor": "#d4edda", "color": "#155724"}


# --- 3. Create a Legend ---
with dot.subgraph(name="cluster_legend") as legend:
    legend.attr(label="Legend", style="rounded", color="lightgrey")
    legend.node("user_action_key", "User Action", **user_action_style)
    legend.node("frontend_key", "Frontend Step", **frontend_style)
    legend.node("backend_key", "Backend Step", **backend_style)
    legend.node("ai_core_key", "AI Core Step", **ai_core_style)
    legend.node("decision_key", "Decision Point", **decision_style)
    legend.node("data_key", "Data Store", **data_style)
    legend.node("output_key", "Final Output", **final_output_style)
    legend.edge("user_action_key", "frontend_key", style="invis")
    legend.edge("frontend_key", "backend_key", style="invis")
    legend.edge("backend_key", "ai_core_key", style="invis")
    legend.edge("ai_core_key", "decision_key", style="invis")
    legend.edge("decision_key", "data_key", style="invis")
    legend.edge("data_key", "output_key", style="invis")


# --- 4. Define the Process Flow Nodes ---

# Start Node
dot.node("start", "User Initiates Action", shape="oval", fillcolor="#cce5ff")

# --- Flow 1: Quick Search (ChatService) ---
with dot.subgraph(name="cluster_quick_search") as qs:
    qs.attr(
        label="Flow: Quick Search (ChatService)",
        style="filled",
        color="#e6f7ff",
        bgcolor="#f5fcff",
    )

    # Frontend
    qs.node("fe_chat_input", "User enters query in Chat UI", **user_action_style)
    qs.node(
        "fe_api_call", "Next.js API Route (/api/chat) sends request", **frontend_style
    )

    # Backend
    qs.node(
        "be_gateway", "FastAPI Gateway receives request\nValidates JWT", **backend_style
    )
    qs.node(
        "be_route_to_chat_service", "Route to ChatService LangGraph", **backend_style
    )

    # AI Core - Pre-processing & Routing
    qs.node(
        "ai_check_portfolio", "Check if query needs portfolio data", **decision_style
    )
    qs.node("ai_get_portfolio", "Tool: Get Portfolio Data", **ai_core_style)
    qs.node("db_portfolio", "Query Portfolio DB (Postgres)", **data_style)

    qs.node(
        "ai_check_kb", "Check if query needs Knowledge Base (RAG)", **decision_style
    )
    qs.node("ai_search_kb", "Tool: Search KB", **ai_core_style)
    qs.node("db_bigquery", "Vector Search (BigQuery)", **data_style)

    qs.node("ai_check_python", "Check if query needs Python code", **decision_style)
    qs.node("ai_python_subflow", "Generate & Execute Python Code", **ai_core_style)

    qs.node("ai_check_web", "Check if query needs Web Search", **decision_style)
    qs.node("ai_web_search", "Tool: Perform Web Search", **ai_core_style)

    # AI Core - Main Loop
    qs.node("ai_call_model", "Invoke LLM (Gemini) with context", **ai_core_style)
    qs.node("ai_check_tool_use", "Does response require a tool?", **decision_style)
    qs.node(
        "ai_tool_node",
        "Execute Financial/Basic Tools\n(yfinance, YouTube, etc.)",
        **ai_core_style,
    )

    # Output
    qs.node("be_stream_response", "FastAPI streams response back", **backend_style)
    qs.node(
        "fe_display_response", "Chat UI displays streaming tokens", **final_output_style
    )

# --- Flow 2: Deep Search (DeepSearchService) ---
with dot.subgraph(name="cluster_deep_search") as ds:
    ds.attr(
        label="Flow: Deep Search (DeepSearchService)",
        style="filled",
        color="#fff5e6",
        bgcolor="#fffaf0",
    )

    ds.node(
        "fe_deep_search_input",
        "User enables 'Deep Research' & submits topic",
        **user_action_style,
    )
    ds.node(
        "be_route_to_deep_search",
        "Route to DeepSearchService LangGraph",
        **backend_style,
    )

    ds.node("ai_plan_report", "1. Plan Report\n(Initial Web Search)", **ai_core_style)
    ds.node(
        "ai_dispatch_sections",
        "2. Dispatch Sections for Parallel Research",
        **ai_core_style,
    )
    ds.node(
        "ai_research_loop",
        "3. Research Loop (per section)\n(Query -> Search -> Write -> Grade)",
        **ai_core_style,
    )
    ds.node("ai_compile_report", "4. Compile Final Report", **ai_core_style)
    ds.node("be_stream_report", "FastAPI streams final report", **backend_style)
    ds.node("fe_display_report", "Chat UI displays final report", **final_output_style)

# --- 5. Connect the Nodes with Edges ---

# Main entry point
dot.edge("start", "fe_chat_input", label="Standard Chat")
dot.edge("start", "fe_deep_search_input", label="Report Generation")

# Quick Search Flow
dot.edge("fe_chat_input", "fe_api_call")
dot.edge("fe_api_call", "be_gateway")
dot.edge("be_gateway", "be_route_to_chat_service")
dot.edge("be_route_to_chat_service", "ai_check_portfolio")

# Conditional routing in ChatService
dot.edge("ai_check_portfolio", "ai_get_portfolio", xlabel="Yes")
dot.edge("ai_get_portfolio", "db_portfolio")
dot.edge("db_portfolio", "ai_check_kb")
dot.edge("ai_check_portfolio", "ai_check_kb", xlabel="No")

dot.edge("ai_check_kb", "ai_search_kb", xlabel="Yes")
dot.edge("ai_search_kb", "db_bigquery")
dot.edge("db_bigquery", "ai_check_python")
dot.edge("ai_check_kb", "ai_check_python", xlabel="No")

dot.edge("ai_check_python", "ai_python_subflow", xlabel="Yes")
dot.edge("ai_python_subflow", "ai_check_web")
dot.edge("ai_check_python", "ai_check_web", xlabel="No")

dot.edge("ai_check_web", "ai_web_search", xlabel="Yes")
dot.e_attr = {"lhead": "cluster_quick_search"}  # Direct arrow to the cluster boundary
dot.edge("ai_web_search", "ai_call_model")
dot.edge("ai_check_web", "ai_call_model", xlabel="No")

# Main AI processing loop
dot.edge("ai_call_model", "ai_check_tool_use")
dot.edge("ai_check_tool_use", "ai_tool_node", xlabel="Yes")
dot.edge("ai_tool_node", "ai_call_model", xlabel="Return Tool Result")  # Loop back
dot.edge("ai_check_tool_use", "be_stream_response", xlabel="No (Final Answer)")

# Final response path
dot.edge("be_stream_response", "fe_display_response")

# Deep Search Flow
dot.edge(
    "fe_deep_search_input", "fe_api_call"
)  # Re-uses the same frontend API call mechanism
dot.edge("be_gateway", "be_route_to_deep_search")  # Alternative routing from gateway
dot.edge("be_route_to_deep_search", "ai_plan_report")
dot.edge("ai_plan_report", "ai_dispatch_sections")
dot.edge("ai_dispatch_sections", "ai_research_loop")
dot.edge("ai_research_loop", "ai_compile_report", xlabel="All sections complete")
dot.edge("ai_compile_report", "be_stream_report")
dot.edge("be_stream_report", "fe_display_report")


# --- 6. Render the graph ---
output_filename = "zenfi_ai_process_flow"
dot.render(output_filename, view=False)

print(f"Process flow diagram saved as {output_filename}.png")
