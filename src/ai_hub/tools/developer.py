import os
import sys
from pathlib import Path

def edit_workspace_code(file_path: str, old_text: str, new_text: str) -> str:
    """
    Инструмент для редактирования исходного кода платформы AI HUB.
    Позволяет нейронке менять темы, интерфейс и логику работы.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Ошибка: Файл {file_path} не найден."
    
    try:
        content = path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Ошибка: Текст для замены не найден в файле {file_path}."
        
        new_content = content.replace(old_text, new_text, 1)
        path.write_text(new_content, encoding="utf-8")
        return "Успешно изменено! Изменения вступят в силу после перезапуска приложения."
    except Exception as e:
        return f"Ошибка при редактировании файла: {str(e)}"
