"""AI HUB Windows desktop interface."""

from __future__ import annotations

import flet as ft


BG = "#0B0F14"
PANEL = "#111820"
PANEL_LIGHT = "#18232D"
BORDER = "#263440"
TEXT = "#E5EDF3"
MUTED = "#8999A8"
ACCENT = "#55D9C5"


def main(page: ft.Page) -> None:
    page.title = "AI HUB | Windows Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    page.spacing = 0

    messages = ft.ListView(
        expand=True,
        spacing=12,
        auto_scroll=True,
        padding=20,
    )

    status = ft.Text(
        "UI PREVIEW  |  AI CORE NOT CONNECTED",
        color="#E5B567",
        size=11,
    )

    def add_message(role: str, content: str, color: str) -> None:
        messages.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(role, color=color, weight=ft.FontWeight.BOLD, size=12),
                        ft.Text(content, color=TEXT, selectable=True, size=14),
                    ],
                    spacing=6,
                ),
                bgcolor=PANEL_LIGHT,
                border=ft.Border.all(1, BORDER),
                border_radius=8,
                padding=14,
            )
        )

    def send_message(e=None) -> None:
        value = (message_input.value or "").strip()
        if not value:
            return

        add_message("YOU", value, ACCENT)
        add_message(
            "SYSTEM",
            "Сообщение принято интерфейсом. Подключение настоящей генерации "
            "через Orchestrator будет следующим этапом.",
            MUTED,
        )

        message_input.value = ""
        page.update()

    message_input = ft.TextField(
        multiline=True,
        min_lines=3,
        max_lines=8,
        shift_enter=True,
        expand=True,
        hint_text="Опишите задачу для AI HUB...",
        hint_style=ft.TextStyle(color=MUTED),
        text_size=14,
        color=TEXT,
        bgcolor=PANEL,
        border_color=BORDER,
        focused_border_color=ACCENT,
        cursor_color=ACCENT,
        on_submit=send_message,
    )

    sidebar = ft.Container(
        width=220,
        bgcolor=PANEL,
        padding=18,
        content=ft.Column(
            [
                ft.Text("AI HUB", size=22, weight=ft.FontWeight.BOLD, color=ACCENT),
                ft.Text("WINDOWS TERMINAL", size=10, color=MUTED),
                ft.Divider(color=BORDER),
                ft.Text("WORKSPACE", color=MUTED, size=11),
                ft.Text("▸  Проекты", color=TEXT),
                ft.Text("▸  Файлы", color=TEXT),
                ft.Container(height=12),
                ft.Text("INTELLIGENCE", color=MUTED, size=11),
                ft.Text("▸  Агенты", color=TEXT),
                ft.Text("▸  Модели", color=TEXT),
                ft.Text("▸  Провайдеры", color=TEXT),
                ft.Container(height=12),
                ft.Text("MEMORY", color=MUTED, size=11),
                ft.Text("▸  История чатов", color=TEXT),
                ft.Text("▸  Память", color=TEXT),
                ft.Container(expand=True),
                ft.Divider(color=BORDER),
                ft.Text("AI HUB CORE  ·  v0.1.0", color=MUTED, size=10),
            ],
            spacing=13,
            expand=True,
        ),
    )

    center = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "TERMINAL / MAIN SESSION",
                                    color=TEXT,
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text("Рабочее пространство AI HUB", color=MUTED, size=11),
                            ],
                            spacing=4,
                        ),
                        ft.Container(expand=True),
                        status,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=BORDER),
                messages,
                ft.Container(
                    bgcolor=PANEL,
                    border=ft.Border.all(1, BORDER),
                    border_radius=10,
                    padding=12,
                    content=ft.Column(
                        [
                            message_input,
                            ft.Row(
                                [
                                    ft.Text(
                                        "SHIFT + ENTER — новая строка  |  ENTER — отправить",
                                        color=MUTED,
                                        size=10,
                                    ),
                                    ft.Container(expand=True),
                                    ft.Button(
                                        content="Отправить",
                                        on_click=send_message,
                                        bgcolor="#174B48",
                                        color=ACCENT,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=14,
            expand=True,
        ),
    )

    right_panel = ft.Container(
        width=220,
        bgcolor=PANEL,
        padding=18,
        content=ft.Column(
            [
                ft.Text("SYSTEM STATUS", color=ACCENT, size=12, weight=ft.FontWeight.BOLD),
                ft.Divider(color=BORDER),
                ft.Text("PROVIDER", color=MUTED, size=10),
                ft.Text("Not connected", color=TEXT),
                ft.Container(height=10),
                ft.Text("MODEL", color=MUTED, size=10),
                ft.Text("Not selected", color=TEXT),
                ft.Container(height=10),
                ft.Text("AGENTS", color=MUTED, size=10),
                ft.Text("Ready for integration", color=TEXT, size=12),
                ft.Container(height=10),
                ft.Text("AUTONOMY", color=MUTED, size=10),
                ft.Text("BALANCED", color=ACCENT),
                ft.Container(expand=True),
                ft.Divider(color=BORDER),
                ft.Text("WINDOWS CORE", color=MUTED, size=10),
                ft.Text("Desktop interface preview", color=MUTED, size=10),
            ],
            spacing=10,
            expand=True,
        ),
    )

    page.add(
        ft.Row(
            [
                sidebar,
                ft.Container(width=1, bgcolor=BORDER),
                center,
                ft.Container(width=1, bgcolor=BORDER),
                right_panel,
            ],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )

    add_message(
        "AI HUB",
        "Windows Terminal запущен. Интерфейс готов. На следующем этапе "
        "подключим настоящее ядро и Ollama.",
        ACCENT,
    )


if __name__ == "__main__":
    ft.run(main)
