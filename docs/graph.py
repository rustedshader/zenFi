from graphviz import Digraph

# --- 1. Define Tool Categories based on your project structure ---

# Tools from /backend/app/chat_provider/tools/
web_search_tools = [
    "google_search_tool",
    "brave_search_tool",
    "duckduckgo_search_run_tool",
    "duckduckgo_search_results_tool",
]

finance_tools = [
    "get_stock_currency",
    "get_stock_day_high/low",
    "get_stock_exchange",
    "get_stock_fifty_day_average",
    "get_stock_last_price/volume",
    "get_stock_market_cap",
    "get_stock_info",
    "get_stock_history",
    "get_stock_income_statement",
    "get_stock_options_chain",
    "get_stock_price_change",
    # (and many more from finance_tools.py)
]

news_tools = [
    "yahoo_finance_news_tool",
    "duckduckgo_news_search_tool",
    "fetch_finance_news",
]

rag_tools = [
    "get_user_portfolio_tool (RAG)",
    "query_knowledge_base (RAG)",
]

basic_tools = [
    "get_current_datetime",
    "youtube_search_tool",
    "python_sandbox_tool",
]


# --- 2. Helper function to generate HTML table rows for the tools node ---
def generate_table_rows(category, tools):
    # Using a bullet point (•) for better list formatting
    tools_list = "<br/>".join(f"• {tool}" for tool in tools)
    return f'<TR><TD ALIGN="LEFT" BGCOLOR="#f2f2f2"><B>{category}</B></TD><TD ALIGN="LEFT">{tools_list}</TD></TR>'


# --- 3. Generate the HTML label for the main "Tools" node ---
table_rows = [
    # FIX: Escaped '&' to '&' to prevent parsing errors
    generate_table_rows("Web and News Search", web_search_tools + news_tools),
    generate_table_rows("Financial Data", finance_tools),
    generate_table_rows("Retrieval-Augmented Generation (RAG)", rag_tools),
    # FIX: Escaped '&' to '&' to prevent parsing errors
    generate_table_rows("Utility and Execution", basic_tools),
]
tools_label = (
    f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
    f'<TR><TD COLSPAN="2" BGCOLOR="#e0e0e0"><B>Agent Tools</B></TD></TR>'
    f"{''.join(table_rows)}"
    f"</TABLE>>"
)

# --- 4. Create the main graph with enhanced styling ---
dot = Digraph(
    comment="Zenfi AI Full Stack Architecture",
    format="png",
    graph_attr={
        "rankdir": "TB",
        "splines": "ortho",
        "bgcolor": "#fafafa",
        "label": "Zenfi AI Full Stack Architecture",
        "labelloc": "t",
        "fontsize": "24",
        "fontcolor": "#333333",
        "fontname": "Helvetica, Arial, sans-serif",
    },
    node_attr={
        "shape": "box",
        "style": "filled,rounded",
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "12",
    },
    edge_attr={
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "10",
        "color": "#555555",
    },
)

# --- 5. Define Nodes and Clusters ---

# Top-level node for the user
dot.node(
    "user",
    label="User",
    shape="circle",
    style="filled",
    fillcolor="#cce5ff",
    fontcolor="#004085",
)

# Frontend Cluster
with dot.subgraph(name="cluster_frontend") as fe:
    fe.attr(
        label="Frontend (Next.js)", style="filled", color="#e6f7ff", bgcolor="#f0faff"
    )
    fe.node(
        "nextjs_ui",
        label="React Components\n(Chat UI, Portfolio, Watchlist, KB)",
        fillcolor="#d1f0ff",
    )
    fe.node(
        "nextjs_api",
        label="Next.js API Routes\n(BFF - Backend for Frontend)",
        fillcolor="#a3daff",
    )

# Backend Cluster
with dot.subgraph(name="cluster_backend") as be:
    be.attr(
        label="Backend (FastAPI)", style="filled", color="#e6ffe6", bgcolor="#f0fff0"
    )
    be.node(
        "fastapi_gateway",
        label="FastAPI Gateway\n(OAuth2, Routers)",
        fillcolor="#c2f0c2",
    )

    # AI Core Cluster (inside Backend)
    with be.subgraph(name="cluster_ai_core") as ai:
        ai.attr(
            label="AI Core (Langchain & LangGraph)",
            style="filled",
            color="#fff0e6",
            bgcolor="#fff5f0",
        )

        # Chat Service (Quick Search)
        with ai.subgraph(name="cluster_chat_service") as cs:
            cs.attr(label="ChatService (Quick Search)", style="filled", color="#ffe0cc")
            cs.node(
                "chat_service_graph",
                label="LangGraph State Machine\n(AppState)",
                shape="Mdiamond",
                fillcolor="#ffccb3",
            )
            cs.node(
                "chat_service_logic",
                label="Conditional Routing:\n- Portfolio Check\n- Knowledge Base Check\n- Python Code Check\n- Web Search Check",
                shape="rect",
                fillcolor="#ffccb3",
            )

        # Deep Search Service (Report Generation)
        with ai.subgraph(name="cluster_deep_search") as ds:
            ds.attr(
                label="DeepSearchService (Report Generation)",
                style="filled",
                color="#ffe0cc",
            )
            ds.node(
                "deep_search_graph",
                label="LangGraph State Machine\n(ReportState)",
                shape="Mdiamond",
                fillcolor="#ffccb3",
            )
            ds.node(
                "deep_search_logic",
                label="Report Generation Flow:\n1. Plan Report\n2. Dispatch Sections\n3. Research & Write\n4. Compile Final Report",
                shape="rect",
                fillcolor="#ffccb3",
            )

        ai.node("tools", label=tools_label, shape="plaintext", fillcolor="#ffffff")

# Data & Services Cluster
with dot.subgraph(name="cluster_data_services") as ds:
    ds.attr(
        label="Data Stores & External Services",
        style="filled",
        color="#f2e6ff",
        bgcolor="#f5f0ff",
    )
    ds.node(
        "postgres_primary",
        label="PostgreSQL\n(Users, Portfolios, Chat History)",
        shape="cylinder",
        fillcolor="#e0ccff",
    )
    ds.node(
        "postgres_checkpoint",
        label="PostgreSQL\n(LangGraph Checkpoints)",
        shape="cylinder",
        fillcolor="#e0ccff",
    )
    ds.node(
        "redis", label="Redis\n(API Caching)", shape="cylinder", fillcolor="#e0ccff"
    )
    ds.node(
        "bigquery",
        label="Google BigQuery\n(Vector Store for RAG)",
        shape="cylinder",
        fillcolor="#e0ccff",
    )
    ds.node(
        "gemini", label="Google Gemini API\n(LLM)", shape="ellipse", fillcolor="#d6b3ff"
    )
    ds.node(
        "external_apis",
        label="External APIs\n(Yahoo Finance, Search, etc.)",
        shape="ellipse",
        fillcolor="#d6b3ff",
    )

# --- 6. Define Edges to show data flow ---
# Using xlabel for compatibility with ortho splines
dot.edge("user", "nextjs_ui", xlabel="Interacts with")
dot.edge("nextjs_ui", "nextjs_api", xlabel="API Calls")
dot.edge("nextjs_api", "fastapi_gateway", xlabel="HTTP Requests")
dot.edge("fastapi_gateway", "chat_service_graph", xlabel="Routes to Quick Search")
dot.edge("fastapi_gateway", "deep_search_graph", xlabel="Routes to Deep Search")
dot.edge("chat_service_graph", "chat_service_logic", xlabel="Executes")
dot.edge("chat_service_logic", "gemini", xlabel="Calls LLM for decisions")
dot.edge("chat_service_logic", "tools", xlabel="Uses Tools if needed")
dot.edge("deep_search_graph", "deep_search_logic", xlabel="Executes")
dot.edge("deep_search_logic", "gemini", xlabel="Calls LLM for planning/writing")
dot.edge("deep_search_logic", "tools", xlabel="Uses Tools for research")
dot.edge("tools", "external_apis", xlabel="API Calls")
dot.edge("tools", "bigquery", xlabel="RAG Query")
dot.edge("tools", "postgres_primary", xlabel="Portfolio Query")
dot.edge("fastapi_gateway", "postgres_primary", xlabel="CRUD Operations")
dot.edge("fastapi_gateway", "redis", xlabel="Cache Get/Set", style="dashed")
dot.edge(
    "chat_service_graph", "postgres_checkpoint", xlabel="Saves State", style="dashed"
)
dot.edge(
    "deep_search_graph", "postgres_checkpoint", xlabel="Saves State", style="dashed"
)
dot.edge("fastapi_gateway", "bigquery", xlabel="Ingests Docs", style="dashed")


# --- 7. Render the graph ---
output_filename = "zenfi_ai_architecture"
dot.render(output_filename, view=False)

print(f"Graph saved as {output_filename}.png")
