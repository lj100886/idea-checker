"""MCP服务器模式：把选题审查能力暴露为MCP工具"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_mcp_server(config_path: Optional[str] = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError("未安装 mcp: pip install mcp")
    from ..config import Config
    from ..core.orchestrator import Orchestrator
    from ..core.report_generator import ReportGenerator
    config = Config(config_path)
    orchestrator = Orchestrator(config)
    mcp = FastMCP("idea-checker")

    @mcp.tool()
    def check_idea(idea: str, persona: str = "default") -> str:
        """审查一个选题/项目想法有没有人做过。输入想法描述，AI自动联网搜索分析，输出带评级的审查报告。"""
        logger.info(f"MCP check_idea: {idea[:50]}")
        report = orchestrator.check_idea(idea, persona)
        return ReportGenerator.to_text(report)

    @mcp.tool()
    def list_personas() -> str:
        """列出所有可用的人设风格"""
        personas = config.list_personas()
        return "可用人设：\n" + "\n".join(f"- {p}" for p in personas)

    return mcp


def run_mcp_server(config_path: Optional[str] = None):
    mcp = create_mcp_server(config_path)
    mcp.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_mcp_server()
