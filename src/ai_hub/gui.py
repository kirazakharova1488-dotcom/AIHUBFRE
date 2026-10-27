import flet as ft
import asyncio
import os
import sys

# Пытаемся импортировать мобильный движок (для ПК сделаем заглушку, чтобы код не падал до сборки)
try:
    import llama_cpp
    MOBILE_LLM_AVAILABLE = True
except ImportError:
    MOBILE_LLM_AVAILABLE = False

class MobileAIApp:
    def __init__(self):
        self.llm = None
        self.model_path = "model/llama-3.2-1b-instruct.Q4_K_M.gguf"

    def init_model(self) -> str:
        if not MOBILE_LLM_AVAILABLE:
            return "Режим ПК: Движок llama_cpp не установлен (будет доступен внутри APK)."
        
        if not os.path.exists(self.model_path):
            return f"Файл модели не найден по пути: {self.model_path}. Поместите туда .gguf файл."
        
        try:
            # Инициализируем модель прямо в памяти смартфона
            self.llm = llama_cpp.Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4,        # Оптимально для мобильных ядер
                n_gpu_layers=1      # Задействуем мобильный GPU/NPU если доступен
            )
            return "Локальная модель успешно загружена в память устройства! 🚀"
        except Exception as e:
            return f"Ошибка инициализации модели: {str(e)}"

    def generate_response(self, prompt: str) -> str:
        if not self.llm:
            return f"[Имитация ответа на ПК]: Вы сказали: '{prompt}'. (На Android здесь ответит встроенная Llama-3.2)."
        
        try:
            # Форматируем промпт под Llama-3.2-Instruct
            full_prompt = f"<|system|>\nВы — встроенный ИИ-помощник в вашем телефоне.<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
            output = self.llm(full_prompt, max_tokens=150, stop=["<|end|>"])
            return output["choices"][0]["text"].strip()
        except Exception as e:
            return f"Ошибка генерации: {str(e)}"

def main(page: ft.Page):
    page.title = "AI HUB Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    
    ai_engine = MobileAIApp()
    
    chat_history = ft.ListView(expand=1, spacing=10, auto_scroll=True)
    message_input = ft.TextField(hint_text="Напишите встроенному ИИ...", expand=True)
    status_text = ft.Text("Проверка движка...", color=ft.colors.GREY_400, size=12)
    
    # Кнопка отправки
    def send_message(e):
        if not message_input.value:
            return
        
        user_text = message_input.value
        chat_history.controls.append(ft.Text(f"Вы: {user_text}", color=ft.colors.BLUE_200))
        message_input.value = ""
        page.update()
        
        # Индикатор мышления
        thinking_index = len(chat_history.controls)
        chat_history.controls.append(ft.Text("ИИ думает прямо на телефоне... 🧠", italic=True, color=ft.colors.GREY_500))
        page.update()
        
        # Запуск генерации
        response = ai_engine.generate_response(user_text)
        
        # Удаляем индикатор и выводим ответ
        chat_history.controls.pop(thinking_index)
        chat_history.controls.append(ft.Text(f"Локальный ИИ: {response}", color=ft.colors.GREEN_200))
        page.update()

    send_button = ft.IconButton(icon=ft.icons.SEND, on_click=send_message)
    
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("AI HUB • OFFLINE EDITION", weight=ft.FontWeight.BOLD, size=16, color=ft.colors.CYAN_200),
                status_text,
            ]),
            padding=10
        ),
        ft.Divider(),
        chat_history,
        ft.Row([message_input, send_button], alignment=ft.MainAxisAlignment.CENTER)
    )
    
    # Фоновая инициализация модели при старте приложения
    status_text.value = ai_engine.init_model()
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
