"""Agent runtime: executes an agent loop with step limits and calls code tools."""

from __future__ import annotations
import json
import re
import asyncio
from ai_hub.agents.models import AgentConfig, ActionRecord, AgentRunResult, AgentStatus
from ai_hub.tools.developer import edit_workspace_code
from ai_hub.core.orchestrator import ChatResult

class AgentRuntime:
    def __init__(self, manager=None, permissions=None, orchestrator=None) -> None:
        self.manager = manager
        self.permissions = permissions
        self.orchestrator = orchestrator

    async def run(self, agent: AgentConfig, prompt: str, steps: int | None = None) -> AgentRunResult:
        if not self.orchestrator:
            from ai_hub.config import settings
            from ai_hub.core.orchestrator import Orchestrator
            self.orchestrator = Orchestrator(settings)

        limit = steps or agent.max_steps
        history: list[ActionRecord] = []
        current_prompt = prompt
        final_text = ""
        
        system_instructions = (
            "Вы — самомодифицирующийся ИИ-ассистент в платформе AI HUB.\n"
            "У вас есть доступ к инструменту редактирования кода проекта.\n"
            "Если вам нужно изменить код файла, верните JSON-команду ИСКЛЮЧИТЕЛЬНО в следующем формате:\n"
            "```json\n"
            "{\n"
            '  "action": "edit_workspace_code",\n'
            '  "file_path": "путь_к_файлу",\n'
            '  "old_text": "точный_старый_текст_для_замены",\n'
            '  "new_text": "новый_текст"\n'
            "}\n"
            "```\n"
            "Если вам нужно просто ответить пользователю или вы завершили изменения, пишите обычный текст."
        )

        full_message = f"{system_instructions}\n\nЗапрос пользователя: {current_prompt}"

        for step in range(1, limit + 1):
            try:
                # Пробуем стандартный вызов оркестратора
                chat_result = await self.orchestrator.process(message=full_message)
                
                # Если роутер упал или провайдер недоступен, делаем прямой фолбэк на Ollama
                if "Requested provider is unavailable" in chat_result.text or "No providers available" in chat_result.text:
                    if self.orchestrator.registry:
                        ollama_provider = self.orchestrator.registry.get("ollama")
                        if ollama_provider:
                            from ai_hub.providers.base import ChatRequest
                            req = ChatRequest(message=full_message, model=agent.model or "qwen2.5:7b")
                            ollama_res = await ollama_provider.chat(req)
                            chat_result = ChatResult(text=ollama_res.text, model=ollama_res.model, provider="ollama")
            except Exception as e:
                chat_result = ChatResult(text=f"Runtime error: {str(e)}", model="-", provider="error")
            
            response_text = chat_result.text
            final_text = response_text
            
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            
            if json_match:
                try:
                    tool_call = json.loads(json_match.group(1))
                    if tool_call.get("action") == "edit_workspace_code":
                        file_path = tool_call.get("file_path")
                        old_text = tool_call.get("old_text")
                        new_text = tool_call.get("new_text")
                        
                        result_msg = edit_workspace_code(file_path, old_text, new_text)
                        
                        record = ActionRecord(
                            step=step, 
                            action="edit_workspace_code", 
                            tool="edit_workspace_code", 
                            result=f"Файл: {file_path}. Результат: {result_msg}", 
                            status="ok"
                        )
                        history.append(record)
                        
                        full_message = f"Результат выполнения инструмента: {result_msg}\nПродолжайте выполнение или завершите ответ."
                        continue
                except Exception as e:
                    error_msg = f"Ошибка разбора JSON команды: {str(e)}"
                    history.append(ActionRecord(step=step, action="tool_error", tool=None, result=error_msg, status="error"))
            
            record = ActionRecord(step=step, action="respond", tool=None, result=response_text, status="ok")
            history.append(record)
            break

        return AgentRunResult(
            agent_id=agent.agent_id,
            status=AgentStatus.DONE,
            final_text=final_text,
            steps=history,
        )
