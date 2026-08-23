"""MCP Server entry point — registers all codely-kb tools."""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from .config import get_config
from .tools import kb as kb_tools
from .tools import search as search_tools
from .tools import quiz as quiz_tools
from .tools import plan as plan_tools
from .tools import research as research_tools

logger = logging.getLogger(__name__)


def _json_result(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


TOOL_DEFINITIONS = [
    {"name": "create_kb", "description": "Create a new knowledge base. Returns kb_id on success.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string", "description": "Unique knowledge base name"}, "description": {"type": "string", "description": "Optional description", "default": ""}}, "required": ["name"]}},
    {"name": "delete_kb", "description": "Delete a knowledge base and all its data.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}}, "required": ["kb_id"]}},
    {"name": "list_kbs", "description": "List all knowledge bases.", "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_kb_info", "description": "Get detailed info about a knowledge base including documents.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}}, "required": ["kb_id"]}},
    {"name": "add_documents", "description": "Import documents into a knowledge base. Supports PDF, Markdown, code files, text, HTML, EPUB. Pass file paths or directory paths (directories are scanned recursively).", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "files": {"type": "array", "items": {"type": "string"}, "description": "File or directory paths to import"}}, "required": ["kb_id", "files"]}},
    {"name": "add_url", "description": "Fetch a URL and add its content to a knowledge base.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "url": {"type": "string", "description": "URL to fetch and import"}}, "required": ["kb_id", "url"]}},
    {"name": "list_documents", "description": "List all documents in a knowledge base.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}}, "required": ["kb_id"]}},
    {"name": "remove_document", "description": "Remove a document and its chunks from a knowledge base.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "file_path": {"type": "string", "description": "File path of the document to remove"}}, "required": ["kb_id", "file_path"]}},
    {"name": "search_kb", "description": "Perform semantic search on a knowledge base. Returns matching document chunks ranked by relevance.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "query": {"type": "string", "description": "Search query"}, "top_k": {"type": "number", "description": "Number of results (default 5)", "default": 5}, "min_score": {"type": "number", "description": "Minimum similarity score (default 0.3)", "default": 0.3}}, "required": ["kb_id", "query"]}},
    {"name": "rag_query", "description": "RAG retrieval — search KB and return chunks + assembled context text + suggested prompt for the LLM.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "query": {"type": "string", "description": "Question to find answers for"}, "top_k": {"type": "number", "description": "Number of chunks to retrieve (default 5)", "default": 5}}, "required": ["kb_id", "query"]}},
    {"name": "generate_quiz", "description": "Generate quiz questions from KB content. Retrieves relevant chunks and constructs a prompt for the Codely LLM to generate actual questions.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "topic": {"type": "string", "description": "Quiz topic"}, "num_questions": {"type": "number", "description": "Number of questions (default 5)", "default": 5}, "question_type": {"type": "string", "enum": ["choice", "short_answer", "fill_blank", "mixed"], "description": "Question type (default mixed)", "default": "mixed"}, "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"], "description": "Difficulty level (default medium)", "default": "medium"}}, "required": ["kb_id", "topic"]}},
    {"name": "grade_answer", "description": "Record and persist a quiz answer grading result.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "question_id": {"type": "string", "description": "Question ID"}, "question_type": {"type": "string", "description": "Question type"}, "question_text": {"type": "string", "description": "Question text", "default": ""}, "user_answer": {"type": "string", "description": "User's answer", "default": ""}, "correct_answer": {"type": "string", "description": "Correct answer", "default": ""}, "score": {"type": "number", "description": "Score 0-100", "default": 0}, "concepts_missed": {"type": "array", "items": {"type": "string"}, "description": "Concepts the user missed", "default": []}}, "required": ["kb_id", "question_id", "question_type"]}},
    {"name": "list_quiz_history", "description": "View quiz history for a knowledge base.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "limit": {"type": "number", "description": "Max results (default 50)", "default": 50}}, "required": ["kb_id"]}},
    {"name": "create_learning_plan", "description": "Create a structured learning plan from KB content.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "topic": {"type": "string", "description": "Learning topic"}, "depth": {"type": "string", "enum": ["quick", "standard", "thorough"], "description": "Plan depth (default standard)", "default": "standard"}}, "required": ["kb_id", "topic"]}},
    {"name": "save_learning_plan", "description": "Persist a learning plan after the LLM generates steps.", "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string", "description": "Knowledge base ID"}, "topic": {"type": "string", "description": "Learning topic"}, "steps": {"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "concepts": {"type": "array", "items": {"type": "string"}}, "kb_chunks": {"type": "array", "items": {"type": "string"}}}}, "description": "Learning steps from LLM"}}, "required": ["kb_id", "topic", "steps"]}},
    {"name": "get_learning_plan", "description": "Retrieve a learning plan with all steps and progress.", "inputSchema": {"type": "object", "properties": {"plan_id": {"type": "string", "description": "Learning plan ID"}}, "required": ["plan_id"]}},
    {"name": "update_step_progress", "description": "Update a learning step's progress.", "inputSchema": {"type": "object", "properties": {"plan_id": {"type": "string", "description": "Learning plan ID"}, "step_id": {"type": "string", "description": "Step ID"}, "status": {"type": "string", "enum": ["completed", "skipped", "struggling"], "description": "New status"}, "score": {"type": "number", "description": "Optional score 0-100", "default": None}}, "required": ["plan_id", "step_id", "status"]}},
    {"name": "get_weak_concepts", "description": "Get the list of weak concepts for a learning plan with recommended review chunks.", "inputSchema": {"type": "object", "properties": {"plan_id": {"type": "string", "description": "Learning plan ID"}}, "required": ["plan_id"]}},
    {"name": "research_search", "description": "Multi-step research search combining KB retrieval and web search suggestions.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Research question"}, "kb_id": {"type": "string", "description": "Optional KB ID"}, "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "description": "Research depth (default standard)", "default": "standard"}}, "required": ["query"]}},
    {"name": "solve_search", "description": "Support for three-phase problem solving (diagnose → solve → verify).", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Problem to solve"}, "kb_id": {"type": "string", "description": "Optional KB ID"}, "phase": {"type": "string", "enum": ["diagnose", "solve", "verify"], "description": "Solving phase (default diagnose)", "default": "diagnose"}}, "required": ["query"]}},
    {"name": "shuffle_quiz_options", "description": "Shuffle the options of each choice question and fix correct_index. Call after LLM generates quiz questions to randomize answer positions.", "inputSchema": {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "object"}, "description": "Quiz questions from generate_quiz (LLM output)"}}, "required": ["questions"]}},
]

TOOL_HANDLERS = {
    "create_kb": lambda args: kb_tools.create_kb(name=args["name"], description=args.get("description", "")),
    "delete_kb": lambda args: kb_tools.delete_kb(kb_id=args["kb_id"]),
    "list_kbs": lambda args: kb_tools.list_kbs(),
    "get_kb_info": lambda args: kb_tools.get_kb_info(kb_id=args["kb_id"]),
    "add_documents": lambda args: kb_tools.add_documents(kb_id=args["kb_id"], files=args["files"]),
    "add_url": lambda args: kb_tools.add_url(kb_id=args["kb_id"], url=args["url"]),
    "list_documents": lambda args: kb_tools.list_documents(kb_id=args["kb_id"]),
    "remove_document": lambda args: kb_tools.remove_document(kb_id=args["kb_id"], file_path=args["file_path"]),
    "search_kb": lambda args: search_tools.search_kb(kb_id=args["kb_id"], query=args["query"], top_k=args.get("top_k", 0), min_score=args.get("min_score", 0.0)),
    "rag_query": lambda args: search_tools.rag_query(kb_id=args["kb_id"], query=args["query"], top_k=args.get("top_k", 0)),
    "generate_quiz": lambda args: quiz_tools.generate_quiz(kb_id=args["kb_id"], topic=args["topic"], num_questions=args.get("num_questions", 5), question_type=args.get("question_type", "mixed"), difficulty=args.get("difficulty", "medium")),
    "grade_answer": lambda args: quiz_tools.grade_answer(kb_id=args["kb_id"], question_id=args["question_id"], question_type=args["question_type"], question_text=args.get("question_text", ""), user_answer=args.get("user_answer", ""), correct_answer=args.get("correct_answer", ""), score=args.get("score", 0), concepts_missed=args.get("concepts_missed")),
    "list_quiz_history": lambda args: quiz_tools.list_quiz_history(kb_id=args["kb_id"], limit=args.get("limit", 50)),
    "create_learning_plan": lambda args: plan_tools.create_learning_plan(kb_id=args["kb_id"], topic=args["topic"], depth=args.get("depth", "standard")),
    "save_learning_plan": lambda args: plan_tools.save_learning_plan(kb_id=args["kb_id"], topic=args["topic"], steps=args["steps"]),
    "get_learning_plan": lambda args: plan_tools.get_learning_plan(plan_id=args["plan_id"]),
    "update_step_progress": lambda args: plan_tools.update_step_progress(plan_id=args["plan_id"], step_id=args["step_id"], status=args["status"], score=args.get("score")),
    "get_weak_concepts": lambda args: plan_tools.get_weak_concepts(plan_id=args["plan_id"]),
    "research_search": lambda args: research_tools.research_search(query=args["query"], kb_id=args.get("kb_id"), depth=args.get("depth", "standard")),
    "solve_search": lambda args: research_tools.solve_search(query=args["query"], kb_id=args.get("kb_id"), phase=args.get("phase", "diagnose")),
    "shuffle_quiz_options": lambda args: {"shuffled_questions": quiz_tools.shuffle_quiz_options(args["questions"])},
}


def create_server():
    """Create and configure the MCP server (MCP SDK 2.0 API)."""
    try:
        from mcp.server import Server
        import mcp.types as types
    except ImportError:
        logger.error("MCP SDK not installed. Install with: pip install mcp")
        sys.exit(1)

    async def handle_list_tools(ctx, params=None) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[types.Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"]) for t in TOOL_DEFINITIONS])

    async def handle_call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
        name = params.name; arguments = params.arguments or {}
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"error": f"[ERROR] Unknown tool: {name}"}))], isError=True)
        try:
            result = handler(arguments)
            return types.CallToolResult(content=[types.TextContent(type="text", text=_json_result(result))])
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"error": f"[ERROR] {name}: {e}"}))], isError=True)

    return Server("codely-kb", on_list_tools=handle_list_tools, on_call_tool=handle_call_tool)


async def run_async() -> None:
    from mcp.server.stdio import stdio_server
    server = create_server()
    config = get_config()
    logger.info("Starting codely-kb MCP Server (home: %s)", config.kb_home)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    import asyncio
    asyncio.run(run_async())


if __name__ == "__main__":
    main()
